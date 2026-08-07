# Paper Figure Device Geometry Recipe

Use this recipe when the user asks to reproduce the geometry of one device from
a specific paper figure, for example "Figure 1 circular loop" or "Figure 1
regular dipole". This is a geometry-first workflow, not a full EM reproduction.

The central rule is simple: build one device per CST project, compare it against
the paper figure, record what is fact versus assumption, and only then move to
the next device.

## Scope

In scope:
- Extracting one device from one paper figure.
- Building a CST MWS geometry project for that one device.
- Adding ports and lumped-element placeholders when the figure shows feed,
  matching, or segmentation components.
- Keeping only the device and matching-circuit geometry that is visible or
  explicitly required by the paper figure. Do not add visual support boards,
  substrates, carriers, or phantom-like solids unless the figure/paper explicitly
  shows or specifies them.
- Producing a reproducible artifact set under `results/<project_id>/`.
- Producing a self-check report comparing the CST model to the paper figure.

Out of scope unless explicitly requested:
- Full tuning or matching to a target S11.
- EM solve, B1+, SAR, shimming, or array performance.
- Multi-device batch builds.
- Author-level exact CAD reconstruction when the paper only shows a schematic.

## Required Inputs

Minimum:
- Paper PDF path.
- Figure number.
- Device name within that figure.

Recommended:
- Whether to build geometry only or also add placeholder electrical elements.
- Whether the user wants CST-native parameters or script-level regeneration.

If the device is ambiguous, ask one compact clarification. Otherwise proceed
with clearly recorded assumptions.

## Required References

Always read:
- `../../driving/artifact-pipeline.md`
- `../../driving/cst-operation-notes.md`
- `../../building-blocks/vba-knowledge/README.md`
- The topology-specific files below.

Topology references:
- Surface loop / rectangular loop / circular loop:
  - `../../building-blocks/vba-knowledge/coil-geometry.md`
  - `../../building-blocks/vba-knowledge/boolean-transform.md`
  - `../../building-blocks/vba-knowledge/ports-monitors-mesh.md`
  - `../../notes/repro-05-single-coil.md`
  - `../../notes/repro-06-fractionated-dipole.md` when using coordinate
    `LumpedElement` across gaps.
- Regular dipole / folded dipole / fractionated dipole / meander:
  - `../../building-blocks/vba-blocks/dipole-build.md` for robust feed-gap and port patterns.
  - `../../notes/repro-06-fractionated-dipole.md` for segmented traces and
    coordinate `LumpedElement`.
  - `../../building-blocks/vba-knowledge/geometry-primitives.md`
  - `../../building-blocks/vba-knowledge/boolean-transform.md`
- Birdcage-like or face-picked lumped capacitors:
  - `../../notes/repro-03-mri-coil.md`
  - `../../pitfalls/mcp-pitfalls.md` for `LumpedFaceElement` pick-edge requirements.

Do not invent CST API names. If an operation is not covered by the references,
grep the official API docs before using it.

## Output Layout

Use one stable project id:

```text
project_id = <paper_short>_<figure>_<device>[_vN]
```

Write:

```text
projects/<project_id>.cst
results/<project_id>/artifacts/generation/
results/<project_id>/artifacts/setup/
results/<project_id>/artifacts/geometry/
results/<project_id>/artifacts/lumped/
results/<project_id>/artifacts/ports/
results/<project_id>/log/
results/<project_id>/output/
```

Required report files:
- `log/<device>_geometry_spec.md`
- `log/cst_readback_counts.txt`
- `output/<device>_status.md`

Recommended evidence files:
- `log/<figure>_<device>_crop.png`
- `output/<device>_topview_spec.png`

## Workflow

### 1. Extract the target figure/device

Render or crop the figure area. If PyMuPDF is installed, use it to create a
high-resolution PNG crop. Store it in `log/` or `tmp/pdfs/...` and cite the
path in the status report.

Record separately:
- Dimensions explicitly shown in the paper.
- Topology facts visible in the figure.
- Electrical labels visible in the figure.
- Missing values.

Never silently convert a label such as `CT`, `CM`, `LT`, or `C` into a numeric
component value. If the value is not in the paper, it is a placeholder.
Never add a substrate/FR4 board just as a visual aid for a loop or antenna
sketch. If a backing material is not part of the paper figure, leave the CST
model as coil conductors plus the shown feed/matching placeholders only.

### 2. Plan the topology before writing VBA

Write a short geometry spec first. It must include:
- Coordinate system and units.
- All paper-derived dimensions.
- All assumptions.
- How many conductors, gaps, feed ports, and lumped elements are expected.
- What will be parameterized at script level versus CST-native parameter level.

For loops, real capacitor gaps are required. A continuous annulus plus colored
markers is not an acceptable reproduction when the figure shows segmented
capacitors.

### 3. Generate artifacts offline

Use the artifact-first pipeline:
- Generate all `.bas` under `results/<project_id>/artifacts/`.
- Prefer a small Python generator for device-specific geometry.
- Keep named blocks small and auditable: setup, geometry, lumped, ports.
- Run `scripts/lint_vba.py --fix results/<project_id>/artifacts`.

Parameterization policy:
- Script-level parameters are acceptable and often more reliable for polygonal
  or curved geometry. Record that changing them requires regenerating artifacts.
- CST-native parameters are required only when the user explicitly needs to edit
  dimensions directly in CST.
- Do not create CST parameters that appear to control geometry if the geometry
  has already been expanded to fixed coordinates. If you do, label them as
  documentation-only in the report.
- Electrical placeholder values such as `CT_placeholder_pF` can be CST-native
  parameters if used directly in `LumpedElement` expressions.

### 4. Execute in CST

Create a new MWS project for this one device. Do not reuse a previous
multi-device project as the target.

Execute:
- setup/materials/parameters block
- geometry block
- lumped-element block, if any
- port block, if any

Save to `projects/<project_id>.cst`.

### 5. Verify more than "no error"

At minimum, run a CST readback VBA snippet:

```vba
Print #1, "shapes=" & CStr(Solid.GetNumberOfShapes())
Print #1, "ports=" & CStr(Solver.GetNumberOfPorts())
```

Also inspect the saved `Model.mod` or equivalent project files for expected
records, for example:
- Number of `With LumpedElement` blocks.
- Number of `SetName "CT_...` and `SetName "CM_...` records.
- Number of ports.
- Expected component/solid names.

If the figure shows 8 capacitors, the report must prove that the model has 8
corresponding gaps/components, not just 8 labels.

### 6. Produce a visual self-check

Generate a simple top-view check sketch from the same parameters used to create
the CST geometry. It does not replace CST screenshots or user review, but it
helps catch obvious topology errors before solving.

The status report must include a table:

```markdown
| Feature | Paper figure | CST model | Status |
|---|---:|---:|---|
| ... | ... | ... | matched / approximate / assumption / missing |
```

### 7. Write the status report

The report must contain:
- File paths.
- Skill references used.
- What was built.
- What changed if this is a new version.
- CST execution result.
- CST readback result.
- Paper-vs-model comparison table.
- Honest remaining issues.
- Whether the model is script-parameterized or CST-native-parameterized.
- Next recommended action.

## Done Criteria

Mark the device geometry as complete only when:
- The CST project was saved.
- L0 lint passed.
- CST execution completed.
- Readback counts are present.
- The expected topology count is proven (for example, gaps/caps/ports).
- PDF-derived facts and assumptions are separated.
- The status report clearly states limitations.

If any of these are missing, mark status as `partial`.

## Anti-Patterns

Do not:
- Build all devices in the figure at once.
- Treat CST execution success as geometry correctness.
- Replace real gaps with colored markers when the figure shows capacitors.
- Add visual FR4/substrate/backing solids when the paper figure does not show or
  specify a substrate.
- Hide missing component values by inventing pF/nH values.
- Mix `DiscretePort` and `DiscreteFacePort` casually in one topology.
- Claim a model is CST-parameterized if the geometry was expanded into fixed
  polygon coordinates.
- Run an expensive solve before the geometry passes the paper comparison gate.

## Example: Hubmann Figure 1 Circular Loop V2

Project:
- `projects/hubmann_circular_loop_v2.cst`

Evidence:
- Paper crop: `tmp/pdfs/hubmann_rendered/figure1_circular_loop_crop.png`
- Top-view self-check: `results/hubmann_circular_loop_v2/output/circular_loop_v2_topview_spec.png`
- Status: `results/hubmann_circular_loop_v2/output/circular_loop_v2_status.md`

Key lessons:
- The first version used a continuous annulus plus markers; this was not enough.
- V2 used eight copper arcs, eight real CT gaps, eight CT `LumpedElement`
  placeholders, two CM placeholders, and one feed port.
- Geometry was script-parameterized, not CST-native geometry-parameterized.
