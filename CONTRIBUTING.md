# Contributing to MRI Hardware Studio

Thank you for your interest in contributing! This guide explains how to add recipes, building blocks, or bug reports.

## Types of Contributions

### 1. Adding a New Recipe

Recipes are the primary way to extend MRI Hardware Studio's capabilities. A recipe must be:
- **Executable**: clear inputs, ordered steps, validation gates, and expected outputs
- **Tested**: verified on at least one real CST project before merging
- **Located** in the correct subdirectory under `skills/mri-coil-design-workflow/recipes/`

**Recipe directory structure:**

| Directory | Use for |
|---|---|
| `recipes/build/` | From-scratch modeling, geometry construction, demo workflows |
| `recipes/b1-sar/` | B1⁺ field analysis, SAR export, field post-processing |
| `recipes/inspect/` | Unknown project inspection, result tree parsing |
| `recipes/optimize/` | Parameter sweeps, FoM optimization, tuning loops |
| `recipes/data-prep/` | Training/dataset record generation |
| `recipes/paper-reproduction/` | Multi-stage paper reproduction pipelines |
| `recipes/reference-repro/` | Single-figure geometry reproduction, official component learning |

Use `recipes/_TEMPLATE.md` as the starting point.

### 2. Contributing VBA Building Blocks

VBA knowledge lives in `skills/mri-coil-design-workflow/building-blocks/`:

- **`vba-blocks/`**: Complete, verified VBA segments extracted from real projects. Include the source project name and date in a comment block at the top.
- **`vba-knowledge/`**: Tier-B few-shot knowledge units — focused on a single CST VBA primitive or operation (geometry, ports, mesh, solver, etc.). Each file covers one topic and includes 2–3 concrete examples.

### 3. Reporting Pitfalls

If you discover a reproducible failure mode:
1. Add it to the relevant file under `skills/mri-coil-design-workflow/pitfalls/`
2. Include: symptom, root cause, deterministic fix, and verification step
3. If it's a VBA error with a known fix pattern, add the `(error-signature → fix)` entry to `pitfalls/error-fixes.md`

### 4. Templates (Tier A)

Jinja2 `.vba.j2` templates in `skills/mri-coil-design-workflow/templates/` represent deterministic, parameter-only VBA generation. Contributing a template requires:
- Full parameter table with types, units, and defaults
- Validation that rendered output passes `scripts/lint_vba.py`
- At least one verified render example in a PR comment

## Pull Request Process

1. Fork the repository and create a feature branch: `git checkout -b recipe/my-new-coil-type`
2. Add your contribution following the guidelines above
3. Run the linter on any VBA you generate: `python skills/mri-coil-design-workflow/scripts/lint_vba.py --fix <path>`
4. Update `notes/README.md` if adding a reproduction log
5. Submit a pull request with a description of what was verified and on which CST version

## Code of Conduct

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions

Open a GitHub Issue with the tag `question` for anything not covered here.
