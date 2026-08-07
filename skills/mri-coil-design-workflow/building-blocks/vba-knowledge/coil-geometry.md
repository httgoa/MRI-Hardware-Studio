# Coil Geometry — Tier B composition patterns (MRI coils)

How to COMPOSE the common MRI coil topologies from the primitives in
`geometry-primitives.md` and the array/transform ops in `boolean-transform.md`.
These are design-level recipes, not verified verbatim VBA (only the dipole is
fully verified — see `../vba-blocks/dipole-build.md`). Treat as a starting
scaffold: generate, L0-lint, then execute one block and inspect before trusting.

> Parameter estimation (radius, rung count, capacitance) lives in the pure-Python
> `coil_library/birdcage.py` (`BirdcageDesigner.design()`); use it to seed
> geometry parameters, then CST-tune. A Jinja2 scaffold exists at
> `templates/birdcage.vba.j2` (not yet end-to-end verified).

## Birdcage (high-pass / low-pass / band-pass)
Composition:
1. **Two end-rings** — thin cylinders (`Cylinder` with `InnerRadius`≈`OuterRadius`)
   or `Torus`, one at `+leg/2`, one at `-leg/2` along Z, radius = coil radius.
2. **N rungs** — model ONE rung (`Brick` or thin `Cylinder`) on the ring radius at
   angle 0, then **array by rotation**: `Transform ... Rotate`,
   `Angle "0","0",360/N`, `MultipleObjects "True"`, `Repetitions "N-1"`.
3. **Capacitor gaps** — subtract a small filler brick from each rung (high-pass)
   or each ring segment (low-pass) where a lumped cap will sit; place a
   `DiscretePort`/lumped element across each gap.
4. Endring/rung material = `Copper (pure)` or `PEC`.

Key parameters (from `coil_library/birdcage.py`): `radius`, `length` (leg),
`num_rungs` (even, e.g. 8/12/16), `rung_width`, `cap_gap`. Larmor sets the target
mode; caps tune it.

## Surface loop (single/receive element)
- A conductor **ring trace**: draw two concentric `Circle` curves (outer/inner)
  → `ExtrudeCurve` the annulus to a thin copper strip, OR a large-radius `Torus`
  with small tube radius.
- **Feed gap**: subtract a small brick from the ring; put a `DiscretePort` across it.
- Optional tuning/matching caps at the gap (schematic, see `schematic-match.md`).

## Saddle / birdcage-leg pair
- Two conductors bent onto a cylinder surface: either `AnalyticalFace` with a
  law mapping (u,v)→cylinder, or bent `Brick`s rotated to the cylinder tangent.
- Symmetric about the axis; mirror one arm to the other (`Transform ... Mirror`).

## Phased array
- Model ONE element (surface loop above), then **array-copy** by translation
  and/or rotation: `Transform`, `MultipleObjects "True"`, `Repetitions`.
- Each element gets its OWN port (increment `PortNumber`); overlaps/decoupling
  handled by geometry spacing + schematic.

## Rules
- Build ONE element/rung, then array with a single `Transform` — never model N copies by hand.
- Put each independent conductor in `component1` with a unique `.Name`; ports numbered per element.
- Verify the first arrayed block visually (or via `probe_project.py`) before generating the rest of the pipeline — array math errors are cheap to catch early, expensive after a solve.
- Coil tuning is a genuine decision loop (Tier C) — do it via the schematic (`schematic-match.md`), not by regenerating geometry.
