# MRI RF Coil Physics — Reference Knowledge

Domain facts for interpreting and setting up MRI RF coil simulations. Not framework-specific.

## Larmor Frequency

`f [MHz] = γ · B0 [T]`, with γ (¹H proton) = **42.577 MHz/T**.

| B0 | ¹H Larmor freq |
| --- | --- |
| 1.5 T | 63.87 MHz |
| 3 T | 127.73 MHz |
| 5 T | 212.9 MHz |
| 7 T | 298.04 MHz |
| 9.4 T | 400.2 MHz |

Other nuclei (MHz/T): ¹³C 10.708, ²³Na 11.262, ³¹P 17.235, ¹⁹F 40.078.

The RF coil must resonate at (and be matched at) the Larmor frequency of the target nucleus/field.

## B1+ Field (transmit field)

- B1+ is the **circularly-polarized transmit component** of the RF magnetic field, NOT the raw |H|.
- Definition (with x,y transverse to B0 along z): `B1+ = (Bx + i·By) / 2` (complex); `B1- = (Bx − i·By)/2` is the receive-relevant counter-rotating part.
- **Never report |H| or |B| as B1+.** CST has a dedicated "B1+ and B1-" post-processing that computes it correctly.
- Typical working unit: **µT** (or µT per √W input). CST field exports are in Tesla → multiply by 1e6 for µT.
- **Homogeneity** metric: coefficient of variation over an ROI, `CV = std/mean × 100%`. Lower is better. Volume coils (birdcage) achieve low CV; single dipole/surface elements are inherently inhomogeneous (high CV, strong near surface, decays with depth).

## SAR (Specific Absorption Rate)

- Power deposited per unit tissue mass, W/kg. Safety-limited (IEC 60601-2-33).
- Reported as **mass-averaged**: 10 g or 1 g average — always state which.
- Requires a power-loss-density field monitor and a lossy tissue (phantom) model.
- Higher B0 (higher freq) → generally higher SAR for the same B1+ → SAR often the limiting constraint at 5T/7T.

## S-parameters / Matching / Resonance

- **Resonance** = frequency of minimum S11 (or an eigenmode result). Report with units; read from data, don't eyeball.
- Good match: **S11 ≤ −15 dB** at the target frequency (≤ −10 dB acceptable).
- S-parameters are complex → dB = `20·log10(|S|)`. Never label raw magnitude as dB.
- VSWR from reflection magnitude: `VSWR = (1+|Γ|)/(1−|Γ|)`.

## Solver Choice for MRI coils

- **HF Frequency Domain** (tetrahedral): narrow-band, high-Q resonant coils — the usual MRI choice. Loaded coil + phantom.
- **Eigenmode**: finding resonant mode frequencies (e.g. birdcage mode spectrum) before tuning.
- **Time Domain** (hexahedral): broadband; less common for narrowband MRI coils but usable.

## Tuning & Matching (circuit)

- Coils are tuned/matched with **lumped capacitors/inductors** (params like Cp/Ct/Lp/Lt).
- CST workflow often splits into: 3D EM solve (field basis) → **circuit co-simulation (AC task)** that applies the tuned lumped network → post-processing on the co-simulated field.
- Tuning direction: resonance `f ∝ 1/√(LC)` → to lower resonance increase C; to raise it decrease C.

## Common coil types

| Type | Use | B1+ character |
| --- | --- | --- |
| Birdcage | volume (head/body) tx/rx | homogeneous interior, low CV |
| Surface coil | local rx | high local SNR, very inhomogeneous |
| Dipole | UHF (7T+) tx, arrays | strong surface, depth-decaying |
| Phased array | parallel imaging rx | per-element local sensitivity |

## Units convention (defaults)

Geometry `mm`, frequency `MHz`, time `ns`. State explicitly in reports.
