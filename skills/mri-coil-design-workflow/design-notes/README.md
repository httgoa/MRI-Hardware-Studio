# Design Notes — Open-Ended Exploration of Roadmap Directions

This is where **directions still being thought through** live: literature surveys, open-source library evaluations, method selection, feasibility sketches. Division of labor with `recipes/`:

| | `recipes/` | `design-notes/` (this directory) |
|---|---|---|
| Content | **Runnable steps** (a verified or to-be-verified operation sequence) | **Directions still being thought through** (survey/selection/sketch) |
| Maturity | Becomes a recipe once verified | Open, may include unresolved questions and to-do research items |
| Drives CST | Yes | No (contains no mandatory execution steps) |

When a direction matures from a design-note to something executable, land it as a formal recipe per `recipes/_TEMPLATE.md`, and turn the design-note into that recipe's background/reference material.

## Current notes
- `decoupling-strategies.md` — decoupling strategies + open-source library survey (corresponds to `recipes/decoupling/`)
- `multichannel-ptx.md` — multichannel/pTx methods (corresponds to `recipes/multichannel/`)
- `novel-structures.md` — novel-structure literature (corresponds to `recipes/novel-structures/`)
