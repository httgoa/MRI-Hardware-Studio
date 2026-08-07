# Recipe: <task name>

**Goal**: one sentence stating what problem this recipe solves and what it produces.

**Applicability**: when to use it; when not to.

**Preconditions**:
- Project state (already modeled / already solved / SAR template installed…)
- Required monitors (h-field / loss / e-field / farfield)
- Solver requirement (TD hexahedral / FD tetrahedral / eigenmode)

---

## Solver choice
Why this solver was chosen (align with `foundations/mri-physics.md` + `pitfalls/solver-meshing.md`).

## Step-by-step sequence (order is a constraint)
1. …
2. …
(Follow the full pipeline timing in `foundations/cst-simulation-sop.md`: model → save → async solve + guard → export H-field → SAR → read P_acc → extract metrics)

## Normalization
Normalize by accepted power (B₁⁺∝1/√P_acc, SAR∝1/P_acc, measure P_acc per case) — see `pitfalls/numerical.md`.

## Output
- Deliverable files (figures/CSV/json/report), stored under `results/<project_id>/output/`.

## Related
- Upstream/downstream recipe: `recipes/.../xxx.md`
- Building blocks: `building-blocks/vba-blocks/xxx.md`, `scripts/xxx.py`
- Known traps: `pitfalls/xxx.md`
