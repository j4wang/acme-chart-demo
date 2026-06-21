"""
Parses a two-table CSV (steps table + edges table, separated by a blank row)
into structured Step and Edge objects for the swimlane diagram renderer.

Expected CSV shape:

    Step Number,Process Step,Actor,Node Type,Pain Point,Notes
    1,Employee incurs an expense,Employee,Step,,
    ...
    <blank row>
    From Step,To Step,Condition,Type,Notes
    1,2,,Normal,
    6,5,Rejected,Loop,Manager rejects...
    ...
"""

from dataclasses import dataclass, field
from typing import Optional
import csv


@dataclass
class Step:
    number: int
    label: str
    actor: str
    node_type: str          # "Step" or "Decision" (decision rendered same as step, see renderer)
    pain_text: str = ""
    notes: str = ""

    @property
    def is_pain(self) -> bool:
        return bool(self.pain_text.strip())


@dataclass
class Edge:
    from_step: int
    to_step: int
    condition: str = ""
    edge_type: str = "Normal"   # "Normal" or "Loop"
    notes: str = ""

    @property
    def is_loop(self) -> bool:
        return self.edge_type.strip().lower() == "loop"


@dataclass
class ProcessModel:
    steps: list[Step] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    lanes: list[str] = field(default_factory=list)  # actor names, in first-seen order

    def step_by_number(self, n: int) -> Step:
        for s in self.steps:
            if s.number == n:
                return s
        raise KeyError(f"No step numbered {n}")

    def normal_edges(self) -> list[Edge]:
        return [e for e in self.edges if not e.is_loop]

    def loop_edges(self) -> list[Edge]:
        return [e for e in self.edges if e.is_loop]


def parse_csv(path: str) -> ProcessModel:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    # Find the blank row that separates the steps table from the edges table.
    split_idx = None
    for i, row in enumerate(rows):
        if all(cell.strip() == "" for cell in row):
            split_idx = i
            break
    if split_idx is None:
        raise ValueError("Could not find blank separator row between steps and edges tables")

    steps_rows = rows[1:split_idx]            # skip header row at index 0
    edges_rows = rows[split_idx + 2:]         # skip blank row + edges header row

    model = ProcessModel()
    seen_actors: list[str] = []

    for row in steps_rows:
        if not row or not row[0].strip():
            continue
        number = int(row[0].strip())
        label = row[1].strip()
        actor = row[2].strip()
        node_type = row[3].strip() or "Step"
        pain_text = row[4].strip() if len(row) > 4 else ""
        notes = row[5].strip() if len(row) > 5 else ""

        model.steps.append(Step(
            number=number,
            label=label,
            actor=actor,
            node_type=node_type,
            pain_text=pain_text,
            notes=notes,
        ))
        if actor not in seen_actors:
            seen_actors.append(actor)

    for row in edges_rows:
        if not row or not row[0].strip():
            continue
        from_step = int(row[0].strip())
        to_step = int(row[1].strip())
        condition = row[2].strip() if len(row) > 2 else ""
        edge_type = row[3].strip() if len(row) > 3 else "Normal"
        notes = row[4].strip() if len(row) > 4 else ""

        model.edges.append(Edge(
            from_step=from_step,
            to_step=to_step,
            condition=condition,
            edge_type=edge_type,
            notes=notes,
        ))

    model.lanes = seen_actors
    return model


if __name__ == "__main__":
    import sys
    m = parse_csv(sys.argv[1] if len(sys.argv) > 1 else "input.csv")
    print(f"Lanes: {m.lanes}")
    print(f"Steps: {len(m.steps)}")
    for s in m.steps:
        flag = " [PAIN]" if s.is_pain else ""
        print(f"  {s.number}. ({s.actor}){flag} {s.label}")
    print(f"Edges: {len(m.edges)}")
    for e in m.edges:
        kind = "LOOP " if e.is_loop else "flow "
        print(f"  {kind}{e.from_step} -> {e.to_step}  [{e.condition}]")
