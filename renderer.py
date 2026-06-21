"""
Renders a ProcessModel + Layout into the final SVG string, matching the
visual style of the original hand-built sample (lane bands, rounded step
boxes, red pain-point styling, dashed loop-back arrows, legend).
"""

import textwrap
from parser import ProcessModel, Step
from layout import (
    Layout, compute_flow_routes, compute_loop_routes,
    MARGIN_X, TITLE_Y, BOX_W, BOX_H, LANE_LABEL_W, LANE_HEIGHT,
)

# ---- Color palette (matches the original sample) ----------------------

COLOR_TEXT_DARK = "#1B2631"
COLOR_STEP_LABEL = "#000000"  # text color for step box labels specifically
COLOR_TEXT_MUTED = "#5D6D7E"
COLOR_BORDER_NORMAL = "#7F8C8D"
COLOR_PAIN_RED = "#FF0436"
COLOR_PAIN_FILL = "#FDEDEC"
COLOR_LOOP_BACK = "#007AFF"
COLOR_LANE_BG_A = "#FBFCFC"
COLOR_LANE_BG_B = "#F4F6F7"
COLOR_LANE_LABEL_BG = "#D6DBDF"
COLOR_LANE_BORDER = "#B3B6B7"

STEP_LABEL_FONT_SIZE = 11
PAIN_LABEL_FONT_SIZE = 10
NUMBER_BADGE_R = 10

CHARS_PER_LINE = 14


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )


def wrap_text(s: str, chars_per_line: int = CHARS_PER_LINE, max_lines: int = 4) -> list:
    lines = textwrap.wrap(s, width=chars_per_line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip() + "..."
    return lines


def render_svg(model: ProcessModel, layout: Layout, title: str) -> str:
    parts = []

    width, height = layout.width, layout.height

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">'
    )
    parts.append(_defs())
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>')
    parts.append(
        f'<text x="{width/2}" y="{TITLE_Y}" font-size="24" font-weight="bold" '
        f'fill="{COLOR_TEXT_DARK}" text-anchor="middle">{esc(title)}</text>'
    )

    parts.append(_render_lanes(layout, width))
    parts.append(_render_steps(model, layout))
    parts.append(_render_flow_arrows(model, layout))
    parts.append(_render_loop_arrows(model, layout))
    parts.append(_render_legend(layout))

    parts.append("</svg>")
    return "\n".join(parts)


def _defs() -> str:
    return """  <defs>
    <marker id="arrow" markerWidth="13" markerHeight="12" refX="11" refY="6" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0,0 L12,6 L0,12 Z" fill="#5D6D7E"/>
    </marker>
    <marker id="arrowRed" markerWidth="15" markerHeight="14" refX="13" refY="7" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0,0 L14,7 L0,14 Z" fill="#C0392B"/>
    </marker>
    <marker id="arrowLoop" markerWidth="15" markerHeight="14" refX="13" refY="7" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0,0 L14,7 L0,14 Z" fill="{loop_color}"/>
    </marker>
  </defs>""".replace("{loop_color}", COLOR_LOOP_BACK)


def _render_lanes(layout: Layout, width: int) -> str:
    out = []
    lane_full_width = width - 2 * MARGIN_X
    for i, lane in enumerate(layout.lanes):
        y = layout.lane_y[lane]
        bg = COLOR_LANE_BG_A if i % 2 == 0 else COLOR_LANE_BG_B
        out.append(
            f'  <rect x="{MARGIN_X}" y="{y}" width="{lane_full_width}" height="{LANE_HEIGHT}" '
            f'fill="{bg}" stroke="{COLOR_LANE_BORDER}" stroke-width="1"/>'
        )
    for i, lane in enumerate(layout.lanes):
        y = layout.lane_y[lane]
        out.append(
            f'  <rect x="{MARGIN_X}" y="{y}" width="{LANE_LABEL_W}" height="{LANE_HEIGHT}" '
            f'fill="{COLOR_LANE_LABEL_BG}" stroke="{COLOR_LANE_BORDER}" stroke-width="1"/>'
        )
        label_cx = MARGIN_X + LANE_LABEL_W / 2
        label_cy = y + LANE_HEIGHT / 2 + 5
        out.append(
            f'  <text x="{label_cx}" y="{label_cy}" font-size="16" font-weight="bold" '
            f'fill="{COLOR_TEXT_DARK}" text-anchor="middle">{esc(lane)}</text>'
        )
    return "\n".join(out)


def _render_steps(model: ProcessModel, layout: Layout) -> str:
    out = []
    for step in model.steps:
        g = layout.geoms[step.number]
        pain = step.is_pain

        fill = COLOR_PAIN_FILL if pain else "#FFFFFF"
        stroke = COLOR_PAIN_RED if pain else COLOR_BORDER_NORMAL
        stroke_w = 2.5 if pain else 1.5

        out.append(
            f'  <rect x="{g.x}" y="{g.y}" width="{g.w}" height="{g.h}" rx="6" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>'
        )

        badge_cx, badge_cy = g.x + 16, g.y + 15
        out.append(
            f'  <circle cx="{badge_cx}" cy="{badge_cy}" r="{NUMBER_BADGE_R}" fill="{COLOR_TEXT_MUTED}"/>'
            f'<text x="{badge_cx}" y="{badge_cy+4}" font-size="11" font-weight="bold" '
            f'fill="#FFF" text-anchor="middle">{step.number}</text>'
        )

        if pain:
            badge2_cx, badge2_cy = g.right - 15, g.y + 13
            out.append(
                f'  <circle cx="{badge2_cx}" cy="{badge2_cy}" r="9" fill="{COLOR_PAIN_RED}"/>'
                f'<text x="{badge2_cx}" y="{badge2_cy+4}" font-size="12" font-weight="bold" '
                f'fill="#FFF" text-anchor="middle">!</text>'
            )

        label_lines = wrap_text(step.label, max_lines=5)
        label_cx = g.cx
        n = len(label_lines)
        line_h = 14
        start_y = g.cy - ((n - 1) * line_h) / 2 + 4
        for li, line in enumerate(label_lines):
            out.append(
                f'  <text x="{label_cx}" y="{start_y + li*line_h}" font-size="{STEP_LABEL_FONT_SIZE}" '
                f'fill="{COLOR_STEP_LABEL}" text-anchor="middle">{esc(line)}</text>'
            )

        if pain:
            pain_lines = wrap_text(step.pain_text, chars_per_line=30, max_lines=3)
            pain_y = g.y + g.h + 18
            for pi, line in enumerate(pain_lines):
                out.append(
                    f'  <text x="{label_cx}" y="{pain_y + pi*13}" font-size="{PAIN_LABEL_FONT_SIZE}" '
                    f'fill="{COLOR_PAIN_RED}" text-anchor="middle">{esc(line)}</text>'
                )

    return "\n".join(out)


def _render_flow_arrows(model: ProcessModel, layout: Layout) -> str:
    out = []
    for route in compute_flow_routes(model, layout):
        if route.same_lane:
            (x1, y1), (x2, y2) = route.points
            out.append(
                f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{COLOR_TEXT_MUTED}" stroke-width="2" marker-end="url(#arrow)"/>'
            )
        else:
            d = _path_d(route.points)
            out.append(
                f'  <path d="{d}" fill="none" stroke="{COLOR_TEXT_MUTED}" '
                f'stroke-width="2" marker-end="url(#arrow)"/>'
            )
        cond = route.edge.condition
        if cond and not route.same_lane:
            # Place the condition label beside the vertical run of the
            # elbow connector, offset to the right so it doesn't sit on
            # top of either box or their pain captions.
            mid_x = route.points[1][0]
            mid_y = (route.points[1][1] + route.points[2][1]) / 2
            out.append(
                f'  <text x="{mid_x + 8}" y="{mid_y}" font-size="10" font-style="italic" '
                f'fill="{COLOR_TEXT_MUTED}" text-anchor="start">{esc(cond)}</text>'
            )
    return "\n".join(out)


def _render_loop_arrows(model: ProcessModel, layout: Layout) -> str:
    out = []
    routes = compute_loop_routes(model, layout)
    for route in routes:
        d = _path_d(route.points)
        out.append(
            f'  <path d="{d}" fill="none" stroke="{COLOR_LOOP_BACK}" stroke-width="2.5" '
            f'stroke-dasharray="2,6" stroke-linecap="round" marker-end="url(#arrowLoop)"/>'
        )
        rail_y = route.points[1][1]
        mid_x = (route.points[0][0] + route.points[-1][0]) / 2
        label_text = wrap_text(route.label, chars_per_line=140, max_lines=1)
        label = label_text[0] if label_text else ""
        out.append(
            f'  <text x="{mid_x}" y="{rail_y - 6}" font-size="11" font-weight="bold" '
            f'fill="{COLOR_LOOP_BACK}" text-anchor="middle">{esc(label)}</text>'
        )
    return "\n".join(out)


def _path_d(points: list) -> str:
    cmds = [f"M {points[0][0]},{points[0][1]}"]
    for (x, y) in points[1:]:
        cmds.append(f"L {x},{y}")
    return " ".join(cmds)


def _render_legend(layout: Layout) -> str:
    y = layout.legend_y
    out = []
    out.append(f'  <text x="{MARGIN_X+130}" y="{y}" font-size="13" font-weight="bold" fill="{COLOR_TEXT_DARK}">Legend:</text>')

    x = MARGIN_X + 210
    out.append(f'  <rect x="{x}" y="{y-13}" width="26" height="17" rx="3" fill="#FFFFFF" stroke="{COLOR_BORDER_NORMAL}" stroke-width="1.5"/>')
    out.append(f'  <text x="{x+35}" y="{y}" font-size="12" fill="{COLOR_TEXT_DARK}">Standard step</text>')

    x = MARGIN_X + 365
    out.append(f'  <rect x="{x}" y="{y-13}" width="26" height="17" rx="3" fill="{COLOR_PAIN_FILL}" stroke="{COLOR_PAIN_RED}" stroke-width="2"/>')
    out.append(f'  <circle cx="{x+26}" cy="{y-10}" r="6" fill="{COLOR_PAIN_RED}"/><text x="{x+26}" y="{y-6.5}" font-size="9" font-weight="bold" fill="#FFF" text-anchor="middle">!</text>')
    out.append(f'  <text x="{x+38}" y="{y}" font-size="12" fill="{COLOR_TEXT_DARK}">Documented pain point</text>')

    x = MARGIN_X + 580
    out.append(f'  <line x1="{x}" y1="{y-5}" x2="{x+50}" y2="{y-5}" stroke="{COLOR_TEXT_MUTED}" stroke-width="2" marker-end="url(#arrow)"/>')
    out.append(f'  <text x="{x+60}" y="{y}" font-size="12" fill="{COLOR_TEXT_DARK}">Process flow</text>')

    x = MARGIN_X + 740
    out.append(f'  <line x1="{x}" y1="{y-5}" x2="{x+50}" y2="{y-5}" stroke="{COLOR_LOOP_BACK}" stroke-width="2.5" stroke-dasharray="2,6" stroke-linecap="round" marker-end="url(#arrowLoop)"/>')
    out.append(f'  <text x="{x+60}" y="{y}" font-size="12" fill="{COLOR_TEXT_DARK}">Rejection / rework loop</text>')

    return "\n".join(out)
