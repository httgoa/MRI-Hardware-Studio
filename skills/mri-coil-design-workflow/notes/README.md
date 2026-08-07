# notes/ — distilled learning references (read on demand, not top-to-bottom)

These are the **learning/reference layer**, distinct from the execution contract
(`../artifact-pipeline.md`, `../error-fixes.md`, recipes). They fall in two
groups: **manual digests** (official CST docs, condensed) and **reproduction
logs** (per-case verified VBA + the exact traps hit). None is read cover-to-cover
— consult the one that matches the task. This index is the "when to read which".

Two things route here automatically now (they used to be save-only):
- **SKILL iron rule** → `cst-help-index.md` first (locate the right Online Help
  page by task), and the matching `repro-*` when the failing op was reproduced.
- **Tier-B generation** (`../../scripts/prepare_tierb_gen.py`) → pulls the
  decision digests + topology repro log into the generation context (see the
  `decision_notes` field): solver/geometry/port steps get `cst-hf-fundamentals.md`;
  a birdcage topology also gets `repro-03-mri-coil.md`, etc.

## Manual digests (decision knowledge for a NEW case)
| File | Read when | Carries |
|---|---|---|
| `cst-hf-fundamentals.md` | choosing a **solver / boundary / mesh / port** for a new coil | §2 solver-selection table (antenna→Transient, filter/resonator→FD, cavity→Eigenmode), §3 adaptive-mesh frequency-point rule, §4 port-type selection, §5 open-boundary/antenna notes |
| `cst-help-index.md` | you need an official Online Help page (iron rule) | task → `.htm` map over ~1413 pages, pre-tagged MRI-relevant / general / extended. Narrows the grep — read the specific page, don't scan the whole help |
| `cst-circuit-sam.md` | building an **EM/circuit co-sim** (tuning/matching, schematic) | co-simulation mental model; complements `../vba-knowledge/schematic-match.md` |
| `cst-manuals-map.md` | you need to know **which manual** covers a topic | map of the bundled CST PDFs → chapters |

## Reproduction logs (verified VBA + traps, per case)
Read the one matching the topology you're about to build — it has the exact
working history VBA and the specific errors already hit (often more precise than
the generic `../mcp-pitfalls.md` / `../error-fixes.md`). Machine-actionable traps
should also live in `error-fixes.md` (L2) / `mcp-pitfalls.md`; these logs are the
human-narrative source + full context.

| File | Case | Notable traps captured |
|---|---|---|
| `repro-01-dipole-antenna.md` | half-wave dipole antenna | basic build + Transient |
| `repro-02-dipole-array.md` | dipole array | array copy, per-element ports |
| `repro-03-mri-coil.md` | **1.5T body coil (birdcage), 63 MHz** | `LumpedFaceElement` needs `Pick.PickEdgeFromId` first (→ error-fixes F7); rotating-B1 via `SimultaneousExcitation` + `PhaseRefFrequency`; caps one-per-history-block; SAT import (parametric birdcage impractical) |
| `repro-04-patch-fd.md` | patch antenna (FD solver) | FD tetra, patch feed |
| `repro-05-single-coil.md` | single coil / differential | differential MWSSCHEM net API traps (→ pitfalls #16/#17) |
| `repro-06-fractionated-dipole.md` | fractionated dipole @7T | segmented dipole + passive `rlcserial` LumpedElement bridges; the paper-reproduction ground truth |
| `repro-07-circular-patch-td.md` | circular patch antenna (TD, official Component Library) | circular patch + substrate + waveguide port; TD/farfield monitor path |
| `repro-08-circular-resonator.md` | circular resonator (two-port, official Component Library) | `Parameters.json` pre-injection; annular resonator + two picked-face waveguide ports; exact S11/S21 replay |
| `repro-09-circular-patch-multilayer.md` | circular patch antenna (HF Multilayer, official Component Library) | face-derived PEC sheets from thick patch/feed; HF Multilayer solver replay |

## Rule
- These inform decisions and seed generation; they are **not** the execution
  path. A verified mechanical fix belongs in `error-fixes.md` (so L2 can apply it
  zero-LLM); a verified canonical snippet belongs in `../vba-knowledge/` (so Tier
  B seeds from it). When you extract such a thing from a repro log, promote it
  there and leave the log as the narrative source.
