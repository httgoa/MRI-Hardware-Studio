# Pitfalls — Schematic / EM-Circuit Co-Simulation (Design Studio)

Traps in matching networks + AC Combine. Rule version: `foundations/cst-red-lines.md#Schematic`; topology decisions: `recipes/build/smith-matching.md`; VBA: `building-blocks/vba-blocks/dipole-schematic.md`.

### Both pins of a series element on the same net = short circuit = matching silently has no effect
- **Symptom**: adding a series L/C but the matching doesn't change at all.
- **Root cause**: both pins of the series element land on the same net = short circuit.
- **Workaround**: a series element **must span two different nets** (pin0 → incoming net, pin1 → a new net toward the load). Shunt elements connect between a rail node and GND.
- **Rule anchor**: → red-lines "Series element must span two different nets".

### `Externalport` casing is exact and strict
- **Symptom**: the connection silently fails.
- **Root cause**: `Externalport`'s casing is exact (capital E, everything else lowercase including the `p`).
- **Workaround**: **never** `.upper()/.lower()` it.

### A contaminated Externalport refuses new connections
- **Symptom**: a port that has been hit repeatedly by `Net.Delete` cannot be wired to a new connection.
- **Workaround**: delete and rebuild it, don't reuse it. Wire connections with the schematic VBA `Net.AddComponentPorts`, defining each electrical node in one shot (`cst_connect_schematic_nodes_tool` cannot append a port to an already-used node). Don't use colon `:` multi-statement lines in VBA (the MCP interpreter rejects them) — one statement per line.

### AC Combine filter `"*"` → an unclosable popup
- **Symptom**: even with combine correctly enabled, a popup still appears: "Results for some defined monitors could not be found — Abort/Retry/Ignore" (the MCP cannot dismiss it).
- **Root cause**: `"*"` matches `surface-current`/power-flow monitors that have no combinable volume field. This is a **filter problem**, not "combine wasn't enabled".
- **Workaround**: **never use `"*"`**. Only combine what's needed: B₁⁺ → the `h-field` monitor (default `[":hfield:"]`); SAR → add the `loss` monitor. Order matters: `SetComplexPortExcitation` must come before `SetPortSourceType("1","Signal")`; `docombineresults`/`blocknameforcombineresults` must be set before `.Update` (a new AC task defaults to `PortSourceType="None"`, which produces no field).
- **Rule anchor**: → red-lines "AC Combine Results filter: never use \"*\"".

### Use `Update()`, not `RunAndWait()`
- **Symptom**: `RunAndWait()` crashes with a `UnicodeDecodeError` when the solver stdout contains non-ASCII characters.
- **Workaround**: use `SimulationTask.Update()` for circuit/AC tasks instead (the previous solve is cached at run_id=0; `Update` re-solves).

### `blocknameforcombineresults` must be a real block name
- **Symptom**: combine produces nothing.
- **Workaround**: fill in the real MWS block name (e.g. `MWSSCHEM1`); empty or wrong names both fail.

### Changing L/C values must use `SetDoubleProperty`
- **Symptom**: `.Modify`/`.Create`/`.UpdateModel` all error out on an existing block.
- **Workaround**: change values with `Block.SetDoubleProperty`.

### `.Position` canvas origin is 50000
- **Symptom**: passing the target coordinate directly (e.g. −600) throws the element far off-canvas (electrical connections are unaffected, only the layout is scattered).
- **Workaround**: pass `50000 + target_stored_coordinate` (e.g. ExtPort stored at −600 → pass 49400).
