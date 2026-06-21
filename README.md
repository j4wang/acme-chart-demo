# acme-charting-demo

Generates a swimlane process diagram (SVG, with optional PNG export) from a
plain CSV describing process steps, actors, pain points, and the flow
between steps. Built to reproduce a specific hand-drawn diagram style:
lane bands per actor, numbered step boxes, red-highlighted pain points,
and dashed amber loop-back arrows for rejection/rework paths.

## What's in here

```
parser.py      Reads the input CSV into Step / Edge / ProcessModel objects
layout.py      Computes box positions, lane bands, and arrow routing
renderer.py    Turns the model + layout into SVG markup
generate.py    Entry point: ties the above together, writes the SVG (and optionally PNG)
svg_to_png.py  Standalone SVG -> PNG converter, usable independently of generate.py
input.csv      Sample input data (Acme Corp expense reimbursement, current state)
```

## Usage

Generate SVG only:

```
python3 generate.py input.csv output.svg
```

Generate SVG and PNG in one pass:

```
python3 generate.py input.csv output.svg --png output.png
```

Convert an existing SVG to PNG separately:

```
python3 svg_to_png.py output.svg output.png
```

If no arguments are given, `generate.py` defaults to `input.csv` and
`output.svg` in the current directory.

## Input CSV format

The file holds two tables, separated by a single blank row.

**Steps table:**

| Column | Meaning |
|---|---|
| Step Number | Integer, also drives left-to-right ordering in the diagram |
| Process Step | Label shown in the box |
| Actor | Which lane the step belongs to (e.g. Employee, Manager) |
| Node Type | `Step` or `Decision` (both render the same way currently; see Known limitations) |
| Pain Point | If non-empty, the step is styled red and this text is shown as a caption below the box |
| Notes | Free text, not rendered, for context/documentation only |

**Edges table** (header row repeats: `From Step,To Step,Condition,Type,Notes`):

| Column | Meaning |
|---|---|
| From Step / To Step | Step numbers being connected |
| Condition | Optional label shown on the connector (e.g. "Approved", "Rejected") |
| Type | `Normal` for forward flow, `Loop` for a feedback/rejection arrow |
| Notes | For `Loop` edges, the first clause (up to the first period or semicolon) is used as the on-diagram label; for `Normal` edges this is unused |

See `input.csv` for a complete working example.

## Dependencies

No pip packages are required to generate SVG; everything in `parser.py`,
`layout.py`, and `renderer.py` uses only the Python standard library.

PNG export (`svg_to_png.py`, or `generate.py --png`) shells out to the
[`wkhtmltoimage`](https://wkhtmltopdf.org/) command-line tool, which must
be installed separately as a system binary, not via pip.

- macOS: `brew install --cask wkhtmltopdf`
- Debian/Ubuntu: `apt-get install wkhtmltopdf`
- Windows: installer at https://wkhtmltopdf.org/downloads.html

If you don't have `wkhtmltoimage` available, skip `--png` and use the SVG
output directly. Most browsers, design tools, and document editors open
SVG natively.

## Known limitations

- `Decision` node type currently renders identically to `Step` (no diamond
  shape). The reject/flag branch out of a decision is expressed as a
  separate `Loop` edge rather than a second outgoing arrow from a diamond.
- Lane order is hardcoded in `generate.py` (`DEFAULT_LANE_ORDER`). If the
  actors in your CSV don't exactly match that list, the script falls back
  to the order actors first appear in the CSV.
- Diagram title is hardcoded in `generate.py` (`DEFAULT_TITLE`), not yet
  read from the input file.
- No cycle-time bar / duration visualization (intentionally out of scope
  for this version).
- Loop-arrow routing assumes loops travel from a later step back to an
  earlier one and routes them above the lane stack. It hasn't been tested
  with loops that would need to route below.

## Extending

- New visual elements (decision diamonds, additional badge types) go in
  `renderer.py`.
- New layout/routing logic (lanes in custom order, loops routed below
  instead of above, multi-row layouts) goes in `layout.py`.
- New input fields or a different CSV/JSON shape go in `parser.py`.
