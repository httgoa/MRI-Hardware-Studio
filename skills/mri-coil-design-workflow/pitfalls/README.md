# Pitfalls — Trap Aggregation (why + how to avoid + origin)

This directory aggregates **real traps actually hit** while driving CST, organized by failure domain, as the single authoritative source. Each entry = symptom + root cause + workaround + origin + rule anchor.

## Three-way division of labor (important — prevents duplicated content from drifting back in)

The skill talks about "avoiding traps" in three places; responsibilities are strictly separated, and **the same fact is only detailed once, in pitfalls**:

| Document | Responsibility | Style |
|---|---|---|
| `foundations/cst-red-lines.md` | **Rules**: hard constraints that must be obeyed | Imperative, short, no long explanations; ends with `see pitfalls/xxx.md for detail` |
| `foundations/cst-simulation-sop.md` | **Execution order**: a per-case checklist + §E trap index table (this skill's only SOP file) | Step-by-step; §E keeps only one line of symptom + link |
| `pitfalls/*.md` (this directory) | **Explanatory backing**: why it happens, how to avoid it, first occurrence | Narrative, can be long, includes mechanism |

When updating trap content: **only edit the detail here in pitfalls**; red-lines / SOP only maintain "one rule line + link" — do not write the mechanism explanation back into them.

## Index (by failure domain)

| File | Covers |
|---|---|
| `session-stability.md` | COM channel contention, zombie mcp_server, cascading batch abort/close failures, GUI not repainting |
| `field-export.md` | 3D field materialization window (Storage.sdb), all-zero export, HDF5 structured array/Fortran order, ASCIIExport timing |
| `sar.md` | `SAR.Create` node invisible headless, `.m3d` archiving, scale-accepted silent failure on mismatch, E-field proxy falsification |
| `schematic-cosim.md` | series element spanning nets, `Externalport` case sensitivity, contaminated ports, AC Combine `"*"` popup, Update vs RunAndWait |
| `numerical.md` | dB conversion, B₁⁺ vs \|H\|, sign convention, gain vs \|E\|, SAR normalization |
| `solver-meshing.md` | TD first-solve dropping volume fields, steady-state limit, hexahedral SAR constraint, eigenmode frequency-range dialog |
| `mcp-pitfalls.md` | **Numbered traps #1-26**: MCP tool signatures / fabricated VBA APIs / differential schematic / reference-case handling + SAR·field-export·session (#18-26). The failure-domain files above are the **detailed explanations**; this file is the **numbered quick-reference table**, referenced by `#NN` from `recipes/paper-reproduction/` and `notes/repro-*`. Check here first for an unknown API/tool. |

## Entry format (unified template)

```markdown
### <Short title>
- **Symptom**: the symptom (verbatim error text / silent-failure behavior)
- **Root cause**: why it happens (CST's internal behavior mechanism)
- **Workaround**: how to avoid it (concrete operation sequence / parameters)
- **Origin**: the case where it was first hit (e.g. ind150 / FD_Optimize) + the related recipe
- **Rule anchor**: -> `foundations/cst-red-lines.md` (if it has been promoted to a red line)
```

Related memories (local private recall, not skill files): `cst-driving-red-lines`, `cst-sar-line-eproxy-and-steadystate`, `cst-sar-scale-accepted-fails-on-mismatch`, `b1-sar-optimization-no-per-case-matching`.
