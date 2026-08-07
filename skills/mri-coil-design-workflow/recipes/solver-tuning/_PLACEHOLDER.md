> Warning: **ROADMAP placeholder — unverified, no executable template, do not use this to drive CST.** When implementing, land it per `recipes/_TEMPLATE.md` and delete this notice.

# Recipe (placeholder): Time / Accuracy Optimization (solver strategy + meshing)

**Scope**: compressing solve time while keeping result accuracy acceptable — solver choice, adaptive/local mesh refinement, steady-state limit, exploiting symmetry planes.

**Expected future recipes** (naming convention):
- `mesh-refinement-strategy.md` — trade-off between local refinement of key regions (feed gap/phantom surface layer/thin conductors) vs. global density
- `solver-selection.md` — a decision tree matching TD vs FD vs Eigenmode to the task (extends `pitfalls/solver-meshing.md`)
- `steadystate-accuracy-tradeoff.md` — a systematic sweep of steady-state limit vs. accuracy (currently only single-point data at −30/−40dB)
- `symmetry-planes.md` — applicability conditions and validation for halving/quartering compute cost with electric/magnetic symmetry planes

**To-verify checklist**:
- [ ] Known data point: steady-state limit −30dB vs −40dB gives FoM difference <1.5% (`pitfalls/solver-meshing.md`) — expand into a systematic curve
- [ ] Mesh-convergence study: convergence criterion for max SAR / B₁⁺ vs. mesh density
- [ ] Whether symmetry planes still hold once a phantom is introduced (the Zsymmetry electric precondition)
- [ ] Measured benefit of the GPU-acceleration toggle

**Depends on**: `pitfalls/solver-meshing.md`, `foundations/cst-simulation-sop.md` §B, §D.4.
