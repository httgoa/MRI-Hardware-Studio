# Result Validation

Use before claiming a CST run succeeded. Physics conventions live in `mri-physics.md`.

## Evidence requirements

A run is validated only when at least one concrete evidence source exists:

- a saved working `.cst` project path
- result-tree entries from `cst_list_results_tool`
- a readable 1D result from `cst_read_1d_result_tool`
- an exported file (Touchstone/CSV/etc.) or a solver log showing completion

If the solver "returned" but no result evidence is available, report `needs_validation` — do not claim success.

## S-parameters

- Confirm the result item exists (e.g. `1D Results\S-Parameters\S1,1`).
- Data may be complex. Compute dB as `20*log10(abs(S11))`. Never label raw complex magnitude as dB.
- State the frequency unit, and the interpolation method if evaluating at a target frequency.
- For pass/fail, state the threshold explicitly, e.g. `S11 <= -10 dB at f0`.
- Evidence is not the same as meeting the tuning objective. If the requested
  threshold is not met at the target frequency, report the S-parameter result as
  parsed but the tuning objective as failed/partial; do not mark the whole run
  `validated` unless the requested thresholds are met or the user explicitly
  accepted a relaxed threshold.

## Resonance frequency (when applicable)

- Resonance = frequency of minimum S11 (or an eigenmode result entry).
- Report it with units; do not eyeball it from a plot without the underlying data.

## B1+ field

- Confirm the `2D/3D Results\B1+ and B1-\B1+ (...) [AC*]` field exists (needs circuit co-sim, not just 3D).
- B1+ is the circular-polarized transmit component, NOT |H|. Do not present |H|/|B| magnitude as B1+.
- Report magnitude in µT (CST export is Tesla → ×1e6). State the plane/ROI.
- Homogeneity: `CV = std/mean × 100%` over a stated ROI. State the ROI box; a coarse export grid distorts CV — flag export resolution as a limitation when relevant.

## SAR

- Confirm the SAR result exists and a power-loss monitor + lossy tissue were present.
- Always state the averaging mass (10 g vs 1 g) and units (W/kg).
- Do not infer SAR from field magnitude alone.

## Status values

| Status | Meaning |
| --- | --- |
| `validated` | Solver ran, requested result evidence was found and parsed, and requested objective thresholds were met |
| `needs_validation` | Project/solver ran but result evidence is missing or incomplete |
| `blocked` | CST/MCP/license/input/project issue prevented meaningful execution |
| `plan_only` | User requested planning without execution |
| `partial` | Some outputs validated, others failed or were not generated |

## Minimum report

- working project path (and source path if copied)
- MCP tools used, in order
- result-tree entries / evidence files
- validation status
- issues and recommended next action
