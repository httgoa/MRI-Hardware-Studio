# Batch Execution Contract (generate/execute separation) \u2014 READ before building geometry

**This is the execution-layer spec for the modeling stage.** Purpose: turn "regimented modeling" from "the agent driving CST block-by-block in real time" into "assembling ordered VBA blocks offline \u2192 one-shot silent batch injection", sidestepping three long-standing problems at once \u2014 getting stuck in thinking loops, being slower than a human, and CST hanging.

> Borrows the core paradigm of LEAM (an LLM antenna-design system): **modeling is not an agent loop, it's a static script executed once in a batch, with zero LLM on the execution side**. We don't bring in a Jinja2/lint machine; instead we get the same benefit directly with the MCP's existing `cst_run_python_tool` (which exposes `de`/`model3d`/`project`) + `de.quiet_mode_enabled()`.

---

## Core principle: separate generation from execution

1. **Generation (offline, doesn't touch CST)**: prepare an **ordered set of VBA blocks** for an already-finalized design \u2014 either baked into a builder script (e.g. `scripts/build_dipole.py`, zero LLM), or, for a new topology, single-shot assembled from the few-shot hard templates in `building-blocks/vba-knowledge/` (no looping). No MCP round trips at this stage.
2. **Execution (one-shot batch)**: inject the whole batch of blocks with **one** `cst_run_python_tool` call, looping `model3d.add_to_history` inside `with de.quiet_mode_enabled():`. Minimum round trips, popups suppressed, fastest.

**Why this sidesteps the three problems**:
- *Getting stuck thinking*: regimented steps no longer reason about VBA signatures block-by-block on the fly \u2014 block content comes from an already-verified script/knowledge base.
- *Slower than a human*: N rounds of "think \u2192 call MCP \u2192 read result" collapse into 1 batch execution.
- *CST hanging*: N COM round trips (each one a potential popup/stale read/COM contention) collapse into 1; `quiet_mode` suppresses dialogs.

---

## Two execution_modes (sharing the same batch of blocks)

| mode | When | Execution side |
|---|---|---|
| **`batch_quiet` (default)** | Production modeling, parameter-sweep case generation, non-recording scenarios | One `cst_run_python_tool` call + a quiet batch loop (pattern below) |
| **`demo_stepwise`** | Request contains "demo/recording/演示/录屏" (see the Demo trigger in SKILL.md) | Block-by-block `cst_add_to_history_tool`, visible in the foreground + milestone `ResetViewToStructure` + `AskUserQuestion` pauses. See `recipes/build/demo-recording-mode.md` (**unchanged**) |

**Key point**: the **block content and order are exactly the same** in both modes (parameters \u2192 units/background \u2192 boundary \u2192 materials \u2192 geometry \u2192 ports \u2192 monitors \u2192 solver, the hard order from SOP \u00a7B.1). The only difference is the execution side: quiet batch vs. visible block-by-block. All "thinking" is done during the generation stage; the demo recording only deterministically replays already-verified blocks at a human pace, with no loading stalls in front of the camera.

---

## batch_quiet execution mode (copy-and-use)

For an already-finalized design (dipole), call the builder directly, with zero block content re-entering context:
```python
# After cst_new_project_tool + cst_save_project_tool, one cst_run_python_tool call:
exec(open(r"<skill>\scripts\build_dipole.py", encoding="utf-8").read())
result = run_dipole_build(de, model3d, project)          # optionally pass params={"L_line":"320"} to tune
```

For a new topology (no builder) \u2014 inline ordered blocks, the same quiet loop:
```python
blocks = [
    ("define parameters", r'''MakeSureParameterExists("R","30")
...'''),
    ("set units and background", r'''...'''),
    # ... remaining blocks, order = parameters \u2192 units/background \u2192 boundary \u2192 materials \u2192 geometry \u2192 ports \u2192 monitors \u2192 solver
]
done, failed = [], None
with de.quiet_mode_enabled():
    for title, vba in blocks:
        try:
            model3d.add_to_history(title, vba)
            done.append(title)
        except Exception as e:
            failed = (title, f"{type(e).__name__}: {e}")   # record where it broke
            break
project.save()
result = {"done": done, "failed": failed}
```
`scripts/build_dipole.py`'s `run_batch()` is the generic version of this loop (including save + a shape-count self-check); a new topology can directly reuse `run_batch(de, model3d, project, blocks, expected_shapes=N)`.

---

## Failure handling: stop at the breakpoint, don't roll back the whole batch

- If some block's `add_to_history` throws \u2014 **stop at the bad block**, record `(title, error)`, **keep all previously-successful history** (don't roll back the whole batch). A human uses the title + error to locate the bad block, fixes the VBA, and resumes from that block.
- Why not auto-regenerate: regimented blocks are supposed to be deterministically correct; an error is usually a VBA signature/geometry issue, and letting the agent freely resend tends to drift off course and enter a loop. Fixing one spot is faster and more controllable than starting over.
- If a single-shot block fails for a new topology: **prefer handing the file to a human to fix** (LEAM-style fail-fast into one inspectable artifact); auto-regenerate at most once, then fall back to a human beyond that.

## Geometry self-check (lightweight, warn-only)

Do a **minimal self-check** after batch execution: compare `Solid.GetNumberOfShapes()` against the expected count (`build_dipole.py` already has this built in, expecting 5). On mismatch, **only warn, don't auto-rebuild** \u2014 rebuilding is left to a human decision (mirrors the idea behind LEAM's CheckSolid, but without hard-routing a re-run, to avoid a runaway loop).

## Reasoning-effort principle (regimented steps vs. decisions)

Not every step deserves expanded reasoning:
- **Regimented/mechanical steps** (injecting modeling blocks, saving, formatted export, reading a fixed tree node) \u2192 go through batch, **don't think**, just execute the deterministic blocks directly.
- **Design decisions** (choosing coil type/topology, turning geometry into an optimization variable, tuning strategy, diagnosing an anomalous result) \u2192 only these deserve expanded reasoning.

This directly addresses "intermediate regimented steps shouldn't get heavy reasoning".

---

## Boundary (batch only covers modeling)

Batch execution **only covers 3D modeling** (up through solver setup). Everything after that \u2014 **circuit tuning \u2192 AC combine \u2192 B1+/SAR post-processing** \u2014 still goes through the interactive MCP: these are decision/interaction surfaces with their own hard timing (see `foundations/cst-simulation-sop.md` \u00a7B.3\u2013B.7, `recipes/build/dipole-from-scratch.md` stage 2/3). **Solving itself** still uses async `start_solver` + polling (a hard rule \u2014 don't fold it into a quiet batch).

## Related
- Builder: `scripts/build_dipole.py` (dipole, zero-LLM)
- Block-content ground truth: `building-blocks/vba-blocks/dipole-build.md`
- New-topology primitives/operation examples: `building-blocks/vba-knowledge/`
- Visible block-by-block demo: `recipes/build/demo-recording-mode.md`
- Hard-timing SOP: `foundations/cst-simulation-sop.md` \u00a7B.1
- CST behavior traps (GUI not refreshing, stale read-after-write): `driving/cst-operation-notes.md`
