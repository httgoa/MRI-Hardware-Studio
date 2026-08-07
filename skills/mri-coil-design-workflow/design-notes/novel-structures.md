# Design Note (placeholder): Novel-Structure Literature

> Open-ended survey notes, not executable steps. Land into `recipes/novel-structures/` once mature.

## To survey
- **Metasurfaces / metamaterials / resonators**: periodic structures for enhancing B₁⁺, focusing the near field, and increasing penetration depth. Modeling keys: unit cell + Floquet/periodic boundary; requirements high-Q resonance places on the solver/mesh.
- **Novel birdcage variants**: high-pass/low-pass/bandpass/hybrid birdcages, butterfly end rings, TEM coils; mode analysis (eigenmode solver).
- **Leaky-wave pTx antennas**: leaky-wave structures as transmit elements at high field; traveling-wave vs standing-wave excitation.
- **High-permittivity pads**: passive-shimming assistance.

## Evaluation metrics (keep the existing FoM or not)
- Whether the existing FoM=B₁⁺(d)/√SAR_max still applies, or whether to introduce new metrics such as penetration depth, focusing quality, B₁⁺ uniformity.

## Interface with existing assets
- Modeling building blocks: `recipes/build/`, `building-blocks/vba-blocks/` (currently dipole-only, needs extension for periodic-structure/birdcage blocks).
- Solver: `pitfalls/solver-meshing.md` (high-Q → FD/eigenmode; steady-state limit).
- Physics: `foundations/mri-physics.md`.

(TODO: fill in specific literature, structural parameter ranges, modeling feasibility assessment.)
