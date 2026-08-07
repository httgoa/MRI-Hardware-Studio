# Paper Reproduction Orchestrator

Multi-stage pipeline for reproducing an MRI RF coil paper end-to-end, with visible stage gates
and context compression at every boundary.

## Why this recipe exists
Reproducing a paper naively in one long conversation blows up the context window (24+ solves ×
~50 turns each = millions of tokens). This pipeline separates scientific decisions, CST work,
and audit/reporting into bounded stages. Each boundary emits a compact artifact instead of
carrying raw solver logs forward. Subagents are optional and may be used only when the active
collaboration instructions permit delegation; the stage boundaries do not depend on them.

## Stage graph

```
01_literature → 01_paper_spec.md              (analyze paper + freeze scope, protocol, and acceptance rules)
     ↓
02_baseline_build → 02_baseline_build.md      (build + solve reference config; BLOCKING verification gate)
     ↓
03_parameter_sweep → 03_sweep_results.md      (shape per paper_type: sweep N / single-demo / comparison)
     ↓
04_postproc → 04_postproc.md                  (B1+/SAR maps + paper Fig compare)
     ↓
99_final_report → 99_final_report.md          (validation audit + scientific conclusion + evidence index)
```

**`paper_type` (from Stage 01) shapes Stage 03**: `optimization-sweep` → loop + pick optimum; `single-design-demo` → one characterization run; `comparison` → run discrete designs + tabulate. The framework has NO default sweep assumption and NO default metric formula.
**Solver is conditional**: `requires_sar: true` → HF TD hexahedral (native 10g SAR); else pick by physics. See Stage 02.
**Modeling method (Stages 02/03) = artifact-first pipeline** (`../../driving/artifact-pipeline.md`,
verified 2026-07-20 on birdcage): generate `.bas` OFFLINE (Tier A render / Tier B few-shot),
L0 lint, then batch-execute in ONE `cst_run_python_tool` round-trip — the LLM is NOT in the
per-block loop. On a failed block, the within-stage recovery is the **L0–L4 error ladder**
(L2 deterministic `error-fixes.md` patch → L3 bounded subagent rewrite of one block → L4 user),
resuming from the checkpoint. This is the standard for ALL procedural VBA; only genuine design
decisions are reasoned live (Tier C). Solve + post-processing stay interactive (unchanged).

Each stage has its own recipe at `stage-NN-<name>.md`. In demo mode these stages are also the
visible narrative: do not hide Stage 01 preparation or Stage 99 conclusions behind the
CST execution sequence.

## Artifact convention (READ CAREFULLY — every stage writes one)

Every stage writes ONE markdown file at `results/<project>/stages/NN_<name>.md`. Format:

```markdown
---
stage_id: 02_baseline_build
status: passed | partial | blocked
project: paper_fractionated_dipole
inputs:
  - stages/01_paper_spec.md
outputs:
  - results/paper_fractionated_dipole/log/baseline_30cm.h5
  - results/paper_fractionated_dipole/output/baseline_B1p_check.png
stats:                     # ONLY numeric/short-string facts, no arrays
  freq_mhz: 298
  dipole_length_mm: 300
  s11_at_298_db: -3.2
  peak_b1p_ut_per_sqrtW: 1.8
  solve_time_s: 42
handoff_hash: {phantom_bbox_mm: [-250, 250, -250, 250, 0, 500], grid_step_mm: 2}
---

## What this stage did
1–3 sentences.

## Key decisions / assumptions
Bullet list.

## Blockers / warnings
Bullet list, or "None".

## What downstream needs from this
Explicit — the next stage should not have to guess.
```

**Rules**:
- `stats:` = only numbers / short strings. No arrays, no VBA text, no raw log dumps. Bigger data goes in `log/` and gets **referenced by path** from `outputs:`.
- Total artifact ≤ 300 lines / ≤ 30 KB. If it grows past that, put detail in `log/<stage>_detail.md` and just link it.
- A stage's **return value** to the main loop is a 3–5 line summary of `status:` + key stats,
  not the full artifact. The main loop reads the artifact on demand.

## Stage dispatch template (main loop side)

For each stage:
1. Confirm previous stage's artifact exists and `status: passed` (or explicit `partial` handoff).
2. **Check the verification gate (if the upstream artifact has one).** After Stage 02 especially: read `verification.gate`. If `FAIL`/`blocked`, **STOP — do NOT dispatch Stage 03** (sweeping N configs on a broken baseline wastes the whole sweep). Surface the suspected cause to the user.
3. Execute the stage on the main thread, or—only when current collaboration instructions allow
   it—dispatch a bounded agent with a **self-contained** prompt that:
   - Names the project id and the exact recipe file to follow
   - Lists which upstream artifacts to Read (paths)
   - States "when done, write `stages/NN_<name>.md` following the artifact convention"
   - States "return 3–5 line summary; do NOT paste the full artifact"
4. Read the artifact once, check its `verification:` block, update the main task list, and
   dispatch the next stage.

**Do NOT** let delegated stages chain directly. Every stage boundary must go through the main
loop for compression and gate enforcement.

## Verification gates (review→revise as boundary checks, not a separate stage)

The pipeline is otherwise a straight line with no feedback — gates add the missing verification signal. Each CST-driving stage writes a `verification:` block; the main loop reads it at the boundary:

| Boundary | Question | Enforcement |
|---|---|---|
| after 01 | Source/scope frozen, acceptance rules declared, and spec self-consistent? Anchors sufficient to *detect* a wrong result? | blocking if core inputs are unresolved; otherwise soft |
| **after 02** | **Baseline physically plausible (order-of-magnitude vs paper anchor)? If off ≳10× → STOP.** | **BLOCKING** |
| after 03 | Our optimum/values match paper's? If not — bug or real discrepancy? | soft (flag in artifact) |
| after 04 | Do figures *actually* match, or are we fooling ourselves? | soft (a skeptic `general-purpose` subagent prompted to REFUTE the match is a strong option) |

The post-02 blocking gate is the highest-leverage compute check. Soft gates flag concerns
without silently redefining success.

## Single-instance CST guardrail

Stages that drive CST (02, 03, 04 and any Stage 99 robustness re-solve) must drive it
**strictly sequentially through the one MCP-managed session**. Never run two CST-driving stages
in parallel. Parallel instances cause "Simulation already running" / orphan `.lok` locks, and
abort/close cascades can kill other projects or disconnect the session.

## When a stage fails
- `status: partial` = kept going, some outputs missing. Downstream may still run if the missing bit is optional (e.g. SAR postproc when only B1+ is needed).
- `status: blocked` = cannot proceed. Main loop stops the pipeline, does NOT dispatch downstream. User decides whether to fix + retry or skip the paper.

## What NOT to do
- Don't write full CST message logs into the artifact. Save the log file to `log/` and reference it.
- Don't skip writing the artifact even if the stage was trivial — downstream depends on the schema.
- Don't run all stages in one big subagent — that defeats the compression.
- Don't paste 3D field arrays into artifacts. Reference the `.h5` path.

## Compression accounting (Stage 99 fills this in)
At the end of the pipeline, Stage 99 summarizes:
- Total artifacts written + sum of their sizes (KB)
- Total `log/` size (MB)
- Estimated turn count per stage vs naive-one-shot baseline
- Any stage where compression was insufficient (artifact >30 KB or subagent context near limit)

Related: `stage-01-literature.md` through `stage-99-final-report.md`.
