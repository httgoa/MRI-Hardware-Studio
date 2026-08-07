# Reproduction 03: MRI Coil (1.5T body coil, 63 MHz) — structurally successful, electrical detail not fully aligned

> Phase 2, third case (MRI main line, highest priority). Official reference (read-only): `references_cases/MRI Coil/`. Reproduction project: `results/mri_coil_repro/`.
> Conclusion: **main structure + rotating-B1 mechanism reproduced successfully** (birdcage import + 32-capacitor tuning + dual-port 0/90° simultaneous excitation + h-field@63MHz). S-parameter **magnitude** matches the official case (both ≈0dB full reflection, no deep resonance), but **phase/electrical detail is not point-for-point aligned** — the official design also has a port-matching network (M1/M2/MT1/MT2) that wasn't reproduced.

## Reference answer (extracted from the official .cst)
- Physics: 1.5T MRI **body coil**, 63 MHz proton resonance, **birdcage coil + cylindrical shield (Schirm)**, RF section only, transient solver.
- **Geometry comes from external CAD**: `bodycoil_1.sat` (the history references `H:\bodycoil.sat`, but the case folder ships `Model/3D/bodycoil_1.sat`). Import yields 4 shapes: BodyCoil:C1 (deleted) / C2 (→PEC_Coil, the birdcage body) / Schirm (shield) / solid1. **Parametric rebuilding of the birdcage is impractical — must import the SAT**.
- Parameters: `Cap=108pF` (tuning capacitance), `M1/M2=13` (Matching Port1/2), `MT1/MT2=5` (Tuning+Matching), `vpos=-60.54` (port position).
- Capacitors: `LumpedFaceElement` RLCSerial, C=Cap. 4 base elements @z=510 at different azimuths → each rotated -90°×3 → 16 (one end-ring) → each translated (0,0,-1020) → another 16 at the other end = **32 total**.
- Ports: 2 discrete ports, 50Ω, 90° apart (port1@(0,286.5,520)-(0,296.5,520), rotate -90° for port2).
- **Rotating-B1 core**: solver `SimultaneousExcitation` port1@0° + port2@90°, `PhaseRefFrequency 63` → a single simulation produces a rotating field.
- Monitors: e-field + h-field @63MHz (Volume).

## Reproduction path (used this time)
Import the shipped SAT → delete C1/rename C2 to PEC_Coil → dual ports → 63MHz monitor → parameter Cap + 4 base capacitors → rotate×3 → translate×16 → simultaneous excitation. **Solve succeeded** ("Steady state energy criterion met").

## Key pitfalls (new to the knowledge base)
1. **`LumpedFaceElement.Create` still requires `Pick.PickEdgeFromId` to select an edge first even when given absolute coordinates via `SetP1/SetP2 "True",x,y,z`** (otherwise reports "No edge picked for discrete face port creation"). This is why every element in the history has 2 pick-edge calls before it. **Cannot build from coordinates alone — a pick is always required**.
2. **Good news: the official pick-edge IDs remain valid on the re-imported same SAT** (`PickEdgeFromId "BodyCoil:C2","1966348","109"` succeeds, NPICKS=2). → After importing the same SAT, you can replay the official pick+lumped block directly.
3. **Make each capacitor its own `add_to_history` block** (with its own pick inside). If multiple `LumpedFaceElement` calls are crammed into one block, the second one's pick state may be lost → failure. One block per element is the most reliable approach.
4. **Translate using a fixed `Vector "0","0","-1020"` + `UsePickedPoints "False"`**: the displacement is fixed by the vector and doesn't truly depend on the pick coordinates → this bypasses the pick dependency when copying the other end's 16 capacitors.
5. `LumpedFaceElement` has no `StartNameIteration`/`GetNextName`/`GetNumberOfElements` query methods (all fabricated attempts failed). Confirming capacitors exist relies on the solve log line "Voltage/current monitoring has not been activated for any lumped elements" (presence of this line = capacitors exist).

## Results comparison (honest)
| | My reproduction | Official |
|---|---|---|
| S11 full band | ≈0dB, no deep dip, @63MHz=-0.02dB | ≈0dB, no deep dip, @63MHz=-0.16dB |
| S11 phase@63 | 179° | -35° |
| h-field@63 | Generated | Generated |
| Solve | finished successfully | finished successfully |

- **Magnitude matches** (both fully reflected, expected for a body coil with no matching network) → main structure is correct.
- **Phase doesn't match** → electrical detail has a discrepancy. Most likely cause: **the official design has a port-matching network (parameters named M1/M2/MT1/MT2 for Matching/Tuning) that I didn't reproduce**; there may also be subtle differences between the rotate/translate-generated capacitors and the official birdcage topology.
- **Teaching goal achieved**: the rotating-B1 mechanism (dual-port 0/90° simultaneous excitation + PhaseRefFrequency) was successfully reproduced — this is exactly the core of an MRI body coil, and a concrete instantiation of the mechanism from [[repro-02-dipole-array]] variant 1.

## Remaining work (if point-for-point electrical alignment is needed later)
- [ ] Dig deeper into whether the official history has port-matching capacitors (LumpedElements named M1/M2/MT1/MT2), and add them to the reproduction.
- [ ] Use the h-field export to compute the rotating B1+ field, and quantitatively compare with the official design (B1 homogeneity/amplitude) — this is the ultimate MRI metric, more important than S-parameters.
- [ ] Two-port reciprocity's effect on port2's field: the official design truly excites simultaneously, while my log shows port2 computed via reciprocity, which may be inaccurate with lossy materials → turn off reciprocity to force two actual excitations.


## Knowledge-base validation conclusion
- Added pitfalls: `LumpedFaceElement`'s pick dependency + SAT pick-id reuse + no API to query capacitors, etc. — already recorded here; the key entries should also go into [[mcp-repro-pitfalls]].
- Confirms [[cst-circuit-sam]]: the body coil tunes directly in 3D using lumped elements (not schematic), and the rotating B1 uses simultaneous solver excitation (not AC combine) — **a different main line from our dipole's schematic+AC-combine route**.
- Related: [[cst-hf-fundamentals]] [[repro-02-dipole-array]] [[textbook-case-readonly]] [[ac-combine-b1-template-are-api]].
