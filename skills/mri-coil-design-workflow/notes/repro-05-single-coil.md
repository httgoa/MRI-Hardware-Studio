# Reproduction 05: MRI Single Coil Element (supp case, 3T H1 @ 128 MHz) — Partial

> Phase 2, fifth case (situational; MRI surface coil **atomic unit**). Official reference (read-only): `references_supp_cases/MRI Single Coil Element.cst`. Reproduction project: `results/single_coil_repro/`.
>
> **Status: 3D modeling + solve + B1+ single-ended field post-processing all passed; schematic differential wiring not solved, work stopped here.** Full report in `results/single_coil_repro/output/REPORT.md`.

## Positioning
An MRI **surface-coil atomic unit** — a 170×150 mm rectangular loop coil, 4 gaps each 10×3 mm, 1 driven gap + 3 shorted-with-tuning-cap gaps + a muscle phantom. Lays the foundation for a Spine Array (8 elements).

**No tutorial htm** (not part of the Component Library's 5-variant tutorials): an official supp case, all reference answers reverse-engineered from the `.cst`'s internal `Model.mod` + `Parameters.json` + `schematic.xml`.

## Reference answer
See the prior version below — unchanged, extracted from the probe copy `results/_probe_supp/Single_probe/`. Key points:
- **9 parameters**: X=170, Y=150 mm, h=0.035 mm, t=10 mm, ct=12.814 pF, cm=159.2 pF, I=6.435 nH
- **Template**: `Bio-Medical Device - MRI.cfg`, mm/MHz, 0..300 MHz, monitor@128 MHz
- **Geometry**: Brick outer-frame minus inner-frame subtract → 4 gap subtracts (modeled as PEC, later switched to Copper (pure) lossy metal)
- **Ports**: **4 DiscreteFacePorts** (key! using DiscretePort instead makes the MWSSCHEM become 4-pin single-ended)
- **Muscle phantom**: Bio Tissue/Muscle, 16-frequency-point dispersive fit
- **Solver**: HF Time Domain Hexahedral, `StimulationPort All`, SteadyStateLimit −40 dB
- **Schematic**: 8-pin differential MWSSCHEM + 4 tuning caps (3 tune + 1 match) + 1 shunt match cap + 1 series inductor + 1 ExtPort + 1 GND

## Empirically verified results (passed)
| Stage | Status | Value |
|---|---|---|
| 3D geometry | Passed | 8 named history blocks, 90% shorter than the official 899 lines |
| Muscle dispersion fit | Passed | 16 frequency points sent in one call; Muscle pole @ 8860 MHz > sim 300 MHz gives a warning but doesn't affect the solve |
| 4 face ports + pick edge (3-arg) | Passed | edge id stable across a fresh build |
| 3D TD solve | Passed | 4-port sequential excitation, "Steady state energy criterion met" each time |
| 4x4 S-matrix | Passed | symmetric: S11=S22=S33=S44=−1.79 dB @128 MHz, adjacent-gap coupling −11.26 dB, opposite-side −9.88 dB |
| Differential MWSSCHEM | Passed | auto 8 pins (`Block.GetNumberOfPins=8, GetDifferentialPorts=True`), pin[0..3]="1..4", pin[4..7]="1'..4'" (matches official) |
| 3D h-field @128 generated | Passed | 4 of them: h-field (f=128) [1]..[4] |
| B1+ single-ended field post-processing | Passed | Port 1 default-signal excitation, peak inside the water phantom after 1W normalization **1.54 uT/sqrt(W)**, CV 0.93 |

## Schematic blocked (not passed)
**Target topology** (8-pin differential, matching official):
- **NodeA (driven+)**: MWSSCHEM.pin0 ("1") + CAP_M1.pin1 + IND1.pin0 + CAP_M.pin0
- **NodeB (driven-)**: MWSSCHEM.pin4 ("1'") + CAP_M1.pin0 + ExtPort.pin1
- **NodeC (RF signal)**: IND1.pin1 + ExtPort.pin0
- **NodeGND**: CAP_M.pin1 + GND
- **P2/P3/P4 shunt caps**: MWSSCHEM.pin1/2/3 <-> CAP_T2/3/4.pin0, MWSSCHEM.pin5/6/7 <-> CAP_T2/3/4.pin1 (cross-gap differential wiring)

**Problem**: every `Net.AddComponentPorts + Apply` call reports **"(&H8000ffff) Unable to create electrical net"** (regardless of 2-pin/3-pin/4-pin, regardless of whether zombie nets were cleared). The `cst_connect_schematic_nodes_tool` MCP tool hits the same error underneath.

**Hypotheses ruled out**:
1. Ruled out: wrong pin index — verified consistent via `GetPinName`
2. Ruled out: exceeding the 4-pin limit — 2 pins also fail
3. Ruled out: `SetDifferentialPorts` not taking effect — already auto True
4. Ruled out: 3D not re-solved — still fails after re-solving
5. Ruled out: zombie-net interference — still fails after clearing down to NNETS=0

**Not yet explored** (possible root cause):
1. Differential MWSSCHEM may need `Block.SetReferenceBlock` or a different API
2. May need `Net.MergeSubNets` / a differential-specific command
3. `SchematicLayout` may need an Apply canvas
4. Manually wire it once in the CST GUI, then extract the correct VBA sequence from the `.mod`

## Key pitfalls (all written back to `mcp-repro-pitfalls.md` #15-17)
1. **The 3D port type automatically determines the schematic MWSSCHEM pin count** (new discovery):
   - `DiscreteFacePort` -> **8-pin differential MWSSCHEM**
   - `DiscretePort` -> **4-pin single-ended MWSSCHEM**
   - `Block.UpdateModel` cannot force a switch; it's entirely determined by the 3D side
2. **`Net.AddComponentPorts` supports at most 4 pins per call** (verified OK in a single-ended environment; in a differential environment **any pin count** fails, needs a different API)
3. **A failed `.Apply` leaves a zombie net behind**: must clean up with `Net.Delete`, procedure: `GetNumberOfNets` -> collect `GetNetNameByIndex(i)` into a list -> loop `Net.Delete`
4. **Mixing `DiscretePort` pitfall**: this run first built face ports -> switched to discrete port -> switched back to face port, which broke the differential-expansion path; recommend **using one port type throughout, start to finish**

## Results comparison (honest)
| | My reproduction | Official | Conclusion |
|---|---|---|---|
| 3D geometry & material | complete | matches parametrically | matched |
| 4x4 S-matrix structure | has values | not retained in the official .cst (not solved for this case) | no alignment anchor |
| 4-port symmetry | S11=S22=S33=S44 | unknown | matched (loop geometry correct) |
| B1+ (matched drive) | **not achieved** | unknown | Warning: topology incomplete |
| B1+ (port 1 single-ended, unmatched) | 1.54 uT/sqrt(W) @1W | N/A | teaching example only |

## Value for the MRI main line
- **First identification** of the rule that 3D port type auto-determines the schematic differential/single-ended decision (applies generally to all supp cases)
- **First successful run** of DiscreteFacePort + the 3-arg PickEdge form + a 16-point dispersive-material fit
- **The differential schematic-wiring API** needs dedicated study — **must be resolved before reproducing Body Coil / Spine Coil**
- The 3D pipeline is fully reusable for Body Coil (32 caps) / Spine Coil (48 caps + 8 ports) — only the schematic layer needs a differential-API breakthrough

## Knowledge-base validation conclusion
- **HF-notes validation**: the MRI surface coil's 4-gap tuning topology + differential-drive requirement should be added to `cst-hf-fundamentals.md` §"MRI surface coils"
- **Help-index addition**: `Block.SetDifferentialPorts` / `Block.SetReferenceBlock` / `Net.MergeSubNets` / `SchematicLayout` and other differential schematic APIs need to be looked up and added to `cst-help-index.md`
- **New recipe**: unlike dipole-schematic's single-ended L-match, the MRI loop coil's **8-pin differential schematic** needs its own recipe (currently empty)
- **Future cases**: Body Coil 3T (32 tune caps) and Spine 3T (48 caps + 8 ExtPort) will both hit the same differential-MWSSCHEM wiring problem → **recommend focusing on this API blocker first before tackling Body / Spine**


Related: [[repro-01-dipole-antenna]] [[repro-03-mri-coil]] [[repro-04-patch-fd]] [[cst-hf-fundamentals]] [[dipole-b1-pipeline]] [[from-scratch-run-findings]] [[textbook-case-readonly]] [[mcp-repro-pitfalls]] [[ac-combine-b1-template-are-api]].
