# vba-knowledge — Tier B few-shot unit library (index)

The **Tier B** knowledge base for the artifact-first pipeline
(`../artifact-pipeline.md`). When a modeling step is a NOVEL topology that no
`templates/*.vba.j2` (Tier A) covers, the generator does ONE few-shot LLM call
seeded with the relevant file(s) here — it picks canonical units and fills in
parameter expressions, it does NOT invent VBA. LEAM `modeling_3d.md` analog.

The mechanism is scaffolded by `../../scripts/prepare_tierb_gen.py`:
`prepare_tierb_context(step, topology, spec)` deterministically selects which
files here to feed (by step category + coil topology) and attaches the pitfall
constraints; the agent makes ONE generation call; `finalize_tierb_block` strips
fences/Sub Main, lints, and writes the `.bas` into `artifacts/<step>/` — the
same layout Tier A uses, so downstream lint→batch_execute→L2/L3 is identical.

## Files
| File | Covers |
|---|---|
| `geometry-primitives.md` | Brick/Cylinder/Sphere/Cone/Torus/Prism/ECylinder/AnalyticalFace + 2.5D curves + Extrude/Rotate |
| `boolean-transform.md` | Add/Subtract/Intersect/Insert/Imprint + Translate/Rotate/Mirror/Scale (array-copy) |
| `mri-setup.md` | Units/background/boundary + materials (with colours) |
| `ports-monitors-mesh.md` | DiscretePort/FacePort + E/H/loss/farfield monitors + mesh |
| `solvers.md` | FD (B1+) / Eigenmode / TD-hex (SAR) + async run + minimal-setter rule |
| `coil-geometry.md` | Birdcage / surface loop / saddle / phased-array composition patterns |
| `schematic-match.md` | L-match placement + wiring + tuning (→ verified `../vba-blocks/dipole-schematic.md`) |
| `field-export.md` | SelectTreeItem + ASCIIExport (→ verified `../vba-blocks/field-export.md`) |

## How Tier B relates to the rest
- **Tier A** (`templates/*.vba.j2`): deterministic whole-step macros for KNOWN
  designs (dipole fully verified). Zero LLM. Use first.
- **Tier B** (this dir): generalized unit library for NOVEL topologies. One
  few-shot LLM call per step, constrained by these canonical snippets.
- **`../vba-blocks/`**: the VERIFIED dipole ground truth these were generalized
  from — the source of truth when the two disagree.

## Rules
- All blocks here are **raw history commands (no `Sub Main`)** unless a file says
  `kind=macro` (field-export) — see `../artifact-pipeline.md` §3 (L0 lint).
- Compose complex shapes from primitives + booleans; do not reach for exotic
  single-call APIs.
- On any "Method or property not found" STOP and check the official VBA
  reference (SKILL iron rule) — never guess a signature.
