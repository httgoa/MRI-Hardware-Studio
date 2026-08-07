> Warning: **ROADMAP placeholder — unverified, no executable template, do not use this to drive CST.** When implementing, land it per `recipes/_TEMPLATE.md` and delete this notice.

# Recipe (placeholder): Multichannel / Phased-Array Simulation

**Scope**: modeling multi-element transmit arrays (pTx) and receive arrays, multi-port excitation, B₁⁺ shimming, SAR (including worst-case SAR from inter-channel interference).

**Expected future recipes** (naming convention):
- `array-build.md` — parametric N-element array geometry generation
- `ptx-b1-shimming.md` — pTx B₁⁺ shimming (amplitude/phase weighting to get the combined B₁⁺)
- `array-sar-worstcase.md` — worst-case 10g SAR from multi-channel superposition (Q-matrix / VOP)
- `sense-grappa-support.md` — sensitivity-map export for parallel imaging

**To-verify checklist**:
- [ ] Multi-port field combination: setting up complex weighting (amplitude+phase) in CST Combine Results
- [ ] Correct complex superposition for combined B₁⁺ = Σ wᵢ·B₁⁺ᵢ (per-channel [AC*] fields)
- [ ] How to implement the Q-matrix/VOP method for worst-case SAR given CST's field export
- [ ] Coupling with decoupling (`recipes/decoupling/`): an array inherently involves inter-channel coupling

**Depends on**: `recipes/build/`, `recipes/b1-sar/`, `recipes/decoupling/`, `design-notes/multichannel-ptx.md`.
