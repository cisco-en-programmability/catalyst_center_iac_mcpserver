from __future__ import annotations

import asyncio
import os
import sys
from urllib.parse import urlparse
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from uuid import uuid4
from typing import Any, Awaitable, Callable

import ansible_runner
import orjson

from models import TaskLifecycleStatus, TaskRecord, TenantCredentials, utc_now
from redis_store import RedisTaskStore, TaskStore
from settings import Settings, get_settings
from cluster_registry import CatalystCenterClusterCatalog, load_cluster_catalog


ProgressCallback = Callable[[float, float, str], Awaitable[None]]


@dataclass(slots=True)
class TaskSubmission:
    task_id: str
    status: str


class RunnerEngine:
    def __init__(self, settings: Settings, store: TaskStore | None = None) -> None:
        self.settings = settings
        self.store = store or RedisTaskStore(settings)
        self.cluster_catalog: CatalystCenterClusterCatalog = load_cluster_catalog(
            settings.catalyst_center_clusters_file
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._progress_state: dict[str, dict[str, Any]] = {}
        self._progress_lock = Lock()

    async def connect(self) -> None:
        await self.store.connect()
        if self._loop is None:
            self._loop = asyncio.get_running_loop()

    async def close(self) -> None:
        await self.store.close()

    def resolve_credentials(
        self,
        tenant_id: str,
        catalyst_center: str | None = None,
    ) -> tuple[TenantCredentials, str | None]:
        cluster = self.cluster_catalog.resolve(catalyst_center)
        if cluster is not None:
            return self._resolve_cluster_credentials(cluster), cluster.name
        return self._resolve_tenant_credentials(tenant_id), None

    def _resolve_tenant_credentials(self, tenant_id: str) -> TenantCredentials:
        tenant_prefix = tenant_id.strip().upper().replace("-", "_")
        env = os.environ
        host = env.get(self.settings.tenant_env_name(tenant_id, "HOST")) or self.settings.catalystcenter_host
        username = env.get(self.settings.tenant_env_name(tenant_id, "USERNAME")) or self.settings.catalystcenter_username
        password = env.get(self.settings.tenant_env_name(tenant_id, "PASSWORD")) or self.settings.catalystcenter_password
        verify_ssl_raw = env.get(self.settings.tenant_env_name(tenant_id, "VERIFY_SSL"))
        port_raw = env.get(self.settings.tenant_env_name(tenant_id, "PORT"))

        if not host or not username or not password:
            raise ValueError(
                f"Missing Catalyst Center credentials for tenant '{tenant_prefix or 'DEFAULT'}'"
            )

        verify_ssl = (
            verify_ssl_raw.lower() == "true"
            if verify_ssl_raw is not None
            else self.settings.catalystcenter_verify_ssl
        )
        port = int(port_raw) if port_raw else self.settings.catalystcenter_port
        
        # Get version and normalize it to the nearest supported version
        raw_version = (env.get(self.settings.tenant_env_name(tenant_id, "VERSION")) 
                      or self.settings.catalystcenter_version)
        normalized_version = self.settings.normalize_catalystcenter_version(raw_version)

        return TenantCredentials(
            host=self._normalize_host(host),
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            port=port,
            version=normalized_version,
        )

    def _resolve_cluster_credentials(self, cluster: Any) -> TenantCredentials:
        env = os.environ
        slug = cluster.slug.upper()
        username = env.get(self.settings.cluster_env_name(slug, "USERNAME")) or env.get(
            self.settings.legacy_cluster_env_name(slug, "USERNAME")
        )
        password = env.get(self.settings.cluster_env_name(slug, "PASSWORD")) or env.get(
            self.settings.legacy_cluster_env_name(slug, "PASSWORD")
        )
        if not username or not password:
            raise ValueError(
                f"Missing credentials for Catalyst Center cluster `{cluster.name}`. "
                f"Set {self.settings.cluster_env_name(slug, 'USERNAME')} and "
                f"{self.settings.cluster_env_name(slug, 'PASSWORD')}."
            )
        verify_ssl_raw = env.get(self.settings.cluster_env_name(slug, "VERIFY_SSL")) or env.get(
            self.settings.legacy_cluster_env_name(slug, "VERIFY_SSL")
        )
        port_raw = env.get(self.settings.cluster_env_name(slug, "PORT")) or env.get(
            self.settings.legacy_cluster_env_name(slug, "PORT")
        )
        version = env.get(self.settings.cluster_env_name(slug, "VERSION")) or env.get(
            self.settings.legacy_cluster_env_name(slug, "VERSION")
        ) or cluster.version
        verify_ssl = (
            verify_ssl_raw.lower() == "true"
            if verify_ssl_raw is not None
            else cluster.verify_ssl
        )
        port = int(port_raw) if port_raw else cluster.port
        return TenantCredentials(
            host=self._normalize_host(cluster.host),
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            port=port,
            version=version,
        )

    @staticmethod
    def _normalize_host(host: str) -> str:
        if "://" not in host:
            return host
        parsed = urlparse(host)
        return parsed.hostname or host

    async def submit_workflow(
        self,
        *,
        tool_name: str,
        module_name: str,
        tenant_id: str,
        catalyst_center: str | None = None,
        state: str,
        config: list[dict[str, Any]],
        progress_callback: ProgressCallback | None = None,
        destructive: bool = False,
        progress_token: str | int | None = None,
    ) -> TaskSubmission:
        workflow_module_args = {
            "state": state,
            "config_verify": True,
            "config": config,
        }
        return await self.submit_module(
            tool_name=tool_name,
            module_name=module_name,
            tenant_id=tenant_id,
            catalyst_center=catalyst_center,
            module_args=workflow_module_args,
            progress_callback=progress_callback,
            destructive=destructive,
            progress_token=progress_token,
        )

    async def submit_module(
        self,
        *,
        tool_name: str,
        module_name: str,
        tenant_id: str,
        catalyst_center: str | None = None,
        module_args: dict[str, Any],
        progress_callback: ProgressCallback | None = None,
        destructive: bool = False,
        progress_token: str | int | None = None,
    ) -> TaskSubmission:
        await self.connect()
        task_id = str(uuid4())
        runner_ident = task_id
        artifact_dir = self.settings.runner_artifact_root / task_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        credentials, resolved_cluster_name = self.resolve_credentials(tenant_id, catalyst_center)
        primary_module_args = {
            **module_args,
            "catalystcenter_host": credentials.host,
            "catalystcenter_username": credentials.username,
            "catalystcenter_password": credentials.password,
            "catalystcenter_verify": credentials.verify_ssl,
            "catalystcenter_port": str(credentials.port),
            "catalystcenter_version": credentials.version,
        }
        playbook_name = self._write_runner_files(
            artifact_dir=artifact_dir,
            collection_namespace=self.settings.ansible_collection_namespace,
            module_name=module_name,
            primary_module_args=primary_module_args,
        )
        record = TaskRecord(
            task_id=task_id,
            tenant_id=tenant_id,
            catalyst_center=resolved_cluster_name,
            tool_name=tool_name,
            module_name=module_name,
            status=TaskLifecycleStatus.SUBMITTED,
            status_message="Task submitted to ansible-runner",
            artifact_dir=str(artifact_dir),
            runner_ident=runner_ident,
            module_args=primary_module_args,
            destructive=destructive,
            progress_token=progress_token,
        )
        await self.store.save_task(record)
        await self._emit_progress(
            task_id,
            1,
            100,
            "Task submitted",
            callback=progress_callback,
            status=TaskLifecycleStatus.SUBMITTED,
        )

        thread, runner = ansible_runner.run_async(
            private_data_dir=str(artifact_dir),
            playbook=playbook_name,
            ident=runner_ident,
            quiet=True,
            event_handler=self._make_event_handler(task_id, progress_callback),
            status_handler=self._make_status_handler(task_id, progress_callback),
        )

        asyncio.create_task(
            self._monitor_runner(
                task_id=task_id,
                runner=runner,
                thread=thread,
                artifact_dir=artifact_dir,
                callback=progress_callback,
            )
        )
        return TaskSubmission(task_id=task_id, status="submitted")

    async def get_task(self, task_id: str) -> TaskRecord | None:
        return await self.store.get_task(task_id)

    def _write_runner_files(
        self,
        *,
        artifact_dir: Path,
        collection_namespace: str,
        module_name: str,
        primary_module_args: dict[str, Any],
    ) -> str:
        env_dir = artifact_dir / "env"
        project_dir = artifact_dir / "project"
        inventory_dir = artifact_dir / "inventory"
        env_dir.mkdir(parents=True, exist_ok=True)
        project_dir.mkdir(parents=True, exist_ok=True)
        inventory_dir.mkdir(parents=True, exist_ok=True)

        ansible_python_interpreter = os.environ.get("ANSIBLE_PYTHON_INTERPRETER") or sys.executable
        playbook_name = "playbook.yml"
        playbook = f"""---
- name: Execute Catalyst Center IaC workflow
  hosts: localhost
  gather_facts: false
  connection: local
  vars:
    ansible_python_interpreter: "{ansible_python_interpreter}"
  tasks:
    - name: Execute workflow manager
      {collection_namespace}.{module_name}: "{{{{ primary_module_args }}}}"
      register: catalyst_center_result

    - name: Persist module result
      ansible.builtin.copy:
        content: "{{{{ catalyst_center_result | to_nice_json }}}}"
        dest: "{{{{ playbook_dir }}}}/result.json"
        mode: "0600"
"""
        (project_dir / playbook_name).write_text(playbook, encoding="utf-8")
        (inventory_dir / "hosts").write_text("localhost ansible_connection=local\n", encoding="utf-8")
        (env_dir / "extravars").write_bytes(
            orjson.dumps(
                {
                    "primary_module_args": primary_module_args,
                }
            )
        )
        (env_dir / "sitecustomize.py").write_text(
            "try:\n"
            "    import catalystcentersdk.api as _api\n"
            "    if not hasattr(_api, 'DNACenterAPI') and hasattr(_api, 'CatalystCenterAPI'):\n"
            "        _api.DNACenterAPI = _api.CatalystCenterAPI\n"
            "except Exception:\n"
            "    pass\n",
            encoding="utf-8",
        )
        (env_dir / "envvars").write_bytes(
            orjson.dumps(
                {
                    "ANSIBLE_STDOUT_CALLBACK": "json",
                    "ANSIBLE_RETRY_FILES_ENABLED": "false",
                    "ANSIBLE_HOST_KEY_CHECKING": "false",
                    "PYTHONUNBUFFERED": "1",
                    "PYTHONPATH": str(env_dir),
                }
            )
        )
        return playbook_name

    def _make_status_handler(
        self,
        task_id: str,
        callback: ProgressCallback | None,
    ) -> Callable[[dict[str, Any], Any], None]:
        def handler(status_data: dict[str, Any], runner_config: Any = None) -> None:
            status = status_data.get("status", "unknown")
            message = status_data.get("job_explanation") or f"Runner status: {status}"
            if status in {"starting", "running"}:
                new_status = TaskLifecycleStatus.RUNNING
                progress = 10 if status == "starting" else 20
            elif status == "failed":
                new_status = TaskLifecycleStatus.FAILED
                progress = 100
            elif status == "successful":
                new_status = TaskLifecycleStatus.COMPLETED
                progress = 100
            else:
                new_status = TaskLifecycleStatus.RUNNING
                progress = 15
            self._schedule_progress_update(
                task_id=task_id,
                progress=progress,
                total=100,
                message=message,
                callback=callback,
                status=new_status,
            )

        return handler

    def _make_event_handler(
        self,
        task_id: str,
        callback: ProgressCallback | None,
    ) -> Callable[[dict[str, Any]], None]:
        def handler(event_data: dict[str, Any]) -> bool:
            event_name = event_data.get("event", "unknown")
            task_name = event_data.get("event_data", {}).get("task", event_name)
            if event_name == "playbook_on_task_start":
                progress = self._next_progress_value(task_id, floor=30, step=25, cap=90)
                message = f"Executing playbook task: {task_name}"
                self._schedule_progress_update(
                    task_id=task_id,
                    progress=progress,
                    total=100,
                    message=message,
                    callback=callback,
                    status=TaskLifecycleStatus.RUNNING,
                    append_event={"event": event_name, "task": task_name},
                )
            elif event_name in {"runner_on_failed", "runner_on_unreachable"}:
                host = event_data.get("event_data", {}).get("host", "localhost")
                self._schedule_progress_update(
                    task_id=task_id,
                    progress=95,
                    total=100,
                    message=f"Ansible reported {event_name} for {host}",
                    callback=callback,
                    status=TaskLifecycleStatus.RUNNING,
                    append_event={"event": event_name, "host": host},
                )
            return True

        return handler

    def _next_progress_value(
        self,
        task_id: str,
        *,
        floor: int,
        step: int,
        cap: int,
    ) -> float:
        with self._progress_lock:
            state = self._progress_state.setdefault(task_id, {"progress": floor - step})
            current = min(cap, state["progress"] + step)
            state["progress"] = current
            return float(current)

    def _schedule_progress_update(
        self,
        *,
        task_id: str,
        progress: float,
        total: float,
        message: str,
        callback: ProgressCallback | None,
        status: TaskLifecycleStatus,
        append_event: dict[str, Any] | None = None,
    ) -> None:
        if self._loop is None:
            return
        coroutine = self._emit_progress(
            task_id,
            progress,
            total,
            message,
            callback=callback,
            status=status,
            append_event=append_event,
        )
        asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    async def _emit_progress(
        self,
        task_id: str,
        progress: float,
        total: float,
        message: str,
        *,
        callback: ProgressCallback | None,
        status: TaskLifecycleStatus,
        append_event: dict[str, Any] | None = None,
    ) -> None:
        record = await self.store.get_task(task_id)
        if record is None:
            return
        record.progress = progress
        record.total = total
        record.status = status
        record.status_message = message
        record.updated_at = utc_now()
        if append_event:
            record.events.append(append_event)
        await self.store.save_task(record)
        if callback is not None:
            try:
                await callback(progress, total, message)
            except Exception:
                pass

    async def _monitor_runner(
        self,
        *,
        task_id: str,
        runner: Any,
        thread: Any,
        artifact_dir: Path,
        callback: ProgressCallback | None,
    ) -> None:
        await asyncio.to_thread(thread.join, self.settings.runner_timeout_seconds)
        timed_out = thread.is_alive()
        status = getattr(runner, "status", "failed")
        rc = getattr(runner, "rc", None)
        result_path = artifact_dir / "project" / "result.json"
        result: dict[str, Any] | None = None
        if result_path.exists():
            result = orjson.loads(result_path.read_bytes())
        final_status = (
            TaskLifecycleStatus.COMPLETED
            if not timed_out and status == "successful" and rc == 0
            else TaskLifecycleStatus.FAILED
        )
        final_message = (
            "Workflow completed successfully"
            if final_status == TaskLifecycleStatus.COMPLETED
            else (
                f"Workflow timed out after {self.settings.runner_timeout_seconds}s"
                if timed_out
                else f"Workflow failed with status={status} rc={rc}"
            )
        )
        record = await self.store.get_task(task_id)
        if record is None:
            return
        record.status = final_status
        record.status_message = final_message
        record.progress = 100
        record.updated_at = utc_now()
        record.result = result or {
            "status": status,
            "rc": rc,
            "stdout": str(artifact_dir / "artifacts" / record.runner_ident / "stdout"),
        }
        await self.store.save_task(record)
        if callback is not None:
            try:
                await callback(100, 100, final_message)
            except Exception:
                pass


_engine: RunnerEngine | None = None


def get_runner_engine() -> RunnerEngine:
    global _engine
    if _engine is None:
        _engine = RunnerEngine(get_settings())
    return _engine
