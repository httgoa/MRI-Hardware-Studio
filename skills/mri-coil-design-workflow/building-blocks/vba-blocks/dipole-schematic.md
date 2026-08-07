# Circuit / Schematic — Dipole Tuning & Matching (ground truth)

The verified matching network from the dipole project (Design Studio schematic).
This is the topology to reproduce for tuning the 3D dipole at the Larmor
frequency. For the from-scratch reference replay, use the stricter
reference-grade target (`S11(f0) <= -30 dB` and the sampled minimum at `f0`);
`S11 < -20 dB` is only an explicitly relaxed engineering target.

## Verified topology (GROUND TRUTH from Dipole(3) `Model/DS/schematic.xml`, 2026-07-13)

The real textbook schematic is a simple **L-match: series Lt + shunt Lp to GND**. All three
elements sit on a single horizontal rail at Y=0; only Lp drops vertically to ground.

```
ExtPort1 ───── Junction ───── Lt (series) ───── MWSSCHEM1 (3D dipole, port 1)
                  │
                 Lp (shunt, vertical)
                  │
                 GND
```

- **MWSSCHEM1** — the 3D EM model block (auto-created once the 3D model has a port).
- **ExtPort1** — external excitation port (AC source / S-param drive enters here).
- **Lt (IND1)** — series inductor between the junction and MWSSCHEM1.
- **Lp (IND2)** — shunt inductor from the junction down to GND.
- **Junction** — the input node joining ExtPort, Lt, and Lp.
- **GND**.

Initial placement values: **`Lt = 78 nH`, `Lp = 37 nH`**. Treat `78 nH` as a
starting point, not as the final tuned value. The dipole replay must run a
closed-loop S11 tuning pass after the schematic is wired. The 2026-07-21
reference comparison showed the saved backup project uses **`Lt = 88 nH`,
`Lp = 37 nH`**, with the S11 minimum on the 0.21 GHz sample.

> Warning: **`Cp` (CAP1 = 1 pF) is PLACED but NOT wired** in the real schematic — no Link references it
> (verified: `Ref="32"` appears in zero connections). It is a spare. Do NOT wire Cp in; the earlier
> from-scratch recipe over-complicated the network by connecting Cp. `Ct=2 pF` is only a parameter,
> no component. So the active network is exactly: **ExtPort → [Lt series] → MWSSCHEM1**, with **Lp
> shunt to GND** at the input junction. Nothing else.

## Exact ground-truth geometry — coordinate origin is 50000, NOT 0 (verified 2026-07-14)

**CRITICAL, previously-wrong fact.** `.Position(x, y)` (what `cst_add_inductor_tool` etc. call)
uses a canvas **origin of 50000**, not 0. The numbers stored in `schematic.xml` (and shown in the
GUI) equal **`(x_input − 50000, y_input − 50000)`**. So the tool defaults `x=50000, y=50000` map to
stored (0,0) = canvas center.

The ground-truth table below lists **STORED** coords (what you want to SEE in `schematic.xml`,
matching the reference `Dipole(3)`). To achieve them you MUST pass **`50000 + stored`** to the tools:

| Block | Class | STORED (X,Y) | PASS to tool (x,y) | Label |
| --- | --- | --- | --- | --- |
| MWSSCHEM1 | MWSSCHEM | (25, 0) | auto-created — do NOT place | port "1" on Left |
| ExtPort1 | EXTPORT | (−600, 0) | **(49400, 50000)** | "1" |
| Lt (IND1) | IND | (−225, 0) | **(49775, 50000)** | series, horizontal |
| Lp (IND2) | IND | (−375, 125) | **(49625, 50125)** | shunt, vertical |
| GND1 | GND | (−375, 250) | **(49625, 50250)** | — |
| Junction | — | (−375, 0) | — | input node (no block) |

> Wrong: **the old recipe said "pass small hundreds like −600" — that is WRONG.** Passing −600 stores
> it at −50600, i.e. ~50000 units away from MWSSCHEM1 → the entire L-match network gets flung far
> off to the lower-left, exactly the "components drawn very far away" symptom. Electrical nets still
> work (they wire by component NAME, not position) and S11 is unaffected, but the layout is unusable.
> The `±40000` warning in the even-older recipe was a different confusion; the real rule is simply
> **origin = 50000, pass `50000 + desired_stored_coord`.**

### If blocks are already mis-placed: move in-place (no delete/rebuild needed)
`Block.Reset : .Name "<n>" : .Position <50000+X>, <50000+Y>` on an EXISTING block repositions it
(verified err=0, takes effect after `save()`). For the external port use the `ExternalPort` object
with the same `.Name/.Position`. Re-wiring is NOT needed — nets are name-based.

### Spacing rationale (stored-coord terms)
- MWSSCHEM1 at stored (25,0) = far right (largest block). Element spacing ≈150 stored units keeps
  labels readable. ExtPort stored (−600,0) → Lt (−225,0) → MWSSCHEM1 (25,0) is a balanced rail;
  shunt branch drops 125 to Lp then 125 to GND.

## MCP tools to build it — VERIFIED from-scratch 2026-07-11

The **MWSSCHEM1** 3D block is auto-created in the schematic once the 3D model has a port — do NOT insert it manually (check with schematic VBA `Block.StartBlockNameIteration`/`GetNextBlockName`).

Add the lumped elements + external port + ground. **Pass `50000 + stored_coord`** (origin=50000,
see the table above) — NOT the raw negative hundreds:
- `cst_add_external_port_tool(name="1", x=49400, y=50000)`   ' stored (−600, 0)
- `cst_add_inductor_tool("Lt", 78, "nH", x=49775, y=50000)`  ' stored (−225, 0), series
- `cst_add_inductor_tool("Lp", 37, "nH", x=49625, y=50125)`  ' stored (−375, 125), shunt
- `cst_add_ground_tool("GND1", x=49625, y=50250)`            ' stored (−375, 250)
- **Do NOT add/wire Cp** — the ground-truth L-match uses only Lt + Lp. (If a coil truly needs a
  shunt cap, that's a different network; for the dipole textbook case, omit it.)

### Wiring — build the two electrical nodes (Cp EXCLUDED)
`cst_connect_schematic_nodes_tool` creates a NEW net each call and CANNOT append a port to an already-used node — repeated calls sharing a port fail with "Unable to create electrical net". **Define each electrical node in ONE shot via schematic VBA `Net.AddComponentPorts`**. The ground-truth network has just two nets (endpoints: `Externalport`/`BLOCK`, port_index):
```vba
' Input (junction) node: ExtPort1 + Lt.0 + Lp.0   (NO Cp)
Dim P1(2,2) As Variant
P1(0,0)="Externalport"
P1(0,1)="1"
P1(0,2)=0
P1(1,0)="BLOCK"
P1(1,1)="Lt"
P1(1,2)=0
P1(2,0)="BLOCK"
P1(2,1)="Lp"
P1(2,2)=0
With Net
    .Reset
    .AddComponentPorts "", P1, False
    .Apply
End With
' Ground node: Lp.1 + GND1.0     (same pattern, 2 ports)
' Dipole node: Lt.1 + MWSSCHEM1.0 (same pattern, 2 ports)
```
> Note: don't use colon `:` multi-statement lines in VBA sent through the MCP — the interpreter
> rejects them ("Unexpected text"). One statement per line (as above).

## Tasks & Tuning — VERIFIED

**S-Parameter task**: `cst_configure_frequency_sweep_tool(task_name="SPara1", fmin=0.15, fmax=0.25, samples=101, unit="GHz")`. Run via `cst_run_circuit_cosimulation_tool("SPara1")`. Read S11 from `cst.results` schematic: `pf.get_schematic().get_result_item("Tasks\\SPara1\\S-Parameters\\S1,1")`, dB = `20*log10(abs(S11))`.

**Changing an L/C value (pitfall)**: `.Modify`, `.Create`, `.UpdateModel` all FAIL on an existing block. The working way is `Block.SetDoubleProperty` alone (no commit method):
```vba
With Block
    .Reset : .Name "Lt"
    .SetLocalUnitForProperty "Inductance", "nH"
    .SetDoubleProperty "Inductance", "86"
End With
```
Then re-run `SPara1` and re-read S11.

**Tuning (closed-loop, mandatory)**: starting Lt=78 gave S11=-11.8 dB @0.21
(resonance at 0.216 GHz, too high). Increasing series L pulls resonance down.
The sequence `78 -> 82.5 -> 86 nH` is only a seed sequence. Do **not** stop at
86 nH unless the objective below is met.

Reference-grade dipole objective:
- target sample: `f0 = 0.21 GHz`
- `S11(f0) <= -30 dB`
- the sampled minimum S11 is at `f0` (or within the frequency-step tolerance if a
  different sweep resolution is used)

Decision rule after every SPara run:
1. Read the full `Tasks\SPara1\S-Parameters\S1,1` curve, not only one point.
2. Compute dB as `20*log10(abs(S11))`.
3. Find `f_min`, the frequency of minimum S11.
4. If `f_min > f0`, the resonance is too high: increase `Lt`. A first estimate is
   `Lt_next = Lt_current * (f_min / f0)^2`, then bracket/refine around it.
5. If `f_min < f0`, decrease `Lt`.
6. If `S11(f0)` is still above the objective, refine `Lt` even when the minimum is
   close to `f0`.

Observed 2026-07-21 comparison: at `Lt = 86 nH`, `S11(0.21) = -25.49 dB` and
the minimum is at `0.211 GHz`; the reasoning above requires continuing upward.
The backup reference with `Lt = 88 nH` gives `S11(0.21) ~= -41.10 dB`. Log every
trial (`Lt`, `S11(f0)`, `f_min`, `S11_min`) under `results/<project>/log/`.

**AC task + Combine Results — ONE TOOL, NO POPUP (preferred, 2026-07-13)**:

Use the dedicated tool that sets excitation AND enables Combine Results up-front:
```
cst_configure_ac_combine_tool(task_name="AC1", fmin=0.15, fmax=0.25, unit="GHz",
                              port_name="1", block_name="MWSSCHEM1", amplitude=10)
                              # monitor_filters default = [":hfield:"] (B1+ needs only H)
```
Then run it:
```
cst_run_circuit_cosimulation_tool("AC1")
```
This produces `h-field (f=0.21) [AC1]` in the 3D tree with **zero GUI clicks**.

Why it works (all official DS `SimulationTask` VBA — see `simulationtaskobject.htm` in CST Online Help):
- **Excitation**: `SetComplexPortExcitation("1","10","0")` MUST be called before `SetPortSourceType("1","Signal")` (the API errors otherwise). 10 V into 50 Ω ≈ 1 W. A fresh AC task defaults to `PortSourceType="None"` → no field; this is the single reason early from-scratch runs produced nothing.
- **Combine enabled up-front**: `SetProperty "docombineresults","True"` + `SetProperty "blocknameforcombineresults","MWSSCHEM1"` = the GUI "Combine results" checkbox + "Block" dropdown. Set these BEFORE `.Update`.
- **Monitor filter — the real popup trigger (2026-07-13 Dipole(3) lesson)**: `ResetCombineMonitorFilters` then add ONLY the monitors you need. Tokens: exact name (`"h-field (f=0.21)"`), type (`":hfield:"`,`":efield:"`,`":farfield:"`,`":fieldsource:"`), or `"*"`=all. **NEVER default to `"*"`**: projects usually have a `surface-current` monitor that produces no combinable volume field (only `.sld`), so `"*"` hits it and fires the Abort/Retry/Ignore dialog — even with combine correctly enabled. That popup is a FILTER problem, not a "combine not enabled" problem (that earlier diagnosis was wrong). B1+ → default `[":hfield:"]`; SAR too → `["h-field (f=0.21)","loss (f=0.21)"]`.

> Sequence still matters: running AC combine clears the 3D H/E-field monitors, so do 3D solve → (tune on SPara) → `cst_configure_ac_combine_tool` → `cst_run_circuit_cosimulation_tool("AC1")`. Re-run the 3D solve if `[1]` was cleared by an earlier attempt.

Once `h-field (f=0.21) [AC1]` exists in the 3D tree, proceed to B1+ post-processing (`b1-field-pipeline.md`).
