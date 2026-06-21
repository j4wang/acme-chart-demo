"""
Computes pixel geometry for a ProcessModel: lane y-positions, step box
x/y positions, and routing paths for normal flow arrows and loop-back
arrows. Pure layout math, no SVG string-building here -- that lives in
renderer.py.
"""

from dataclasses import dataclass
from parser import ProcessModel, Step, Edge

# ---- Layout constants (mirrors the proportions of the original sample) ----

MARGIN_X = 20
TITLE_Y = 38
LOOP_RAIL_ZONE = 70   # vertical space reserved above the lanes for loop-back arrows + labels
LANES_TOP = 60 + LOOP_RAIL_ZONE
LANE_LABEL_W = 125
LANE_HEIGHT = 170

BOX_W = 135
BOX_H = 70
COL_GAP = 25          # gap between boxes in the same lane sequence
COL_PITCH = BOX_W + COL_GAP + 0  # left-edge-to-left-edge distance per sequence slot
COL_START_X = LANE_LABEL_W + MARGIN_X + 15  # first box's left edge

LEGEND_TOP_PAD = 60   # space below last lane before legend
FOOTER_H = 0          # cycle-time bar intentionally omitted in this version


@dataclass
class StepGeometry:
    step: Step
    x: float
    y: float
    w: float = BOX_W
    h: float = BOX_H
    col: int = 0
    lane_index: int = 0

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def left(self) -> float:
        return self.x


@dataclass
class Layout:
    lanes: list[str]
    lane_y: dict
    geoms: dict
    width: int
    height: int
    legend_y: int


def compute_layout(model: ProcessModel, lane_order: list[str] | None = None) -> Layout:
    lanes = lane_order if lane_order else model.lanes
    lane_y = {lane: LANES_TOP + i * LANE_HEIGHT for i, lane in enumerate(lanes)}

    # Sequence position = order steps appear in the steps list (their
    # natural process order), independent of which lane they sit in.
    # This matches the original sample's convention: column position is
    # global step order, not a per-lane counter.
    geoms: dict[int, StepGeometry] = {}
    for col, step in enumerate(model.steps):
        lane_index = lanes.index(step.actor)
        x = COL_START_X + col * COL_PITCH
        y = lane_y[step.actor] + (LANE_HEIGHT - BOX_H) / 2
        geoms[step.number] = StepGeometry(
            step=step, x=x, y=y, col=col, lane_index=lane_index
        )

    n_cols = len(model.steps)
    width = int(COL_START_X + (n_cols - 1) * COL_PITCH + BOX_W + MARGIN_X + 15)
    lanes_bottom = LANES_TOP + len(lanes) * LANE_HEIGHT
    legend_y = lanes_bottom + LEGEND_TOP_PAD
    height = legend_y + 140

    return Layout(
        lanes=lanes,
        lane_y=lane_y,
        geoms=geoms,
        width=width,
        height=height,
        legend_y=legend_y,
    )


# ---- Arrow routing ----------------------------------------------------

@dataclass
class FlowRoute:
    edge: Edge
    same_lane: bool
    points: list

    def __init__(self, edge, same_lane, points):
        self.edge = edge
        self.same_lane = same_lane
        self.points = points


@dataclass
class LoopRoute:
    edge: Edge
    points: list
    label: str

    def __init__(self, edge, points, label):
        self.edge = edge
        self.points = points
        self.label = label


def compute_flow_routes(model: ProcessModel, layout: Layout) -> list:
    routes = []
    for e in model.normal_edges():
        g_from = layout.geoms[e.from_step]
        g_to = layout.geoms[e.to_step]
        same_lane = g_from.lane_index == g_to.lane_index

        if same_lane:
            points = [(g_from.right, g_from.cy), (g_to.left, g_to.cy)]
        else:
            mid_x = g_from.right + 5
            points = [
                (g_from.right, g_from.cy),
                (mid_x, g_from.cy),
                (mid_x, g_to.cy),
                (g_to.left, g_to.cy),
            ]
        routes.append(FlowRoute(edge=e, same_lane=same_lane, points=points))
    return routes


def compute_loop_routes(model: ProcessModel, layout: Layout) -> list:
    """
    Routes each loop edge as a rectilinear path that exits the top of
    the source box, travels above all lanes, and re-enters the top of
    the target box. Multiple loops are stacked at increasing heights
    above the lane band so their rails don't overlap.

    If two or more loops share the same target box, their landing
    points are spread out across that box's top edge (instead of all
    converging on its exact center) so the arrowheads and incoming
    lines don't stack on top of each other.
    """
    routes = []
    rail_top = TITLE_Y + 22
    rail_bottom = LANES_TOP - 12
    loop_edges = model.loop_edges()
    n_loops = max(len(loop_edges), 1)
    rail_spacing = (rail_bottom - rail_top) / n_loops

    # Figure out how many loops land on each target step, so shared
    # targets can be spread across the box's top edge instead of all
    # landing at the exact same point.
    targets_seen: dict = {}
    target_counts: dict = {}
    for e in loop_edges:
        target_counts[e.to_step] = target_counts.get(e.to_step, 0) + 1

    LANDING_SPREAD = 18  # px between landing points when a box has multiple incoming loops

    for i, e in enumerate(loop_edges):
        g_from = layout.geoms[e.from_step]
        g_to = layout.geoms[e.to_step]

        rail_y = rail_top + (i * rail_spacing) + rail_spacing / 2

        # Compute this loop's landing x-offset on the target box. The
        # first loop to a given target lands left of center, the next
        # one right of center, etc., centered around the box midpoint.
        count = target_counts[e.to_step]
        seen = targets_seen.get(e.to_step, 0)
        targets_seen[e.to_step] = seen + 1
        landing_x = g_to.cx + (seen - (count - 1) / 2) * LANDING_SPREAD

        points = [
            (g_from.cx, g_from.y),
            (g_from.cx, rail_y),
            (landing_x, rail_y),
            (landing_x, g_to.y),
        ]

        condition = f"{e.condition}: " if e.condition else ""
        # Keep only the first clause of the notes (up to the first
        # period or semicolon) so the rail caption stays a single
        # readable line, matching the concise style of the original
        # sample's loop labels. Full notes remain available on the
        # Edge object for anyone inspecting the model directly.
        first_clause = e.notes.split(".")[0].split(";")[0].strip() if e.notes else ""
        label = f"{condition}{first_clause}" if first_clause else (e.condition or "")
        routes.append(LoopRoute(edge=e, points=points, label=label))

    return routes
