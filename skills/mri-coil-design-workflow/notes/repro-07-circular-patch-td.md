# Repro 07: Circular Patch Antenna TD

## Status

**Reproduced.** Official source `references_cases/Circular Patch Antenna_2.cst`
was replayed into `projects/circular_patch_td_repro.cst`, solved, and compared
against the official `1D Results\S-Parameters\S1,1` curve. Final report:
`results/circular_patch_td_repro/output/REPORT.md`.

## Source

- Official case: `references_cases/Circular Patch Antenna_2.cst`
- Source history: `references_cases/Circular Patch Antenna_2/Model/3D/ModelHistory.json`
- Extracted inventory: `results/circular_patch_td_repro/log/source_inventory.md`
- Generated artifacts: `results/circular_patch_td_repro/artifacts/`

The official project is CST 2024.0, MWS, mm/GHz, frequency range 1-4.5 GHz,
active solver `HF Time Domain`. It has no external parameter table.

## What This Case Teaches

This is a compact Component Library example for a **circular planar patch**:

- PEC circular disk: `Cylinder`, radius 17 mm, thickness 0.05 mm.
- PEC feed strip: `Brick`, X `-2..2`, Y `-56..0`, Z `0..0.05`.
- Substrate layer: epsilon 2.62, transparent blue, with the PEC objects inserted
  into the substrate by boolean insert.
- One waveguide port at `ymin`, free-coordinate range, with
  `.ClipPickedPortToBound("false")`.
- Frequency monitors at 2.92 GHz: H-field and farfield.
- TD hexahedral/PBA solver with adaptive mesh.

## Reproduction Pipeline

1. `extract_component_history.py` split the official `ModelHistory.json` into
   replayable `.bas` artifacts.
2. `lint_vba.py --fix results/circular_patch_td_repro/artifacts` found no
   blocking errors.
3. First replay used setup/materials/geometry/ports/monitors plus
   `999_generated_minimal_solver.bas`: all 18 blocks succeeded.
4. Geometry readback passed:
   - `Solid.GetNumberOfShapes() = 3`
   - `Solver.GetNumberOfPorts() = 1`
5. Minimal solver solve succeeded but did not match the official S11 tightly.
6. Official blocks 18-32 were then replayed: all 15 blocks succeeded.
7. Second solve with official solver/mesh/adaptive blocks succeeded and produced
   `Adaptive Meshing` result-tree entries.

## Results And Comparison

Tree item compared: `1D Results\S-Parameters\S1,1`

| Metric | Reproduction | Official |
|---|---:|---:|
| Points | 1001 | 1001 |
| S11 minimum frequency | 2.946000 GHz | 2.949500 GHz |
| S11 minimum | -11.567448 dB | -11.572863 dB |
| S11 near 2.92 GHz | -10.542968 dB | -10.518837 dB |
| Max absolute dB difference | 0.037438 dB | n/a |
| Mean absolute dB difference | 0.003218 dB | n/a |

Evidence:
- Minimal-solver comparison:
  `results/circular_patch_td_repro/log/s11_compare_reference.json`
- Official-mesh comparison:
  `results/circular_patch_td_repro/log/s11_compare_reference_after_official_mesh.json`
- Post-solve probe:
  `results/circular_patch_td_repro/log/probe_after_solve.json`

## Traps Found

1. **Minimal solver is not numerically equivalent.** It solved quickly but moved
   the S11 minimum from the official 2.9495 GHz to 2.9285 GHz and produced up to
   1.765 dB S11 difference. For official Component Library reproduction, use it
   only as a sanity build gate.
2. **Official TD solver/mesh blocks were safe here.** Unlike the previous FD
   patch case where full FD solver dumps carried version-sensitive setters, this
   CST 2024 TD circular patch accepted the official mesh/adaptive/special solver
   blocks cleanly and needed them for numerical alignment.
3. **Adaptive mesh is part of the answer.** The official source has Adaptive
   Meshing result items; the reproduced project only gained comparable results
   after replaying blocks 18-32.

## Promote To Shared References

- Add circular patch geometry pattern to `../building-blocks/vba-knowledge/geometry-primitives.md`.
- Add free-coordinate waveguide port pattern to `../building-blocks/vba-knowledge/ports-monitors-mesh.md`.
- Add solver note: Component Library TD cases may require full official
  adaptive mesh blocks for reference-level numerical reproduction.

## Links

Related: `repro-04-patch-fd.md`, `cst-hf-fundamentals.md`,
`mcp-pitfalls.md`, `official-component-repro-learning.md`.
