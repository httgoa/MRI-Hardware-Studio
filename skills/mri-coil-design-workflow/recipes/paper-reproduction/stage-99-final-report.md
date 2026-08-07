# Stage 99 · Final Scientific Report and Reproducibility Handoff

**Goal**: Produce one `99_final_report.md` that answers the paper-reproduction question,
performs the final validation audit, explains discrepancies and limitations, and lets another
operator locate and replay the evidence. Context-compression accounting is secondary.

## Inputs
- `stages/01_paper_spec.md`
- `stages/02_baseline_build.md`
- `stages/03_sweep_results.md`
- `stages/04_postproc.md`

## Method
1. Read all upstream artifacts; do not infer success from attractive figures.
2. Audit every Stage 01 target against its predeclared tolerance: paper value, reproduced
   value, error, trend/optimum agreement, evidence path, robustness limits, and verdict.
3. Lead with a plain-language answer: what was tested, what reproduced, what did not, and the
   confidence level. A polished figure never overrides a failed quantitative target.
4. Summarize the paper's question, mechanism, baseline, and original evidence type before
   describing CST work.
5. Present the exact scope/exclusions, paper-to-CST translation, solver/mesh/excitation,
   phantom/body, case matrix, ROI, normalization, and processing commands. Distinguish
   reported, derived, digitized, and assumed values.
6. Aggregate the claim-by-claim scorecard. Use numeric error/tolerance where possible and
   separate value agreement, trend agreement, and visual similarity.
7. Explain material mismatches, failed cases, robustness limits, assumption sensitivity, and
   the strongest skeptical reason the apparent match could be misleading.
8. Include a reproducibility inventory: source hash, environment, manifests, CST projects,
   raw data, processing scripts/commands, figures, and stage artifacts.
9. Recommend next work prioritized by effect on scientific confidence.
10. Append concise **process/compression accounting** after the scientific conclusion:
   - Count subagent dispatches (main loop task list length)
   - Sum artifact sizes (kB)
   - Sum `log/` size (MB — via Bash `du` or Python)
   - Estimate turns per stage (from the main task list metadata if visible; else 3–5 line rough guess)
   - Compare to naive baseline: "if all 24 solves + all their logs stayed in ONE context, how many turns would this have taken?" — rough estimate is enough
11. Note pipeline lessons: which stage was too big/small and which evidence fields were missing.

## Handoff — write `stages/99_final_report.md`

Template:
```markdown
---
stage_id: 99_final_report
status: passed | partial | blocked
project: <project_id>
paper: "<title>"
inputs:
  - stages/01_paper_spec.md
  - stages/02_baseline_build.md
  - stages/03_sweep_results.md
  - stages/04_postproc.md
outputs:
  - stages/99_final_report.md
overall_status: reproduced | partially_reproduced | not_reproduced
confidence: high | medium | low
agreement_summary: "<one precise sentence>"
---

# Paper reproduction: <title>

## Executive conclusion
State which exact claims/figures were reproduced, at what accuracy, and with what confidence.

## Paper analysis in brief
- Research question and proposed mechanism
- Baseline and claimed improvement
- Evidence types used in the original paper

## Scope and success criteria
| Target | Acceptance rule | Outcome |
| --- | --- | --- |
| T1 | ... | pass / partial / fail |

## Reproduction method
- Paper-to-CST translation and assumptions
- Geometry/material/excitation/solver/mesh
- Case matrix, normalization, ROI, and post-processing

## Quantitative results
| Target / metric | Paper | Reproduction | Error | Tolerance | Verdict |
| --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... |

## Trend and figure comparison
Explain curve shape, plateau/optimum, spatial pattern, and visual differences. Link the
paper-original comparison figures generated from the current run.

## Robustness, discrepancies, and limitations
- Robustness/sensitivity checks performed
- Mismatch classifications and unresolved risks
- Experimental or licensed assets that were not reproduced

## Reproducibility inventory
| Item | Path / value | Validation state |
| --- | --- | --- |
| Source PDF hash | ... | verified |
| CST projects | ... | saved |
| Build/case manifests | ... | complete |
| Raw HDF5/CSV | ... | complete / partial |
| Scripts and commands | ... | recorded |
| Final figures | ... | current-run |

## Recommended next work
Numbered by impact on scientific confidence.

## Process accounting
| Stage | Artifact size (KB) | Log size (MB) | Solves | Retries | Status |
| --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... |

Baseline (naive one-shot, estimated): N turns, all context in one place → would have blown ~<n> tokens.
Compressed pipeline: N stages × <turns/stage> mean → ~<n'> tokens (rough).
Compression ratio: ~<n/n'> ×.

Briefly note context compression and workflow lessons here, after the scientific conclusion.
```

## Demo presentation rule

At the final milestone, show the executive conclusion, scorecard, comparison figures, and
reproducibility inventory. Merely saying “outputs generated” is not a completed paper
reproduction demo.

## Return value to main loop
3–5 lines: overall verdict, passed/total targets, confidence, largest remaining uncertainty,
and report path.
