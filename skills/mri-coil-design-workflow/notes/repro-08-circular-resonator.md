# Repro 08: Circular Resonator

## Status

**Reproduced.** Official source `references_cases/Circular Resonator.cst` was
replayed, solved, and compared against the official `S1,1` and `S2,1` curves.
Final report: `results/circular_resonator_repro/output/REPORT.md`.

## Source

- Official case: `references_cases/Circular Resonator.cst`
- Source history: `references_cases/Circular Resonator/Model/3D/ModelHistory.json`
- Extracted inventory: `results/circular_resonator_repro/log/source_inventory.md`
- Generated artifacts: `results/circular_resonator_repro/artifacts/`
- Reproduction project: `projects/circular_resonator_repro_retry.cst`

The official project is CST 2024.0, MWS, mm/GHz, frequency range 0-10 GHz,
active solver `HF Time Domain`.

## What This Case Teaches

This is a compact two-port circular resonator example:

- CST-native parameters:
  - `k = 5.76`
  - `h = 0.635`
- Annular conductor:
  - `Cylinder`, outer radius 7 mm, inner radius 4 mm, Z `0..0.05`.
- A small feed/coupling brick is rotated and boolean-added into the resonator.
- Substrate brick is added under the conductor.
- Two orthogonal picked-face waveguide ports use expressions such as `k*h` and
  `h` in `.XrangeAdd`, `.YrangeAdd`, and `.ZrangeAdd`.

## Schematic Check

The official project has `Model/DS/schematic.xml`, but it is only the automatic
`MWSSCHEM1` view of the MWS model:

- `assemblyImport3DX.json` has `"blocks": []`.
- `schematic.xml` has one `MWSSCHEM` block with two pins/ports.
- No nets, external ports, lumped elements, matching components, or active
  schematic simulation tasks exist.
- `simulationproperties.json` has `schematic_tasks_run.active = false`.

Conclusion: no separate schematic reproduction is required. The schematic layer
is only useful as a port-exposure note.

## Reproduction Pipeline

1. `extract_component_history.py` split the official `ModelHistory.json` into
   artifacts.
2. The extractor now emits `artifacts/parameters/000_define_parameters.bas`
   from `Model/Parameters.json`.
3. `lint_vba.py --fix results/circular_resonator_repro/artifacts` found no
   blocking errors.
4. Replay was done in chunks to avoid losing the exact failure point:
   - 0-16: parameters, template, annular geometry, material/substrate.
   - 17-27: frequency, boundaries, solver and mesh setup.
   - 28-34: picked faces, two ports, special TD solver, final mesh/solver type.
5. All chunks succeeded after parameter pre-injection.
6. TD solve completed successfully.
7. `cst.results.ProjectFile` comparison against the official `.cst` produced
   exact curve agreement.

## Results And Comparison

Compared:
- `1D Results\S-Parameters\S1,1`
- `1D Results\S-Parameters\S2,1`

| Curve | Points | Same grid | Max dB diff | Mean dB diff | Max complex diff |
|---|---:|---|---:|---:|---:|
| S1,1 | 1001 | yes | 0.0 | 0.0 | 0.0 |
| S2,1 | 1001 | yes | 0.0 | 0.0 | 0.0 |

Evidence:
- `results/circular_resonator_repro/log/sparam_compare_reference.json`
- `results/circular_resonator_repro/log/readback_basic.txt`
- `results/circular_resonator_repro/log/result_items.json`

## Traps Found

1. **Parameters.json must be replayed first.** The official history references
   `k*h` before the project has a defined `k` when replayed from scratch. CST
   opens a modal "New Parameter" dialog for `K/k`; while that dialog is open,
   all MCP calls appear to hang.
2. **Case-sensitive prompt, case-insensitive parameter.** The modal displayed
   `K`, while the official parameter name is `k`. Pre-injecting `StoreParameter
   "k", "5.76"` avoids the prompt.
3. **Checkpoint chunks are useful.** The original full replay reached block 29
   and then blocked before port 2 because the modal was pending. Chunked replay
   plus progress files made the failure boundary obvious.

## Promote To Shared References

- `extract_component_history.py` now generates `000_define_parameters.bas`.
- `official-component-repro-learning.md` now requires replaying Parameters.json
  before official history.
- Add the modal-parameter trap to `mcp-pitfalls.md`.
- Add circular resonator and picked-face waveguide port examples to
  `../building-blocks/vba-knowledge/`.

## Links

Related: `repro-07-circular-patch-td.md`, `official-component-repro-learning.md`,
`mcp-pitfalls.md`, `ports-monitors-mesh.md`, `geometry-primitives.md`.
