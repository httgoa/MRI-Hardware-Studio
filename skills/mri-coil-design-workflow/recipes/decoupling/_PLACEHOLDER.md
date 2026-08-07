> Warning: **ROADMAP placeholder — unverified, no executable template, do not use this to drive CST.** When implementing, land it per `recipes/_TEMPLATE.md` and delete this notice.

# Recipe (placeholder): Multichannel Decoupling

**Scope**: inter-channel decoupling simulation and optimization for multichannel MRI array coils (transmit arrays/receive arrays).

**Expected future recipes** (naming convention):
- `preamp-decoupling.md` — preamplifier decoupling (low input impedance)
- `geometric-overlap.md` — geometric-overlap decoupling (critical overlap between neighboring elements to null mutual inductance)
- `inductive-decoupling.md` — inductive/capacitive decoupling networks
- `decoupling-matrix.md` — N×N S-parameter decoupling-matrix evaluation (diagonal dominance, inter-channel isolation <−15dB criterion)

**To-verify checklist**:
- [ ] Field normalization under multi-port excitation (per-channel P_acc? or matrix excitation?) — difference from the single-port FoM normalization (`pitfalls/numerical.md`)
- [ ] The Combine Results filter for a multi-port scenario (how the `"*"` trap in `pitfalls/schematic-cosim.md` is handled with multiple channels)
- [ ] S-parameter extraction and threshold criteria for isolation/coupling
- [ ] Survey of open-source decoupling libraries (see `design-notes/decoupling-strategies.md`)

**Depends on**: `recipes/build/` (need to be able to build a single element first), `recipes/b1-sar/` (single-channel field), `design-notes/decoupling-strategies.md` (strategy survey).
