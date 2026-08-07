# Pitfalls — Numerical Correctness

Traps where a quantity is computed wrong or mislabeled with the wrong unit. Rule version: `foundations/cst-red-lines.md#Numerical Correctness`; physics definitions: `foundations/mri-physics.md`.

### S-parameter complex value → dB
- **Symptom**: labeling a raw magnitude as dB.
- **Workaround**: `20*log10(abs(S))`. VSWR uses the reflection-coefficient magnitude, **not dB**.

### B₁⁺ is the CP transmit component, not |H|
- **Symptom**: reporting `|H|`/`|B|` as B₁⁺.
- **Root cause**: B₁⁺ is the circularly-polarized transmit component `(Bx + i·By)/2`.
- **Workaround**: use CST's "B1+ and B1−" result, or compute it yourself. When computing manually, match `b0_plus_z`: B0 along +z ⇒ `(Hx − i·Hy)/2` (a sign error swaps B₁⁺/B₁⁻). Report in µT (CST field export is in Tesla → ×1e6); state the plane/ROI. See `scripts/compute_b1plus.py`.
- **Rule anchor**: → red-lines "B1+ is the CP transmit component".

### Antenna gain ≠ |E|
- **Symptom**: reporting `Abs(E)` (raw E-field magnitude) as gain.
- **Workaround**: use the `Realized Gain`/`Gain`/`Directivity` results — these are different quantities.

### SAR must state averaging mass + unit
- **Workaround**: state 10g vs 1g and the W/kg unit; requires a power-loss monitor + lossy tissue. SAR normalization detail: `sar.md`.

### Resonance = read from data, never eyeball it
- **Workaround**: resonance = the S11-minimum frequency or an eigenmode entry, read from data. Never claim convergence/pass/optimum without evidence. State the frequency unit explicitly.

### FoM normalization: normalize by accepted power, and measure it per case
- **Symptom**: assuming "1W excitation = 1W accepted", leading to conclusions that contradict the paper.
- **Root cause**: a bare-port dipole can be severely mismatched, with P_acc as low as 0.00025W (a 2000× spread).
- **Workaround**: both the numerator and denominator of FoM=B₁⁺/√SAR_max must be normalized to **1W accepted power** (B₁⁺∝1/√P_acc, SAR∝1/P_acc); measure P_acc per case (`1D Results\Power\Excitation [1]\Power Accepted per Port\Port 1` @freq, using `run_ids[-1]`). Normalizing a geometry/component sweep by accepted power makes FoM invariant to matching, so **no per-case matching is required** (antenna linearity: fixed P_acc ⇒ fixed current distribution ⇒ fixed B₁⁺/SAR distribution).
- **Origin**: FD_Optimize M2/M3. Memory `b1-sar-optimization-no-per-case-matching`.
