# Artifact Pipeline — generate → lint → review → execute (with L0–L4 error ladder)

The **execution contract** for the artifact-first modeling architecture. Read
this before building any model from scratch or replaying a known design. It
replaces the old "agent drives CST live, block by block" pattern for the
**procedural** parts of modeling.

**Why**: driving CST live per-block made the agent (a) burn tokens re-reasoning
procedural VBA it should already know, (b) run slower than a human, and (c) hang
on COM round-trips / popups. This pipeline moves all procedural work OFFLINE
(generate artifacts without touching CST), then executes them in as few live
round-trips as possible. The agent's live reasoning is reserved for genuine
design decisions and for repairing the rare failing block.

Companion files: `scripts/render_templates.py` (Tier-A generate, ①),
`scripts/lint_vba.py` (L0), `scripts/batch_execute.py` (L1 executor),
`error-fixes.md` (L2 signature table) + `scripts/apply_error_fix.py`
(L2 executor that consumes it), `vba-knowledge/` (Tier-B few-shot),
`templates/*.vba.j2` (Tier-A deterministic; skill-local).

---

## 1. Generation tiers — how each `.bas` is produced

Classify each step, then pick the cheapest tier that can produce it correctly.

| Tier | Use when | How | LLM |
|---|---|---|---|
| **A — deterministic render** | the step is a known, fully-parameterized design (dipole, birdcage, standard setup/monitors/solver/export) | render a Jinja2 template `templates/*.vba.j2` with the parameter dict | **zero** |
| **B — few-shot single-shot** | a novel topology / geometry not covered by a template | `scripts/prepare_tierb_gen.py` scaffolds it: `prepare_tierb_context(step, topology, spec)` deterministically selects the relevant `vba-knowledge/*.md` blocks + doc pointers + pitfall constraints and bundles them; the main agent makes ONE generation call; `finalize_tierb_block` strips fences/Sub Main, lints, and writes the `.bas` into `artifacts/<step>/` — same layout as Tier A, so lint→batch_execute→L2/L3 treat A and B output identically. No agentic loop. | one call / step |
| **C — agent reasoning** | a genuine design decision (which coil type, change a topology, tuning strategy) | the agent reasons in the main loop | yes |

Rule of thumb: **A first, B if A can't express it, C only for decisions.** Never
use C to reproduce a procedure that A or B already covers — that reintroduces
the thinking-loop.

## 2. Generate phase (OFFLINE — no CST)

For each modeling step, produce a `.bas` file. Standard step order for a
from-scratch coil (mirrors the verified `dipole-from-scratch` flow):

```
parameters → units/background/boundary → materials → geometry
→ ports → monitors → mesh → solver   (+ schematic match blocks if tuned)
```

Write every artifact under the project's run folder:

```
results/<project_id>/artifacts/<step>/<name>.bas
```

e.g. `results/dipole_scratch/artifacts/geometry/create_dipole.bas`.

### 2.1 The build manifest — Tier-A rendering, driven by one JSON

Tier-A steps are rendered by `scripts/render_templates.py` from a **build
manifest** (`results/<id>/artifacts/build_manifest.json`). One manifest = one
whole build; running it emits every `.bas` in one offline call (no CST):

```
python .../scripts/render_templates.py --manifest results/<id>/artifacts/build_manifest.json
```

Manifest shape:

```json
{
  "project": "<id>",
  "globals": { ...shared params... },
  "steps": [
    {"step": "setup",    "template": "common_setup", "kind": "history"},
    {"step": "geometry", "template": "dipole_build", "kind": "history",
     "params": {"L_line": "300"}}
  ]
}
```

- `kind`: `history` (raw block → `add_to_history`) or `macro` (Sub Main →
  `cst_execute_vba_tool` / `cst_schematic_execute_vba_tool`). Defaults per
  template are baked into the renderer; override per step when needed.
- `params`: step-local values. Missing template vars fall back to the
  template's own defaults; an *undefined* var (no default, not supplied) is a
  hard render error (`StrictUndefined`) — a real bug, not silently blanked.

### 2.2 Shared parameters live in manifest `globals` — never per-step (IRON RULE)

Any quantity used by **more than one template** — above all **frequency and
units** (`units_frequency`, `freq_min`, `freq_max`, `f0`,
`monitor_frequencies`) — is defined **exactly once** in the manifest's
top-level `globals` block. The renderer merges `globals` into every step's
params (step-local values win). This is the single source of truth: a shared
value **cannot drift** between `setup`, `monitors`, and `solver` because there
is only one place it is written.

**Why this rule exists (case-agnostic):** if each template carries its own
frequency/unit default and the manifest fills them per-step, they *will* drift
— e.g. `Units.Frequency "MHz"` in setup but `MonitorValue "0.21"` (GHz) in
monitors = a silent 1000× error that ruins every field. This is not a dipole
quirk; it bites any coil/frequency. Fixing it per-case (annotating each build)
does not scale — the fix is structural: **one definition, merged everywhere.**

**Backstop — semantic gate:** before rendering, `render_templates.py` runs a
cross-step check that every working frequency (`f0`, each `monitor_frequencies`
entry) sits inside the sweep band `[freq_min, freq_max]`. Out-of-band → refuse
to render (exit 1), flagging the likely unit mismatch. `lint_vba.py` cannot
catch this — it is a per-*file* structural linter; unit agreement is a
per-*manifest* semantic property, so it is enforced at render time. Override
with `--no-freq-check` only when a band genuinely excludes a monitor on purpose.

## 3. L0 lint (deterministic, zero LLM) — BEFORE any CST call

Run `scripts/lint_vba.py` on the generated `.bas` (file or whole `artifacts/`
dir). It strips markdown fences / stray prose, checks `With/End With`,
`Sub/End Sub`, `If/End If`, `For/Next`, `Do/Loop` balance, and flags
duplicate or reserved-word parameter names (pitfall #1).

```
python .../scripts/lint_vba.py --fix results/<project_id>/artifacts
```

`--fix` repairs what is mechanically fixable (fences, trailing whitespace, Sub
Main wrap for `--kind macro`). Any remaining ERROR-severity issue must be
resolved (regenerate that step) before execution. WARNINGS don't block.

## 4. Review gate

Present a compact **defaults card + artifact list** (which steps, key parameter
values, file paths) and get confirmation before executing — same discipline as
before any expensive solve. For `demo` / recording, this is also where the user
confirms they're ready to record.

## 5. Execute phase — two modes, ONE artifact set

Both modes replay the **same** pre-generated `.bas` files via
`scripts/batch_execute.py` (sent through `cst_run_python_tool`, where `de` /
`project` / `model3d` are in scope). The critical fact: the per-block loop lives
in that Python script — **the LLM is not in the loop**. The agent sends it once
and gets back one structured table.

### `execution_mode = batch_quiet`  (default / production)
One `cst_run_python_tool` call:
```python
# encoding="utf-8" is REQUIRED: on a zh-CN Windows the default open() codec is
# cp936/gbk and chokes on the non-ASCII chars in the script's docstrings
# (UnicodeDecodeError). Same for reading any .bas the loop opens.
exec(open(r"...\scripts\batch_execute.py", encoding="utf-8").read())
BLOCKS = [
    ("define parameters",       r"...\artifacts\parameters\parameters.bas"),
    ("set units and background", r"...\artifacts\setup\setup.bas"),
    ("define materials",        r"...\artifacts\materials\materials.bas"),
    # ...
]
result = run_blocks(project, de, BLOCKS, quiet=True)
```
- wrapped in `de.quiet_mode_enabled()` → no Abort/Retry/Ignore popups
- fewest COM round-trips, fastest
- stops at the first failing block (checkpoint in `result["failed_index"]`)

### `execution_mode = demo_stepwise`  (recording)
Same `BLOCKS`, but replayed so the CST front-end stays visually in sync. Only
these four things must hold (nothing more — no rehearsal / dry-run):
- **quiet mode OFF, front-end visible**
- **one block per `cst_add_to_history_tool` call** (so the viewport repaints)
- **between blocks: Rebuild + fit-view** (`ResetViewToStructure` for 3D)
- **milestone pauses (`AskUserQuestion`) + milestone narration**

Full visualization cheat-sheet (view-switch commands, schematic Python methods,
milestone points) stays in `recipes/build/demo-recording-mode.md`.

Mode selection: default `batch_quiet`. If the request contains a demo trigger
(demo / recording / screen capture / "I want to see it happen live in CST") → `demo_stepwise`.

## 6. Error ladder L0–L4 (runtime)

When L1 reports a failed block, walk the ladder — cheapest/most-deterministic
first, stop as soon as the block succeeds:

| Layer | Trigger | Action | LLM |
|---|---|---|---|
| **L0** | before execution | `lint_vba.py` static lint/repair | zero |
| **L1** | during execution | `batch_execute.run_blocks` per-block try/except; stop at failing block, return structured table | zero |
| **L2** | a block failed | `scripts/apply_error_fix.py` (`try_l2_fix`) matches the error against `error-fixes.md` signatures; for the .bas-text-patchable kinds (F1/F2/F4/F10) it rewrites the failing `.bas` deterministically and returns `resume_index`; for match-only kinds (F3/F5–F9/F11) it returns the `action` to apply. No match → L3. | zero |
| **L3** | L2 no match | `scripts/prepare_l3_repair.py` scaffolds it: `prepare_l3_context` deterministically selects the relevant `vba-knowledge/*.md` (by block-title + error keywords) + doc pointers and bundles them with the failing `.bas` + error; the **main-thread agent** regenerates ONLY that block; `finalize_l3_repair` writes+lints it and returns `resume_index`. Retry budget **≤ 2** enforced via a state file, then → L4. | bounded (LLM only rewrites the one block) |
| **L4** | L3 exhausted | surface to human with full context; keep completed blocks (checkpoint) so nothing is redone | — |

Resume after any fix: call `run_blocks(..., start_index=result["failed_index"])`
so already-successful history is not re-run.

Demo error handling: if a block fails mid-recording → pause → main agent runs
L2/L3 off the visible timeline → resume `demo_stepwise` from the checkpoint
block. (No pre-recording rehearsal.)

## 7. What is NOT changed by this pipeline

Solve + post-processing stay interactive through the existing MCP tools — they
are genuinely stateful/decision-driven and have a small surface:
- async solve (`model3d.start_solver()` + poll)
- `cst_configure_ac_combine_tool` → `cst_run_circuit_cosimulation_tool`
- `cst_calc_b1_field_tool`
- field export (SelectTreeItem + ASCIIExport), scripted plotting

MCP is still required end-to-end: it is the COM bridge and owns everything
beyond modeling. This pipeline only changes **how modeling talks to MCP**
(batch instead of chatty), not whether MCP exists.

## 8. Checklist (one build)

1. classify steps → Tier A/B/C
2. generate all `.bas` OFFLINE → `results/<id>/artifacts/<step>/`
3. `lint_vba.py --fix` → resolve ERRORs
4. review gate (defaults card + file list)
5. execute: `batch_quiet` (default) or `demo_stepwise` (recording)
6. on block failure → L2 → L3 → L4, resume from checkpoint
7. hand off to solve + post-processing (unchanged MCP path)
