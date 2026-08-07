# Schematic Matching — Tier B reference (Design Studio)

Tuning/matching the 3D coil in a Design Studio schematic. The **verified
ground truth** (topology, exact coords, wiring, tuning sequence, pitfalls) is
`../vba-blocks/dipole-schematic.md` — read that for any real build. This file is
the generalized Tier-B summary + the deterministic wiring snippet (also
templated at `templates/schematic_match.vba.j2`).

## What is deterministic vs a decision
- **Deterministic (Tier A / template)**: element placement + net wiring.
- **Decision loop (Tier C)**: the tuning values (Lt/Lp/Cp) — iterate against S11.

## Topology (L-match ground truth)
`ExtPort → [Lt series] → MWSSCHEM1`, with `Lp shunt → GND` at the input junction.
MWSSCHEM1 (the 3D block) is **auto-created** once the 3D model has a port — do NOT insert it.

## Placement — coordinate origin is 50000, not 0 (pitfall F10)
`.Position(x,y)` canvas origin = 50000. Pass `50000 + stored_coord`:
- `cst_add_external_port_tool(name="1", x=49400, y=50000)`
- `cst_add_inductor_tool("Lt", 78, "nH", x=49775, y=50000)`  ' series
- `cst_add_inductor_tool("Lp", 37, "nH", x=49625, y=50125)`  ' shunt
- `cst_add_ground_tool("GND1", x=49625, y=50250)`
Passing raw negatives (e.g. −600) flings the layout ~50000 units away.

## Wiring — one net per node via `Net.AddComponentPorts` (≤4 pins, pitfall #16)
`cst_connect_schematic_nodes_tool` cannot append to a used node → define each
node in ONE shot. Deterministic block: `templates/schematic_match.vba.j2`
(three nets: input / ground / dipole; Cp NOT wired). One statement per line — no colon `:`.

## Tuning (decision loop — Tier C)
Change a value with `Block.SetDoubleProperty` only (`.Modify/.Create/.UpdateModel` fail):
```vba
With Block
    .Reset : .Name "Lt"
    .SetLocalUnitForProperty "Inductance", "nH"
    .SetDoubleProperty "Inductance", "<Lt_nH>"
End With
```
Raise series L to pull resonance DOWN (`f ~ 1/sqrt(LC)`). Tuning is a
closed-loop decision, not a hard-coded list:

1. Run `SPara1`.
2. Read the full S11 curve.
3. Find `f_min` and `S11(f0)`.
4. If `f_min > f0`, increase series `Lt`; if `f_min < f0`, decrease `Lt`.
5. Use `Lt_next = Lt_current * (f_min / f0)^2` as a first estimate, then refine.
6. Stop only when the requested threshold at `f0` is met and the minimum is on
   the target sample/tolerance.

Dipole replay note: `78 -> 82.5 -> 86 nH` is only a seed. The 2026-07-21
reference comparison showed `86 nH` still resonates high (`f_min = 0.211 GHz`);
continue toward the backup reference value `Lt = 88 nH`.

## AC task + Combine Results (pure API, no popup)
`cst_configure_ac_combine_tool(task_name="AC1", ..., monitor_filters=[":hfield:"])`
then `cst_run_circuit_cosimulation_tool("AC1")` → produces `h-field (f=0.21) [AC1]`.
Never filter `["*"]` (pitfall F3). Full detail: `../vba-blocks/dipole-schematic.md`.
