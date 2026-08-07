# Repro 09: Circular Patch Antenna HF Multilayer

## Status

**Reproduced.** Official source `references_cases/Circular Patch Antenna.cst`
was replayed, solved, and compared against the official `S1,1` curve. Final
report: `results/circular_patch_multilayer_repro/output/REPORT.md`.

## Source

- Official case: `references_cases/Circular Patch Antenna.cst`
- Source history: `references_cases/Circular Patch Antenna/Model/3D/ModelHistory.json`
- Extracted inventory: `results/circular_patch_multilayer_repro/log/source_inventory.md`
- Generated artifacts: `results/circular_patch_multilayer_repro/artifacts/`
- Reproduction project: `projects/circular_patch_multilayer_repro.cst`

The official project is CST 2024.0, MWS, mm/GHz, frequency range 1-5 GHz,
active solver `HF Multilayer`.

## What This Case Teaches

This is the HF Multilayer circular patch variant:

- Same basic circular patch/feed/substrate family as `repro-07`.
- One waveguide port.
- Farfield monitor at 3 GHz.
- The official history converts the patch/feed solids into face-derived PEC
  sheet shapes:
  - pick face
  - make shape from faces
  - delete original PEC solid
- Solver path is HF Multilayer / surface mesh rather than TD hexahedral.

## Schematic Check

The official Design Studio schematic is only an automatic one-port `MWSSCHEM1`
block:

- `assemblyImport3DX.json` has `"blocks": []`.
- `schematic.xml` has one `MWSSCHEM` block with one exposed port.
- No nets, external ports, lumped elements, matching components, or active
  schematic tasks exist.

Conclusion: no separate schematic reproduction is required.

## Reproduction Pipeline

1. `extract_component_history.py` split the official `ModelHistory.json` into
   `.bas` artifacts.
2. L0 lint passed with warnings only for global `SetSolverType "HF_MULTILAYER"`.
3. Replay was done in two chunks:
   - 1-19: setup, geometry, material, port.
   - 20-38: HF Multilayer solver, surface mesh, face-derived sheet shapes,
     farfield monitor, final solver type.
4. Both chunks succeeded.
5. HF Multilayer solve completed successfully.
6. `cst.results.ProjectFile` comparison against the official `.cst` showed
   close reference-level agreement.

## Results And Comparison

Compared: `1D Results\S-Parameters\S1,1`

| Metric | Reproduction | Official |
|---|---:|---:|
| Points | 1001 | 1001 |
| Same grid | yes | yes |
| S11 minimum frequency | 2.988000 GHz | 2.992000 GHz |
| S11 minimum | -12.200091 dB | -12.194509 dB |
| S11 near 3 GHz | -12.005022 dB | -12.005855 dB |
| Max absolute dB difference | 0.017448 dB | n/a |
| Mean absolute dB difference | 0.001044 dB | n/a |

Evidence:
- `results/circular_patch_multilayer_repro/log/s11_compare_reference.json`
- `results/circular_patch_multilayer_repro/log/readback_basic.txt`
- `results/circular_patch_multilayer_repro/log/result_items.json`

## Traps Found

1. **HF Multilayer history was safe on CST 2024.** The official `FDSolver`,
   surface mesh, and `SetSolverType "HF_MULTILAYER"` blocks replayed cleanly on
   the same CST major version. Keep the L1 checkpoint discipline anyway, because
   FD/multilayer solver dumps are known to be version-sensitive in other cases.
2. **Face-derived sheet conversion matters.** The official case does not leave
   the circular patch/feed as thick PEC solids. It makes PEC sheet shapes from
   selected faces and deletes the originals before solving.
3. **No schematic reproduction.** The schematic is only automatic MWS port
   exposure, not a circuit workflow.

## Promote To Shared References

- Use `repro-07` for the TD circular patch path.
- Use this note when a circular patch task specifically wants the HF Multilayer
  / surface-mesh sheet workflow.
- Keep solver dumps behind chunked/checkpoint replay for future CST versions.

## Links

Related: `repro-07-circular-patch-td.md`,
`repro-08-circular-resonator.md`, `official-component-repro-learning.md`,
`mcp-pitfalls.md`.
