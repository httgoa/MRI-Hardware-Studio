# Solvers — Tier B few-shot reference (CST VBA)

Choose and configure the solver. Raw history commands (no `Sub Main`), via
`add_to_history`. **Keep setter blocks MINIMAL** — only the ~5–10 setters the
case needs; copying a full official `.mod` solver block drags in newer-version
APIs that pop "No such property or method" and block the history (pitfall #11).

## Solver choice (physics-driven)

| Need | Solver | Mesh |
|---|---|---|
| B1+ / S-params / narrowband field on a lossy load | HF **Frequency Domain** | tetrahedral |
| native IEEE **10g SAR** | HF **Time Domain** | **hexahedral** (pitfall #18) |
| resonant modes / birdcage tuning (unloaded) | **Eigenmode** | tetrahedral |

Do NOT hardcode "always TD-hex" — TD-hex is a *conditional* requirement for
native SAR only.

## HF Frequency Domain (tetrahedral) — the B1+ workhorse
```vba
ChangeSolverType "HF Frequency Domain"
Solver.FrequencyRange "0.15", "0.25"        ' narrow band around Larmor (high-Q coil)
With FDSolver
    .Reset
    .SetMethod "Tetrahedral", "General purpose"
    .OrderTet "Second"
    .Stimulation "All", "1"
    .AccuracyTet "1e-4"
    .MeshAdaptionTet "True"
    .CalcPowerLoss "True"
    .SetKeepSolutionCoefficients "MonitorsAndMeshAdaptation"
End With
```
> `SetKeepSolutionCoefficients "MonitorsAndMeshAdaptation"` is REQUIRED so the
> later circuit co-simulation can back-substitute the tuned excitation and
> produce the `[AC*]` field that B1+ needs.

## HF Time Domain (hexahedral) — required for native 10g SAR
```vba
ChangeSolverType "HF Time Domain"
Solver.FrequencyRange "0.15", "0.25"
With Solver
    .Method "Hexahedral"
    .SteadyStateLimit "-30"                 ' -30 dB: high-Q loads settle far faster than -40 (pitfall #25)
    .CalculateModesOnly "False"
    .StimulationPort "All"
    .StimulationMode "All"
End With
```
> High-Q + severe mismatch rings for a long time; `-30` keeps DFT field accuracy
> (B1+/SAR residual ~0.1%) while roughly halving runtime. Use the SAME steady-state
> limit across all cases you compare.

### Official Component Library TD replay

For fast sanity builds, a minimal TD solver block is enough to verify geometry,
ports, and monitors. For **numerical reproduction of an official Component
Library TD case**, replay the official mesh/adaptive/special solver blocks when
they execute cleanly on the same CST major version.

`notes/repro-07-circular-patch-td.md` showed the difference:
- minimal generated TD block solved but shifted S11 by up to about 1.77 dB;
- replaying official blocks 18-32 enabled Adaptive Meshing and reduced max S11
  curve difference against the official project to about 0.037 dB.

This is a TD-specific learning result. It does not cancel the FD warning in
`mcp-pitfalls.md`: full official FD solver dumps can still carry
version-sensitive setters, so execute them through the normal L1/L2/L3 ladder.

## Eigenmode (resonant mode frequencies — birdcage)
```vba
ChangeSolverType "HF Eigenmode"
With EigenmodeSolver
    .Reset
    .SetMeshType "Tetrahedral"
    .SetNumberOfModes "10"
    .SetModesInFrequencyRange "False"
    .SetFrequencyTarget "True", "0.21"
    .Start
End With
```

## Run (async — preferred for 3D; avoids MCP blocking timeout)
Run via `cst_run_python_tool`, not a VBA `.Start`, so it doesn't block:
```python
project.save()
model3d.start_solver()            # non-blocking
# then poll: model3d.is_solver_running() / model3d.get_solver_run_info()
```

## Rules
- Minimal setters — CST keeps unset fields at safe defaults; a fabricated/newer setter pops a blocking dialog.
- Save before solving (red line). Prefer async start + poll over blocking `cst_run_solver_tool` for 3D.
- After a TD first-solve, verify 3D volume-field monitors exist; if missing, re-solve once (pitfall #23).
