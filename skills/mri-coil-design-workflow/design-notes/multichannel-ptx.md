# Design Note (placeholder): Multichannel / pTx Methods

> Open-ended survey notes, not executable steps. Land into `recipes/multichannel/` once mature.

## To survey
- **Combined B₁⁺**: implementing multi-channel complex-weighted superposition B₁⁺ = Σ wᵢ·B₁⁺ᵢ in CST (complex weights in the Combine of per-channel [AC*] fields).
- **B₁⁺ shimming**: static shimming (fixed per-channel amplitude/phase) vs dynamic; optimization objective (minimize B₁⁺ uniformity CV within the ROI / maximize efficiency).
- **Worst-case SAR**: an upper bound on 10g SAR from multi-channel superposition — Q-matrix, Virtual Observation Points (VOP) compression. How CST's field export supports this (per-channel E-field → construct the Q-matrix).
- **High-field pTx**: parallel transmit at 7T and above, combined with novel antenna elements (`novel-structures`).

## Interface with existing assets
- Multi-port Combine: `pitfalls/schematic-cosim.md` (handling the `"*"` filter trap under multiple channels).
- Single-channel field baseline: `recipes/b1-sar/`.
- SAR field export: `recipes/b1-sar/sar-field-export.md` (per-channel E-field).

(TODO: concrete implementation path for the VOP/Q-matrix method, references.)
