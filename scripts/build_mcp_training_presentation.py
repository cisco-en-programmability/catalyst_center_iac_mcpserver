from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_VERTICAL_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


OUTPUT = Path("Plan_Provision_Validate_MCP_Enabled_Network_Automation.pptx")

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

NAVY = RGBColor(9, 32, 63)
TEAL = RGBColor(9, 142, 154)
CYAN = RGBColor(85, 195, 214)
GOLD = RGBColor(255, 184, 77)
INK = RGBColor(34, 43, 54)
MUTED = RGBColor(86, 99, 115)
PAPER = RGBColor(248, 250, 252)
CARD = RGBColor(240, 245, 248)
WHITE = RGBColor(255, 255, 255)
LINE = RGBColor(210, 220, 230)


def set_background(slide, color=WHITE):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_background_accents(slide, dark: bool = False):
    circle_specs = [
        (-0.7, -0.6, 2.4, CYAN if dark else TEAL, 0.82),
        (11.7, 5.8, 2.5, GOLD if dark else CYAN, 0.88),
        (10.6, -0.8, 1.8, TEAL if dark else GOLD, 0.9),
    ]
    for left, top, size, color, transparency in circle_specs:
        shape = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL, Inches(left), Inches(top), Inches(size), Inches(size)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.fill.transparency = transparency
        shape.line.fill.background()


def add_content_frame(slide, title: str, subtitle: str, section: str | None = None):
    add_background_accents(slide)
    band = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0), Inches(0), SLIDE_W, Inches(0.22)
    )
    band.fill.solid()
    band.fill.fore_color.rgb = TEAL
    band.line.fill.background()

    if section:
        pill = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.72), Inches(0.42), Inches(2.5), Inches(0.42)
        )
        pill.fill.solid()
        pill.fill.fore_color.rgb = CARD
        pill.line.fill.background()
        tf = pill.text_frame
        tf.paragraphs[0].text = section.upper()
        tf.paragraphs[0].font.name = "Aptos"
        tf.paragraphs[0].font.size = Pt(11)
        tf.paragraphs[0].font.bold = True
        tf.paragraphs[0].font.color.rgb = TEAL

    title_box = slide.shapes.add_textbox(Inches(0.72), Inches(0.95), Inches(9.8), Inches(0.7))
    p = title_box.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = title
    run.font.name = "Aptos Display"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = NAVY

    sub_box = slide.shapes.add_textbox(Inches(0.72), Inches(1.58), Inches(10.8), Inches(0.45))
    p = sub_box.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = subtitle
    run.font.name = "Aptos"
    run.font.size = Pt(13)
    run.font.color.rgb = MUTED

    accent = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0.72), Inches(2.0), Inches(1.15), Inches(0.06)
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = GOLD
    accent.line.fill.background()


def add_footer(slide, index: int, total: int):
    footer = slide.shapes.add_textbox(Inches(0.72), Inches(7.0), Inches(12.0), Inches(0.24))
    p = footer.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    run = p.add_run()
    run.text = f"Customer session | {index:02d}/{total:02d}"
    run.font.name = "Aptos"
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED


def add_section_divider(slide, title: str, subtitle: str, kicker: str):
    set_background(slide, NAVY)
    add_background_accents(slide, dark=True)

    strap = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(1.1), Inches(3.0), Inches(0.48)
    )
    strap.fill.solid()
    strap.fill.fore_color.rgb = TEAL
    strap.line.fill.background()
    p = strap.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = kicker.upper()
    run.font.name = "Aptos"
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = WHITE

    title_box = slide.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(10.5), Inches(1.1))
    p = title_box.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = title
    run.font.name = "Aptos Display"
    run.font.size = Pt(30)
    run.font.bold = True
    run.font.color.rgb = WHITE

    sub_box = slide.shapes.add_textbox(Inches(0.9), Inches(3.1), Inches(11.2), Inches(0.8))
    p = sub_box.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = subtitle
    run.font.name = "Aptos"
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(225, 236, 245)

    quote = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(4.7), Inches(11.5), Inches(1.2)
    )
    quote.fill.solid()
    quote.fill.fore_color.rgb = RGBColor(18, 53, 93)
    quote.line.color.rgb = CYAN
    tf = quote.text_frame
    tf.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "Use the next section to turn AI interest into an operating model the customer can trust."
    run.font.name = "Aptos"
    run.font.size = Pt(18)
    run.font.color.rgb = WHITE


def add_card(slide, left, top, width, height, title, body, fill=CARD, title_color=NAVY, body_color=INK):
    shape = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = LINE

    title_box = slide.shapes.add_textbox(
        Inches(left + 0.2), Inches(top + 0.16), Inches(width - 0.4), Inches(0.5)
    )
    p = title_box.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = title
    run.font.name = "Aptos"
    run.font.size = Pt(17)
    run.font.bold = True
    run.font.color.rgb = title_color

    body_box = slide.shapes.add_textbox(
        Inches(left + 0.2), Inches(top + 0.68), Inches(width - 0.4), Inches(height - 0.88)
    )
    tf = body_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = body
    run.font.name = "Aptos"
    run.font.size = Pt(13)
    run.font.color.rgb = body_color
    return shape


def add_bullet_box(slide, left, top, width, height, title, bullets, fill=WHITE):
    add_card(slide, left, top, width, height, title, "", fill=fill)
    body_box = slide.shapes.add_textbox(
        Inches(left + 0.2), Inches(top + 0.62), Inches(width - 0.4), Inches(height - 0.82)
    )
    tf = body_box.text_frame
    tf.word_wrap = True
    for idx, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.text = bullet
        p.font.name = "Aptos"
        p.font.size = Pt(13)
        p.font.color.rgb = INK
        p.level = 0
        p.space_after = Pt(10)


def add_metric_card(slide, left, top, width, height, value, label, note):
    shape = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = WHITE
    shape.line.color.rgb = LINE

    big = slide.shapes.add_textbox(Inches(left + 0.18), Inches(top + 0.16), Inches(width - 0.36), Inches(0.55))
    p = big.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = value
    run.font.name = "Aptos Display"
    run.font.size = Pt(24)
    run.font.bold = True
    run.font.color.rgb = TEAL

    mid = slide.shapes.add_textbox(Inches(left + 0.18), Inches(top + 0.75), Inches(width - 0.36), Inches(0.3))
    p = mid.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = label
    run.font.name = "Aptos"
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = NAVY

    low = slide.shapes.add_textbox(Inches(left + 0.18), Inches(top + 1.08), Inches(width - 0.36), Inches(0.42))
    p = low.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = note
    run.font.name = "Aptos"
    run.font.size = Pt(10)
    run.font.color.rgb = MUTED


def add_process_row(slide, top, steps):
    left = 0.78
    width = 2.35
    gap = 0.38
    for idx, (title, body) in enumerate(steps):
        x = left + idx * (width + gap)
        add_card(slide, x, top, width, 1.85, title, body, fill=WHITE)

        badge = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL, Inches(x + 0.16), Inches(top - 0.16), Inches(0.42), Inches(0.42)
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = TEAL
        badge.line.fill.background()
        p = badge.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = str(idx + 1)
        run.font.name = "Aptos"
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = WHITE

        if idx < len(steps) - 1:
            arrow = slide.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.CHEVRON,
                Inches(x + width + 0.06),
                Inches(top + 0.62),
                Inches(0.22),
                Inches(0.42),
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = GOLD
            arrow.line.fill.background()


def add_architecture_diagram(slide):
    blocks = [
        (0.75, 2.45, 1.9, 1.1, "AI Client", "ChatGPT\nCodex\nMCP client"),
        (2.95, 2.45, 2.0, 1.1, "MCP Server", "FastMCP\nFastAPI\nHTTP/SSE"),
        (5.25, 2.45, 2.15, 1.1, "Translation Layer", "Flat tool input\nTyped models\nSchema control"),
        (7.7, 2.45, 2.0, 1.1, "Execution Engine", "ansible-runner\nrun_async()\nRedis state"),
        (10.0, 2.45, 2.35, 1.1, "Catalyst Center", "cisco.catalystcenter\nworkflow_manager\ncontroller APIs"),
    ]
    for left, top, width, height, title, body in blocks:
        add_card(slide, left, top, width, height, title, body, fill=WHITE)

    for x in [2.68, 4.98, 7.45, 9.74]:
        arrow = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW, Inches(x), Inches(2.82), Inches(0.2), Inches(0.32)
        )
        arrow.fill.solid()
        arrow.fill.fore_color.rgb = GOLD
        arrow.line.fill.background()

    add_metric_card(slide, 0.9, 4.55, 2.7, 1.65, "Stateless", "API layer", "Safe for horizontal scale and tenant isolation")
    add_metric_card(slide, 3.95, 4.55, 2.7, 1.65, "Progress", "Long-running tasks", "taskId, polling, and progressToken updates")
    add_metric_card(slide, 7.0, 4.55, 2.7, 1.65, "Guarded", "Enterprise safety", "Read-only hints, confirmation gates, typed inputs")
    add_metric_card(slide, 10.05, 4.55, 2.3, 1.65, "Ready", "Identity model", "OAuth 2.1 federation-ready design")


def add_translation_visual(slide):
    add_card(
        slide,
        0.9,
        2.35,
        3.75,
        3.15,
        "AI-facing tool input",
        "site_type: building\nname: BLD23\nparent_path: Global/USA/SAN JOSE\nlatitude: 37.39819\nlongitude: -121.91297\nrf_model: Cubes And Walled Offices",
        fill=WHITE,
    )

    arrow = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.CHEVRON, Inches(4.95), Inches(3.5), Inches(0.42), Inches(0.58)
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = GOLD
    arrow.line.fill.background()

    add_card(
        slide,
        5.65,
        2.35,
        3.1,
        3.15,
        "Translation layer",
        "Pydantic models validate inputs.\nTransformers rebuild the nested config expected by workflow_manager modules.\nThe LLM never has to invent the Cisco payload shape.",
        fill=CARD,
    )

    arrow = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.CHEVRON, Inches(9.02), Inches(3.5), Inches(0.42), Inches(0.58)
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = GOLD
    arrow.line.fill.background()

    add_card(
        slide,
        9.72,
        2.35,
        2.65,
        3.15,
        "Module payload",
        "config:\n- site:\n    building:\n      name: BLD23\n      parent_name: Global/USA/SAN JOSE\n      latitude: 37.39819\n      longitude: -121.91297\n  type: building",
        fill=WHITE,
    )

    add_card(
        slide,
        0.9,
        5.8,
        11.45,
        0.78,
        "Why customers care",
        "Flat schemas reduce AI error rates, improve repeatability, and let teams keep their existing Ansible content exactly where it already works.",
        fill=RGBColor(231, 247, 248),
        title_color=TEAL,
    )


def add_prompt_examples(slide):
    add_card(
        slide,
        0.9,
        2.25,
        5.4,
        3.95,
        "What the operator says",
        "Pull the site hierarchy under Global/USA/SAN JOSE as YAML.\n\nReapply this config using site_workflow_manager.\n\nCreate SAMPLE with one building and two floors.\n\nShow me the task logs.",
        fill=WHITE,
    )
    add_card(
        slide,
        6.65,
        2.25,
        5.7,
        3.95,
        "What the AI must do",
        "1. Choose a config generator for pull operations.\n2. Convert user intent into flat MCP tool inputs.\n3. Submit long-running tasks and return a taskId.\n4. Poll /tasks/get and present logs and artifacts.\n5. Re-pull state for validation after change.",
        fill=CARD,
    )


def add_code_card(slide, left, top, width, height, title, code, fill=WHITE):
    shape = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = LINE

    title_box = slide.shapes.add_textbox(
        Inches(left + 0.2), Inches(top + 0.16), Inches(width - 0.4), Inches(0.45)
    )
    p = title_box.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = title
    run.font.name = "Aptos"
    run.font.size = Pt(16)
    run.font.bold = True
    run.font.color.rgb = NAVY

    code_box = slide.shapes.add_textbox(
        Inches(left + 0.2), Inches(top + 0.62), Inches(width - 0.4), Inches(height - 0.82)
    )
    tf = code_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = code
    run.font.name = "Courier New"
    run.font.size = Pt(10)
    run.font.color.rgb = INK


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, NAVY)
    add_background_accents(slide, dark=True)

    strap = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.78), Inches(0.72), Inches(3.25), Inches(0.42)
    )
    strap.fill.solid()
    strap.fill.fore_color.rgb = TEAL
    strap.line.fill.background()
    p = strap.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "45-MINUTE CUSTOMER SESSION"
    run.font.name = "Aptos"
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = WHITE

    title = slide.shapes.add_textbox(Inches(0.78), Inches(1.45), Inches(8.8), Inches(1.35))
    p = title.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = "Plan, Provision, Validate:\nMCP-Enabled Network Automation"
    run.font.name = "Aptos Display"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = WHITE

    sub = slide.shapes.add_textbox(Inches(0.82), Inches(3.02), Inches(8.6), Inches(0.8))
    p = sub.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = (
        "How to expose existing Ansible, Terraform, and Python automation as safe AI-callable tools "
        "without rewriting what already works."
    )
    run.font.name = "Aptos"
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(226, 235, 242)

    callout = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(8.95), Inches(1.2), Inches(3.4), Inches(4.8)
    )
    callout.fill.solid()
    callout.fill.fore_color.rgb = RGBColor(18, 53, 93)
    callout.line.color.rgb = CYAN

    add_metric_card(slide, 9.2, 1.55, 2.9, 1.35, "No rewrites", "Keep current automation", "Wrap what exists instead of starting over")
    add_metric_card(slide, 9.2, 3.0, 2.9, 1.35, "Predictable AI", "Tool contracts", "Schemas, task IDs, and guardrails create trust")
    add_metric_card(slide, 9.2, 4.45, 2.9, 1.35, "Closed loop", "Plan to validation", "Export, provision, validate, and capture artifacts")

    audience = slide.shapes.add_textbox(Inches(0.82), Inches(5.4), Inches(7.1), Inches(0.7))
    p = audience.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = "Audience: NetOps leaders, platform teams, automation architects, and customer engineering teams"
    run.font.name = "Aptos"
    run.font.size = Pt(13)
    run.font.color.rgb = RGBColor(226, 235, 242)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Executive Summary", "The three messages the customer should leave with", section="Opening")
    add_metric_card(slide, 0.9, 2.55, 3.7, 1.85, "1", "You already own the automation", "Ansible playbooks, Terraform plans, and SDK scripts remain the system of execution.")
    add_metric_card(slide, 4.82, 2.55, 3.7, 1.85, "2", "MCP is the control contract", "It gives AI a typed, discoverable, governable way to invoke those assets.")
    add_metric_card(slide, 8.74, 2.55, 3.7, 1.85, "3", "Plan-Provision-Validate becomes one loop", "The same toolchain can export state, apply change, and verify the outcome.")
    add_card(
        slide,
        0.9,
        4.85,
        11.45,
        1.15,
        "Suggested time split",
        "10 minutes on the operating model, 15 minutes on server architecture, 10 minutes on the live demo, 10 minutes for customer questions and rollout discussion.",
        fill=WHITE,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Why This Matters Now", "Most enterprise teams have automation assets, but not a clean orchestration boundary", section="Context")
    add_bullet_box(
        slide,
        0.9,
        2.3,
        5.4,
        3.8,
        "What teams already have",
        [
            "Ansible playbooks for provisioning and brownfield collection",
            "Terraform plans for cloud edge, compute, and platform resources",
            "Python SDK scripts for edge cases and API gaps",
            "Validation jobs in pyATS, Genie, or custom test harnesses",
        ],
        fill=WHITE,
    )
    add_bullet_box(
        slide,
        6.55,
        2.3,
        5.8,
        3.8,
        "What still breaks down",
        [
            "Inputs are inconsistent across tools and handoffs",
            "Operators translate intent manually between plan and execution",
            "Change and validation are often disconnected",
            "AI assistants cannot safely orchestrate scripts without a contract",
        ],
        fill=WHITE,
    )
    add_card(
        slide,
        0.9,
        6.25,
        11.45,
        0.62,
        "Key message",
        "The gap is no longer automation coverage. The gap is a reliable interface that connects automation, AI, and operator trust.",
        fill=RGBColor(231, 247, 248),
        title_color=TEAL,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "From Tool Sprawl to Operating Model", "What changes when MCP becomes the boundary layer", section="Model")
    add_bullet_box(
        slide,
        0.9,
        2.3,
        5.2,
        3.85,
        "Before MCP",
        [
            "Operators choose among scripts, playbooks, and notebooks",
            "Every handoff requires format conversion or tribal knowledge",
            "AI outputs text, but not safely executable operations",
            "Logging and artifacts are inconsistent across tools",
        ],
        fill=WHITE,
    )
    add_bullet_box(
        slide,
        7.0,
        2.3,
        5.35,
        3.85,
        "With MCP",
        [
            "AI discovers tools with typed schemas and clear descriptions",
            "The server translates flat intent into automation-native payloads",
            "Every long-running job returns a taskId and progress events",
            "Validation and artifacts are part of the workflow, not an afterthought",
        ],
        fill=CARD,
    )
    arrow = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW, Inches(6.2), Inches(3.8), Inches(0.48), Inches(0.55)
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = GOLD
    arrow.line.fill.background()

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "What MCP Is, and What It Is Not", "Set the customer's mental model early", section="Model")
    add_bullet_box(
        slide,
        0.9,
        2.25,
        5.45,
        3.95,
        "MCP is",
        [
            "A protocol for exposing tools, prompts, and resources to AI systems",
            "A way to standardize tool discovery, invocation, and outputs",
            "A boundary that lets you wrap proven automation instead of replacing it",
            "A practical path to compose export, provision, and validation steps",
        ],
        fill=WHITE,
    )
    add_bullet_box(
        slide,
        6.65,
        2.25,
        5.7,
        3.95,
        "MCP is not",
        [
            "A replacement for Ansible, Terraform, or Python",
            "A license to let an LLM invent controller payloads on its own",
            "A shortcut around approvals, validation, or auditability",
            "A reason to rewrite working automation from scratch",
        ],
        fill=WHITE,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "The Critical Design Pattern", "Flatten the AI boundary, hide the nested automation payloads", section="Model")
    add_translation_visual(slide)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_divider(
        slide,
        "Architecture and Runtime",
        "Move from concept to implementation: transport, tasks, translation, and execution.",
        "Part 2",
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Catalyst Center MCP Server Architecture", "The implementation pattern behind this customer-ready reference server", section="Architecture")
    add_architecture_diagram(slide)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Tool Surface: High-Level and Full-Fidelity", "Use specialized tools for common workflows and generic wrappers for collection coverage", section="Architecture")
    add_metric_card(slide, 0.9, 2.25, 2.4, 1.65, "45", "Total MCP tools", "Current implementation count exposed by the server")
    add_metric_card(slide, 3.55, 2.25, 2.4, 1.65, "6", "Specialized tools", "Opinionated tools with flat arguments for common tasks")
    add_metric_card(slide, 6.2, 2.25, 2.4, 1.65, "39", "Generic tools", "One wrapper per installed workflow_manager module")
    add_metric_card(slide, 8.85, 2.25, 3.5, 1.65, "Preferred pattern", "Start specialized, fall back generic", "Give the AI the simplest safe tool first, then full module access when needed")
    add_bullet_box(
        slide,
        0.9,
        4.25,
        5.55,
        2.2,
        "Specialized tools in this server",
        [
            "provision_site and delete_site",
            "deploy_template",
            "onboard_fabric_devices and reprovision_fabric_device",
            "manage_assurance_issues",
        ],
        fill=WHITE,
    )
    add_bullet_box(
        slide,
        6.8,
        4.25,
        5.55,
        2.2,
        "Generic workflow families",
        [
            "Site, template, inventory, discovery, and network settings",
            "SD-Access fabric sites, devices, virtual networks, transits, and host onboarding",
            "Assurance, backup, reports, SWIM, user-role, wired campus automation, and more",
        ],
        fill=CARD,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Long-Running Task Lifecycle", "The November 2025 task primitive is what makes AI automation operationally usable", section="Architecture")
    add_process_row(
        slide,
        2.45,
        [
            ("Submit", "Tool returns taskId and status=submitted immediately."),
            ("Execute", "ansible-runner starts asynchronously with workflow_manager inputs."),
            ("Track", "Progress updates flow through progressToken and Redis state."),
            ("Poll", "Client calls /tasks/get until the run completes or fails."),
        ],
    )
    add_card(
        slide,
        0.9,
        5.05,
        11.45,
        1.15,
        "Operational value",
        "This pattern keeps the UI responsive, supports brownfield jobs that take minutes, and gives operators a reliable place to inspect logs, artifacts, and final controller results.",
        fill=WHITE,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Enterprise Guardrails", "Customer readiness depends on control boundaries, not just code coverage", section="Architecture")
    add_metric_card(slide, 0.9, 2.35, 2.65, 1.75, "Typed", "Input controls", "Python type hints, Literal, and Enum constrain the tool surface")
    add_metric_card(slide, 3.75, 2.35, 2.65, 1.75, "Read-only", "Config generation", "Export tools should be clearly marked and preferred for pull operations")
    add_metric_card(slide, 6.6, 2.35, 2.65, 1.75, "Confirmed", "Destructive operations", "delete_site and reprovision flows require explicit human confirmation")
    add_metric_card(slide, 9.45, 2.35, 2.9, 1.75, "Auditable", "State and artifacts", "Redis state plus ansible-runner artifacts preserve execution history")
    add_bullet_box(
        slide,
        0.9,
        4.45,
        11.45,
        1.95,
        "Architecture guardrails to call out verbally",
        [
            "Use HTTP/SSE for multi-tenant delivery and disable proxy buffering.",
            "Keep the API layer stateless so instances can scale horizontally.",
            "Design for OAuth 2.1 identity federation even if the first lab uses local credentials.",
            "Treat tool schema quality with the same discipline as API design quality.",
        ],
        fill=WHITE,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Multi-Tenant and Security Model", "A customer-ready server must isolate credentials, identity, and execution context", section="Architecture")
    add_code_card(
        slide,
        0.9,
        2.25,
        5.55,
        3.95,
        "Credential scoping pattern",
        "CATALYSTCENTER_HOST=catc1.example.com\nCATALYSTCENTER_USERNAME=admin\nCATALYSTCENTER_PASSWORD=secret\n\nCATALYSTCENTER_ACME_HOST=acme-catc.example.com\nCATALYSTCENTER_ACME_USERNAME=svc-acme\nCATALYSTCENTER_ACME_PASSWORD=acme-secret\n\nawait call_tool(\"provision_site\", {\"tenant_id\": \"acme\", ...})",
        fill=WHITE,
    )
    add_bullet_box(
        slide,
        6.8,
        2.25,
        5.55,
        3.95,
        "Production controls",
        [
            "Optional OAuth and JWT validation with JWKS-based trust",
            "Tenant isolation through per-tenant credential scoping",
            "External secret-management friendly: vault or cloud secret stores",
            "TLS termination at the reverse proxy with proxy buffering disabled for SSE",
            "Configurable SSL verification per tenant and auditable artifacts per task",
        ],
        fill=CARD,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "What We Proved in the Lab", "Concrete evidence makes the story more credible with customers", section="Architecture")
    add_metric_card(slide, 0.9, 2.35, 2.6, 1.7, "45", "MCP tools exposed", "Specialized tools plus generic workflow_manager wrappers")
    add_metric_card(slide, 3.8, 2.35, 2.6, 1.7, "8/8", "Tests passing", "Server, transformers, and task contract validation")
    add_metric_card(slide, 6.7, 2.35, 2.6, 1.7, "Live", "Controller validation", "Export, reapply, create, and task log inspection executed")
    add_metric_card(slide, 9.6, 2.35, 2.75, 1.7, "Idempotent", "site_workflow_manager", "Reapplying existing SAN JOSE state produced no changes")
    add_bullet_box(
        slide,
        0.9,
        4.45,
        11.45,
        1.95,
        "Real examples already exercised",
        [
            "Pulled the Global/USA/SAN JOSE hierarchy into YAML using a config generator flow.",
            "Reapplied the generated site hierarchy and received changed=false on the live controller.",
            "Created a SAMPLE area with one building and two floors, then inspected the ansible-runner logs and result artifacts.",
        ],
        fill=WHITE,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_section_divider(
        slide,
        "Demo and Customer Conversation",
        "Use the live workflow to connect the architecture story to something the customer can repeat.",
        "Part 3",
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Training Use Case: Campus Build-Out", "A realistic workflow that shows where MCP helps and where Ansible still does the work", section="Demo")
    add_process_row(
        slide,
        2.45,
        [
            ("Sites", "Create the hierarchy for area, building, and floor objects."),
            ("Settings", "Apply DNS, NTP, DHCP, SNMP, or syslog through network settings workflows."),
            ("Discover", "Run discovery and inventory onboarding before intent provisioning."),
            ("Fabric", "Onboard border, edge, and control-plane roles into SD-Access."),
        ],
    )
    add_bullet_box(
        slide,
        0.9,
        5.0,
        11.45,
        1.45,
        "Why it lands well with customers",
        [
            "It starts from familiar day-0 and day-1 activities, then shows how MCP lets AI orchestrate those steps without replacing the underlying playbooks.",
        ],
        fill=WHITE,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Training Use Case: Day-2 Operations", "Use the same MCP pattern for compliance, remediation, and assurance-driven operations", section="Demo")
    add_process_row(
        slide,
        2.45,
        [
            ("Check", "Run network compliance or backup workflows asynchronously."),
            ("Assess", "Poll task results and identify non-compliant devices or failed intents."),
            ("Remediate", "Deploy a remediation template or re-run a bounded provisioning step."),
            ("Resolve", "Update assurance issues and revalidate the final state."),
        ],
    )
    add_bullet_box(
        slide,
        0.9,
        5.0,
        11.45,
        1.45,
        "Key message",
        [
            "MCP is not just for greenfield provisioning. It is a practical wrapper for day-2 network operations where evidence, polling, and repeatability matter even more.",
        ],
        fill=WHITE,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Recommended Demo Storyboard", "A four-step sequence that shows planning, provisioning, and validation without unnecessary risk", section="Demo")
    add_process_row(
        slide,
        2.45,
        [
            ("Generate", "Export the SAN JOSE site hierarchy as reusable YAML."),
            ("Reapply", "Submit the same config through site_workflow_manager and prove idempotency."),
            ("Create", "Ask for a new SAMPLE hierarchy from natural language intent."),
            ("Inspect", "Show taskId polling, logs, and the final module result."),
        ],
    )
    add_card(
        slide,
        0.9,
        5.05,
        11.45,
        1.15,
        "What the audience should notice",
        "The AI is not free-styling controller payloads. It is selecting explicit tools, using typed inputs, and presenting stateful operational evidence.",
        fill=RGBColor(231, 247, 248),
        title_color=TEAL,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Prompt-to-Tool Behavior", "Show customers how natural language maps to safe execution", section="Demo")
    add_prompt_examples(slide)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "AI Usage Pattern to Recommend", "Keep the agent inside a bounded loop", section="Demo")
    add_process_row(
        slide,
        2.45,
        [
            ("Plan", "Use read-only generators and inventory pulls to collect current state."),
            ("Normalize", "Convert intent into flat tool inputs and validated schemas."),
            ("Apply", "Run workflow_manager tools through ansible-runner with task tracking."),
            ("Validate", "Re-pull state or run checks before declaring success."),
        ],
    )
    add_bullet_box(
        slide,
        0.9,
        5.0,
        11.45,
        1.45,
        "Operating rule",
        [
            "For pull operations or reusable data-file generation, prefer config generator tools. For desired-state change, prefer workflow_manager tools. For destructive operations, require explicit human approval.",
        ],
        fill=WHITE,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Customer Adoption Path", "A practical rollout plan instead of a large transformation program", section="Close")
    add_metric_card(slide, 0.9, 2.45, 3.6, 1.85, "30 days", "Start small", "Expose one generator/export tool and one idempotent apply tool")
    add_metric_card(slide, 4.85, 2.45, 3.6, 1.85, "60 days", "Close the loop", "Add validation, task polling, and artifact inspection for each flow")
    add_metric_card(slide, 8.8, 2.45, 3.55, 1.85, "90 days", "Scale deliberately", "Expand coverage by domain and keep approvals around destructive boundaries")
    add_card(
        slide,
        0.9,
        4.85,
        11.45,
        1.25,
        "Best first use case",
        "Pick a brownfield workflow where customers already distrust manual handoffs: export current state, reapply to prove idempotency, then introduce one small controlled change.",
        fill=WHITE,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "Deployment and AI Integration", "Give customers a credible path from lab demo to production consumption", section="Close")
    add_bullet_box(
        slide,
        0.9,
        2.25,
        5.55,
        4.0,
        "Deployment options",
        [
            "Local development with uvicorn server:app --reload",
            "Production behind a reverse proxy with multiple workers and Redis",
            "Containerized deployment with the hardened Dockerfile in this repo",
            "Kubernetes-ready pattern with stateless replicas and externalized secrets",
        ],
        fill=WHITE,
    )
    add_code_card(
        slide,
        6.8,
        2.25,
        5.55,
        4.0,
        "AI client integration pattern",
        "\"mcpServers\": {\n  \"catalyst-center\": {\n    \"url\": \"http://localhost:8000/mcp\",\n    \"transport\": \"http\"\n  }\n}\n\nGET /healthz\nGET /tasks/get/{task_id}",
        fill=CARD,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, PAPER)
    add_content_frame(slide, "What Customers Leave With", "Concrete assets they can reuse immediately", section="Close")
    add_bullet_box(
        slide,
        0.9,
        2.3,
        5.7,
        3.9,
        "Reusable technical assets",
        [
            "server.py for the FastMCP and FastAPI entry point",
            "runner_engine.py for ansible-runner execution and Redis-backed task state",
            "transformers.py for flat-to-nested schema translation",
            "Dockerfile for a hardened non-root deployment image",
        ],
        fill=WHITE,
    )
    add_bullet_box(
        slide,
        6.9,
        2.3,
        5.45,
        3.9,
        "Reusable operating patterns",
        [
            "How to separate generator/export tools from apply tools",
            "How to model long-running tasks and polling cleanly",
            "How to add destructive confirmation boundaries",
            "How to keep AI orchestration predictable without rewriting automation",
        ],
        fill=CARD,
    )

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_background(slide, NAVY)
    add_background_accents(slide, dark=True)
    title = slide.shapes.add_textbox(Inches(0.9), Inches(1.5), Inches(10.0), Inches(1.0))
    p = title.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = "Q&A"
    run.font.name = "Aptos Display"
    run.font.size = Pt(32)
    run.font.bold = True
    run.font.color.rgb = WHITE

    quote = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(2.7), Inches(11.5), Inches(2.0)
    )
    quote.fill.solid()
    quote.fill.fore_color.rgb = RGBColor(18, 53, 93)
    quote.line.color.rgb = CYAN
    tf = quote.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = (
        "You do not need to rewrite your automation to make it AI-usable.\n"
        "You need a reliable tool contract, a safe runtime, and a validation loop."
    )
    run.font.name = "Aptos Display"
    run.font.size = Pt(24)
    run.font.bold = True
    run.font.color.rgb = WHITE

    close = slide.shapes.add_textbox(Inches(0.9), Inches(5.35), Inches(11.0), Inches(0.7))
    p = close.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "Plan, Provision, Validate with MCP-enabled automation"
    run.font.name = "Aptos"
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(226, 235, 242)

    total = len(prs.slides)
    for index, built_slide in enumerate(prs.slides, start=1):
        add_footer(built_slide, index, total)

    prs.save(OUTPUT)


if __name__ == "__main__":
    build()
