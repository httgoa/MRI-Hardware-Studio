# Data Prep Complete Case Router

Use this router when the user asks for data-prep complete-case records.

## Available Modules

- Dipole module D1:
  `recipes/data-prep/complete-case(D1)/data-prep-complete-case-dipole.md`
- Fractionated dipole D1 pilot SOP:
  `recipes/data-prep/complete-case(D1)/data-prep-complete-case-fd-sop.md`
- Validated record to few-shot card compiler:
  `recipes/data-prep/learning-cards.md`

## Routing

For regular dipole, direct-port dipole, SAR HDF5 export failures, or the current
complete-case matrix/template bundle, read the D1 dipole module first.

For `fractionated_dipole`, `FD_*` case ids, or any request to start an FD
complete case, read the D1 dipole module and then immediately read the
FD-specific SOP. `FD_case_matrix.csv` is the expert-reviewed authority for FD
parameters. Do not route FD rows to the regular-dipole batch runner or to
`live_build_case`; FD requires its own build entry point or sibling script.

The D1 module owns its colocated inputs:

```text
recipes/data-prep/complete-case(D1)/RD_case_matrix.csv
recipes/data-prep/complete-case(D1)/FD_case_matrix.csv
recipes/data-prep/complete-case(D1)/data-prep-complete-case-fd-sop.md
recipes/data-prep/complete-case(D1)/record_template_v1.json
```

It also incorporates the project SOP at:

```text
notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md
```

For D1, module-specific SAR export rules, phantom subvolume, record fields, and
case-matrix policy override older generic defaults.
