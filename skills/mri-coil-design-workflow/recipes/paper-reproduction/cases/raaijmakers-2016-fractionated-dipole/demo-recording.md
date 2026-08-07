# Fractionated-dipole paper reproduction demo / recording

Use this recipe to record a visible, step-by-step CST reproduction of Raaijmakers et al.,
*The Fractionated Dipole Antenna - A New Antenna for Body Imaging at 7 Tesla*.
It layers presentation and pacing over `reproduction.md`; the physics,
normalization, sweeps, and final figures remain unchanged.

The demo is a paper-reproduction narrative, not only a CST execution recording. It must show
the paper analysis and predeclared reproduction protocol before modeling, then the validation
audit and scientific report after the figures. Use `paper-brief.md` as the
verified literature input for this specialized fast route.

Also obey `../../../build/demo-recording-mode.md`, `../../../../driving/artifact-pipeline.md`,
and `../../../../driving/cst-operation-notes.md`. Run on the main thread only.

## Recording contract

- Generate and lint every `.bas` before the recording starts. Do not show code generation.
- Start each topology from a fresh empty MWS project and replay one history block per
  `cst_add_to_history_tool` call. Do not use `batch_quiet` on camera.
- Show every modeling operation and run the complete Fig. 3 and Fig. 4 case lists from this
  demo project. Do not reuse prior reproduction CSV/HDF5 data as demo evidence.
- Before CST mutation, show `01_paper_spec.md`: source identity, research question,
  claim map, baseline, paper-to-CST traceability, case matrix, assumptions, exclusions, and
  acceptance rules. “We will reproduce Fig. 3/4” alone is not paper analysis.
- After post-processing, show `99_final_report.md`: quantitative
  scorecard, robustness/sensitivity status, discrepancy ledger, conclusion, and evidence index.
- After a milestone, save, announce it, ask the user whether to inspect or continue, and
  **end the turn / wait**. Never cross a pause point in the same turn.
- If `request_user_input` is available, offer: `Pause and inspect`, `Continue`, and
  `Continue without further optional pauses`. Otherwise ask the same question in the final
  response. Required topology/result gates are never suppressed.
- On a failed block, stop the visible sequence. Repair off-camera with L2/L3 and resume from
  that block; do not rebuild completed history.

## Outputs and isolation

Use a dedicated run folder, never the validated production folder:

```text
<outroot>/paper_fractionated_dipole_demo/
  stages/
  artifacts/demo/plain/
  artifacts/demo/segmented/
  log/
  output/
  paper_fractionated_dipole_demo_plain.cst
  paper_fractionated_dipole_demo_segmented.cst
```

Generate the recording manifests offline:

```powershell
python -B ../../../../scripts/paper_fractionated_dipole.py --outroot <outroot> --project paper_fractionated_dipole_demo --variant plain --segments-per-arm 1 --presentation-mode recording
python -B ../../../../scripts/paper_fractionated_dipole.py --outroot <outroot> --project paper_fractionated_dipole_demo --variant segmented --segments-per-arm 3 --presentation-mode recording
python -B ../../../../scripts/lint_vba.py --fix <outroot>/paper_fractionated_dipole_demo/artifacts/demo
```

The recording manifest adds three fields per CST block:

- `reset_view`: execute `ResetViewToStructure` after the block.
- `visible`: expected CST foreground content for the milestone announcement.
- `milestone_after`: required pause identifier, or `null`. Modeling blocks do not pause;
  the solver configuration block carries the single pre-solve pause for each figure.

## Fast-start and PDF routing contract

This recipe is self-contained for the target PDF. Use the verified paper-specific brief above;
do **not** invoke a generic PDF skill or
perform PDF text extraction, page rendering, Poppler discovery, package installation, or
dependency probing during startup. Those actions are not preflight requirements and must not
delay the recording gate.

The only permitted PDF operation before visible modeling is a filesystem existence check for
the exact target path. Paper-image extraction happens only after a current-demo Fig. 3 or Fig. 4
has been generated: `paper_fractionated_dipole_post.py paper-compare` uses `pypdf` to extract
the embedded image from PDF page 4 or 5. If that final comparison command later reports a real
PDF extraction error, diagnose it at that stage without invalidating completed CST evidence.

For the canonical prompt requesting a formal demo from a blank CST project, complete startup
in this strict order:

1. Read this recipe plus the required CST operation/artifact rules.
2. Complete Stage 01 from the verified brief: hash the target PDF, freeze scope/exclusions and
   acceptance rules, then write and show `stages/01_paper_spec.md` with the T1–T3 claim map.
3. Generate the plain and segmented recording manifests and run
   L0 lint. Show the defaults/case-matrix review card.
4. Detect CST and require exactly one visible Design Environment.
5. Announce `preflight_ready`, ask the user to close the old project while keeping CST running,
   then end the turn and wait. Do not create the blank MWS project before that confirmation.

Do not insert unrelated environment scans or document-tool checks into this sequence.

## Preflight gate — wait for the user

1. Confirm the paper PDF exists and the demo output folder is writable. Prior reproduction
   results are not an input requirement.
2. Detect CST and require one visible Design Environment.
3. Ask the user to close the old project while keeping CST running.
4. Wait until the user says it is closed and recording/rehearsal is ready.
5. Reconnect to the CST PID if closing the project dropped the MCP session.
6. Create a new MWS project, save it immediately under the demo folder, and verify the
   connection is fresh enough for foreground repaint.

Do not start visible modeling before this gate passes.

## Camera and view policy

The artifact order intentionally creates the antenna before the 500 mm phantom.
This makes close-up fitting useful instead of shrinking the antenna to a few pixels.

1. Reset after each conductor pair. The plain arms or segmented pieces should fill the view.
2. Reset after the feed port so the center gap remains legible.
3. For the segmented topology, reset after each completed bridge pair, not after each single
   bridge. This avoids distracting camera jumps.
4. Create the transparent phantom only after the antenna, port, and bridges are visible.
   Reset once to show the full antenna/phantom relationship.
5. Do not reset for parameters, material definitions, monitors, or solver settings; they
   change the tree but produce no useful geometry change.
6. If a verified reset does not repaint, save and stop. Ask the user to close/reopen the demo
   project; do not continue recording with a stale viewport.

For every manifest block:

1. Read its `.bas` as UTF-8 through `cst_run_python_tool` and take the code only from
   `structuredContent.result.vba_code`. Do not pass the textual output of a shell/terminal
   tool directly to `cst_add_to_history_tool`: that output may be prefixed with transport
   status lines such as `Exit code:`, `Wall time:`, and `Output:`, which CST parses as VBA
   and rejects with `Expecting 'All | Sub'`.
   Before the history call, require a non-empty payload, reject those three prefixes, and
   report the first line plus SHA-256 digest. This is the recording transport gate.
2. Call `cst_add_to_history_tool(title, vba_code)` once.
3. Rebuild and save.
4. If `reset_view=true`, call `cst_execute_vba_tool("ResetViewToStructure")`.
5. Verify the expected solid/port/bridge count and report `visible`.
6. If `milestone_after` is non-null, execute the pause contract. After the user starts a
   figure sweep, do not pause again until that figure's complete reproduction and paper-image
   comparison have been written.

Verified structured-read pattern:

```python
from hashlib import sha256
from pathlib import Path

code = Path(BAS_PATH).read_text(encoding="utf-8")
bad = ("Exit code:", "Wall time:", "Output:")
if not code.strip() or code.lstrip().startswith(bad):
    raise RuntimeError("invalid demo VBA transport payload")
result = {
    "vba_code": code,
    "first_line": code.splitlines()[0],
    "sha256": sha256(code.encode("utf-8")).hexdigest(),
}
```

Pass only `structuredContent.result.vba_code` from that tool result into the single
`cst_add_to_history_tool` call. The digest/first-line check happens before any visible CST
mutation, so a transport regression stops off-camera instead of interrupting the recording.

## Storyboard and required milestones

| Phase | Visible work | Required pause |
| --- | --- | --- |
| 0. Paper analysis and protocol | Show source identity, research question, claim map, scope, assumptions, case matrix, metrics, normalization, and acceptance rules | `preflight_ready` |
| 1. Plain model | Parameters/setup/material, continuous arms, feed, phantom, monitors, TD solver | `fig3_pre_solve` |
| 2. Complete Fig. 3 | Verify the current-run 300 mm baseline first, then run all nine lengths and generate the paper-original comparison | `fig3_outputs_ready` |
| 3. Segmented model | Fresh project, six PEC segments, feed, four RLC bridges, phantom, monitors, solver | `fig4_pre_solve` |
| 4. Complete Fig. 4 | Run all 15 loaded cases plus the current-run plain baseline and generate the paper-original comparison | `fig4_outputs_ready` |
| 5. Validation and final report | Show scorecard, discrepancies, confidence, limitations, evidence inventory, and final verdict | `report_ready` |

Do not pause after geometry or phantom creation. Keep the modeling sequence flowing and pause
only after solver configuration, immediately before starting each complete sweep. The 300 mm
case remains the blocking baseline check inside the Fig. 3 phase. At
output milestones, show the newly generated comparison image and wait for inspection.

## Live solve scope

Required recording scope is the literal complete case list in
`reproduction.md`: nine Fig. 3 lengths and fifteen Fig. 4 loads. The plain
300 mm baseline used at `Z=0` must come from the current demo run. After each figure, call the
paper-comparison command in `paper_fractionated_dipole_post.py`; compare against the PDF page,
not against prior reproduction results.

```powershell
python -B ../../../../scripts/paper_fractionated_dipole_post.py paper-compare --figure <3|4> --paper-pdf "<target.pdf>" --reproduction "<current-demo-figure.png>" --output "<current-demo-comparison.png>"
```

## Milestone announcement

Use the generic format plus the paper context:

```text
Milestone N/6 complete: <name>
   - Paper case: <plain length / segmented loading>
   - Completed: <operation and key parameter>
   - Now visible in CST: <manifest visible text or selected result>
   - Evidence: <demo path>
```

Then wait for the user. Do not append the next operation.

## Rehearsal acceptance checks

- Both recording manifests lint with zero errors.
- Stage 01 is present and shown before the first CST mutation; the source hash, claim map,
  acceptance rules, traceability matrix, assumptions, and exclusions are non-empty.
- Plain and segmented projects start from empty projects and save to isolated paths.
- Every conductor pair, feed port, and bridge pair becomes visible in sequence.
- Reset points make the antenna legible before the phantom is added.
- Each topology stops exactly once before its first solver run.
- After solver start, the next pause occurs only after the corresponding complete figure and
  paper-original comparison exist.
- All nine Fig. 3 and all fifteen Fig. 4 loaded cases finish with selectable H/loss results.
- Every Fig. 3 SAR profile covers `Yhalf=160 mm` through 300 mm and
  `Yhalf=L_total/2+15 mm` above 300 mm on both sides: +/-160 mm through 300 mm,
  then +/-190, +/-215, and +/-240 mm for 350,
  400, and 450 mm. Fig. 4 uses +/-160 mm. A shorter HDF5/CSV range blocks
  figure generation even when accepted power and SARmax are valid.
- Final Fig. 3/4 images are generated from the current demo summaries and shown together with
  the paper originals extracted directly from the target PDF.
- Fig. 4 panels (a) and (d) each show exactly six curves and six legend entries:
  1 pF, 5 pF, plain, 50 nH, 100 nH, and 150 nH. Missing entries block the output milestone.
- Stage 99 audits every target against the predeclared rule, records discrepancies, and indexes
  all current-run evidence.
- No solver remains running and no `.lok` is left in the demo folder.
