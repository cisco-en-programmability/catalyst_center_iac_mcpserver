from __future__ import annotations

import re
import sys
from pathlib import Path


README_PATH = Path(__file__).resolve().parents[1] / "README.md"

LOCAL_PATH_PATTERN = re.compile(
    r"\]\(((?:/Users/|/home/|/tmp/|[A-Za-z]:[\\/])[^)]+)\)"
)
STALE_PATTERNS = (
    re.compile(r"\bTOOLS\.md\b"),
    re.compile(r"pip install -r requirements\.txt"),
)


def _line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def main() -> int:
    text = README_PATH.read_text(encoding="utf-8")
    failures: list[str] = []

    for match in LOCAL_PATH_PATTERN.finditer(text):
        failures.append(
            f"README.md:{_line_number(text, match.start())} contains a local filesystem link: {match.group(1)}"
        )

    for pattern in STALE_PATTERNS:
        for match in pattern.finditer(text):
            failures.append(
                f"README.md:{_line_number(text, match.start())} contains stale text matching `{pattern.pattern}`"
            )

    if failures:
        print("README hygiene check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("README hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
