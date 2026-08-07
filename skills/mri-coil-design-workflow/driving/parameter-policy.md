# Parameter Policy (MRI)

Use when the user omits inputs or asks for defaults. Physics conventions: `mri-physics.md`.

## Ask Once for Critical Inputs

Ask a compact question only when a missing value changes the simulation meaning. If several are missing, present a defaults card instead of a question sequence.

| Input | Why it matters |
| --- | --- |
| coil / case type | birdcage vs surface vs dipole vs array need different setup |
| field strength / target frequency | drives Larmor freq, geometry, solver range, monitors |
| project source | new-build vs inspect-and-edit an existing `.cst` |
| primary objective | S11/resonance, B1+ homogeneity, SAR, or efficiency imply different outputs |
| execution intent | 3D EM solves are slow / license-bound — run or plan only? |

If the user says "directly run", "use defaults", "just go with defaults for now", or similar → use defaults and record them in the report.

## Defaultable Inputs

| Input | Default |
| --- | --- |
| units | `mm`, `MHz`, `ns` (MRI is MHz-scale, NOT GHz) |
| background | vacuum/air |
| conductor | Copper (CST library) |
| tissue | phantom material from the project if present; else a lossy tissue model |
| boundary | expanded open |  <!-- API value; NOT the GUI label "open (add space)" -->

| solver | HF Frequency Domain (narrowband high-Q loaded coil); HF Eigenmode for mode-finding |
| frequency range | `0.9*f0` to `1.1*f0` (coils are high-Q, narrower than antennas) |
| mesh | adaptive; refine at feeds, gaps, conductor edges, thin dielectrics |
| monitors | H-field (for B1+) and power-loss (for SAR) at f0; S-parameters over the sweep |
| outputs | resonance + S11, B1+ field 2D profiles + 1D line profiles + homogeneity CV, SAR if a lossy phantom exists |
| run directory | auto-named `results/<task>_<project>_<id>/` |

State defaulted values in the report.

## Derived Inputs

- Larmor frequency: `f_MHz = 42.577 * B0_T` (¹H). See `mri-physics.md` for other nuclei/fields.
- Tuning direction: resonance `f ∝ 1/√(LC)` → raise C to lower f, lower C to raise f.
- B1+ 1D profile axes/positions: mirror the project's existing template curves when present (e.g. `Tables\1D Results\...(Y)`), else default to lines through the phantom center along Y and Z.
- Homogeneity ROI: a stated box inside the phantom core; report the box with the CV.

## Existing Project Inputs

When a `.cst` exists, inspect before asking (run `probe_project.py`). Read from the probe summary:
- project identity + solver type
- parameters (names + expressions)
- nav tree: fields, monitors, S-parameters, B1+/SAR templates
- whether circuit co-sim `[AC*]` fields already exist

Ask the user only for genuinely ambiguous choices (which parameter to sweep, which result is the objective).

## Defaults Card Template

Present before an expensive solve (or include in the final report if the user already said run/defaults):

```text
I will run this MRI CST setup unless you change it:

Coil/case:
Project (source → working copy):
Field / frequency:
Tissue / phantom:
Solver:
Boundary:
Monitors:
Pipeline stages:
Outputs (2D + 1D + metrics):
Run mode:
Results subfolder:
```
