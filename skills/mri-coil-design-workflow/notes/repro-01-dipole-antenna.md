# Reproduction 01: Dipole Antenna (official Component Library)

> Phase 2, first case. Goal: use the official textbook to calibrate the general antenna approach + validate the knowledge base.
> Official reference (read-only): `references_cases/Dipole Antenna/`. Reproduction project: `results/dipole_repro/dipole_repro.cst`.
> Result: **fully successful** — resonance 27.0 GHz, S11=−67.5 dB, radiation efficiency 99.997%@27.18GHz. Matches official behavior.

## Reference answer (extracted from the official .cst)
- Physics: λ/2 electric dipole, λ=10mm, farfield calculation.
- Parameters: `lambda=10`, `l2=0.5*lambda=5`, `r=0.003369*lambda=0.03369`, `d=0.025*lambda=0.25` (mm).
- Geometry: PEC layer → thin cylinder (Driven Element, z-axis, ±l2/2, radius r) → brick (cut gap, Zrange ±d/2) → `Solid.Subtract`.
- Port: discrete port 1, **65Ω**, across the gap at two points (0,0,±d/2), Monitor True.
- Boundaries: all 6 faces `expanded open`; symmetry **Xsym=magnetic, Ysym=magnetic, Zsym=electric** (dipole along z → symmetry saves ~8x time).
- Monitors: farfield @27.18 GHz.
- Mesh: Hex/PBA, StepsPerWave 30, **PEC EdgeRefinement ratio 6** (thin PEC wires need mesh refinement or accuracy suffers).
- Solver: Transient (HF_TRANSIENT), TD-S, SteadyStateLimit −60dB.

## MCP reproduction pitfalls (new to the knowledge base, not covered by the manual)
1. **`lambda` is a reserved word**: the MCP bridge (Python side) forbids using `lambda` as a parameter name ("must not be a VBA or Python keyword"). The official history runs fine with `lambda`, but bridged through MCP it must be renamed (use `lambda0`) → rename every expression that depends on it too.
2. **`StoreParameterSettings "name","descr"` reports "Expecting an existing scalar var"**: the API signature for adding a parameter description is counter-intuitive; **skip the description** during reproduction (not required), just use `MakeSureParameterExists name, expr`. If a description is truly needed, check the help page for the parameter object.
3. **Discrete port uses coordinates instead of picked points**: the official history uses `Pick.PickCenterpointFromId` + `UsePickedPoints True`. Since the MCP has no interactivity, using `.Point1/.Point2` coordinates + `UsePickedPoints "False"` directly is more reliable, and gives the same result.
4. **PML reference-frequency INFO**: the default open boundary reference frequency is 30GHz (near fmax); > the monitor's 27.18GHz triggers an INFO notice. The official final history has `Boundary.FrequencyForMinimumDistance "27.18"` to fix this. Doesn't affect the main result, but a precise monitor should be set to the monitored frequency.

## Physics validation (anchor for judging reproduction correctness)
- Theoretical λ/2 dipole resonance: λ=10mm→f=c/λ=30GHz, but a real half-wave dipole resonates slightly lower (end effects) → **27GHz is reasonable**.
- The official case places the farfield at 27.18GHz = the resonance point; our independently reproduced resonance = 27.0GHz → mutually confirms the geometry/port/mesh are correct.
- PEC lossless → radiation efficiency ≈ 100% (got 99.997%). The 65Ω port is near-perfectly matched at resonance (−67dB).

## Knowledge-base validation conclusion
- The HF notes' judgment that "antenna = Transient + open boundary + farfield monitor" was confirmed correct.
- Gaps filled: (1) mesh refinement for thin PEC wires (StepsPerWave up + PEC EdgeRefinement up); (2) the 4 MCP pitfalls above.
- The help index's `_discreteports`/`_boundary_conditions_symmetryplanes`/`_monitor` entries all proved useful.
- Related: [[cst-hf-fundamentals]] [[from-scratch-run-findings]] [[textbook-case-readonly]].

## To-do (reuse for later cases)
- Avoiding reserved words in parameter naming → now a general rule, recorded in [[from-scratch-run-findings]]'s pitfall pool.
- Next: MRI Coil (highest priority, 1.5T body coil, 63MHz, rotating B1).
