> Warning: **ROADMAP placeholder — unverified, no executable template, do not use this to drive CST.** When implementing, land it per `recipes/_TEMPLATE.md` and delete this notice.

# Recipe (placeholder): Novel Structure Exploration

**Scope**: novel RF structures beyond conventional dipoles/birdcages — metamaterials/metasurfaces, resonators, novel birdcage variants, novel high-field pTx antennas (e.g. leaky-wave antennas).

**Expected future recipes** (naming convention):
- `metasurface-resonator.md` — metasurface/resonator arrays (enhancing B₁⁺, focusing the near field)
- `birdcage-variants.md` — novel birdcage body coils (high-pass/low-pass/bandpass/hybrid, butterfly end rings, etc.)
- `leaky-wave-ptx.md` — high-field leaky-wave antenna pTx elements
- `dielectric-pad.md` — high-permittivity pad-assisted shimming

**To-verify checklist**:
- [ ] Modeling building blocks for each structure (unit cell + boundary/Floquet ports for periodic structures?)
- [ ] Special mesh/solver requirements for resonant structures (high Q → is steady-state limit/FD more suitable? see `pitfalls/solver-meshing.md`)
- [ ] Whether to keep FoM=B₁⁺/√SAR or introduce new metrics (focusing quality, penetration depth)
- [ ] Literature survey: see `design-notes/novel-structures.md`

**Depends on**: `recipes/build/`, `design-notes/novel-structures.md`, `foundations/mri-physics.md`.
