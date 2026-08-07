# Stage 01 · Literature — Extract reproduction spec from paper

**Goal**: Analyze the paper before simulation and produce a compact `01_paper_spec.md` that
explains the scientific argument and gives downstream stages an executable, traceable build
contract without re-reading the PDF.

## Inputs
- Target PDF at `target_paper/<paper>.pdf`
- Any pre-extracted text scratch at `target_paper/_scratch_*.txt` (use if available; else run `references_cases/_tools/pdf_extract.py <pdf> text <start> <end>`)

## What to extract

Extract the reproduction-relevant scientific story as well as the implementation facts:

0. **Research question and claim map**
   - What problem does the paper solve, what mechanism is proposed, and what improvement is
     claimed against which baseline?
   - Map every declared target ID to the paper section/figure/table that supports it.
   - Separate simulation, bench measurement, phantom MRI, in-vivo, and author interpretation.
     Do not present a simulated claim as experimentally validated.

1. **Physical setup**
   - Frequency (MHz), field strength (T)
   - **Excitation / characterization model** — DO NOT assume a driven single port. Classify:
     - `driven-port` — the device is fed (dipole, birdcage, loop): record feed type, port impedance, port count.
     - `passive-structure-with-external-coil` — the device has NO port of its own (metasurface, high-permittivity pad, passive resonator): it's characterized by its EFFECT on a separate driving coil's field → record the driving coil too, and that evaluation is with-vs-without the structure.
   - Coil / antenna geometry: dimensions, material, (feed type + port impedance IF driven-port)
   - Phantom / body model: shape, size, ε, σ (or dispersion source)
   - Distance from coil to phantom

2. **Numerical setup** (as stated in paper)
   - Solver (FDTD / FEM / ...), the paper's SW (SEMCAD / HFSS / CST) — we always translate to CST
   - Mesh / grid, boundaries, symmetries (if any)
   - Normalization (usually 1 W accepted)

3. **Evaluation metrics**
   - Primary: B1+, 10g SAR, SNR, S-parameters, ratio B1+/√SARmax, etc
   - Secondary: coupling, efficiency, radiation pattern
   - ROI (region-of-interest) definitions

4. **Paper type** (determines the Stage 03 shape — DO NOT default to "sweep")
   - `optimization-sweep` — paper varies parameter(s) and picks an optimum by a figure of merit (e.g. Fractionated Dipole: length + lumped sweeps → B1+/√SARmax optimum).
   - `single-design-demo` — paper presents ONE design and characterizes it (no sweep); Stage 03 becomes a single characterization run, not a loop.
   - `comparison` — paper compares a few discrete designs (e.g. structure A vs B vs none); Stage 03 runs each and compares, no continuous sweep.
   - This field drives whether Stage 03 loops, and what its metric criterion is.

5. **Parameter sweep space** (ONLY if `paper_type: optimization-sweep`)
   - List every dimension: parameter name, values, units, expected count of solves
   - Mark which sweeps are "primary" (main claim) vs "secondary"
   - **Metric criterion**: the EXACT figure of merit the paper optimizes (e.g. `B1+/sqrt(SARmax) at 10cm depth`). Record it verbatim from the paper — this is paper-specific, the framework has NO default.

6. **Expected results anchors** (from paper's Table/Figure)
   - Enough numbers to know if our reproduction is right or off
   - Cite paper's figure numbers when quoting values
   - **Baseline anchor (for the Stage-02 verification gate)**: at least one order-of-magnitude number for the canonical/reference config so Stage 02 can be sanity-checked before any sweep runs.

7. **Out of scope** (be honest)
   - E.g. in-vivo measurements, VNA experiments, license-restricted voxel models
   - What we will NOT reproduce and why

8. **Paper-to-CST traceability and ambiguity**
   - For every geometry/material/excitation/solver/normalization/ROI field, cite a page,
     section, figure, table, or supplement location.
   - Label each value `reported`, `derived`, `digitized`, `assumed`, or `unavailable`.
   - Carry every material assumption into the Stage 99 sensitivity audit.
   - Explain semantic translations where CST represents the physics differently.

## Method

- Record the PDF path and SHA-256, requested targets, exclusions, environment, unresolved
  assumptions, and predeclared numeric/trend/qualitative acceptance rules in this stage.
- Read the whole PDF (pdf_extract → text files at
  `target_paper/_scratch_<paper>_p<X>-<Y>.txt`).
- If PDF has figures with numeric anchors we care about, transcribe them
- Do NOT copy the abstract wholesale — extract the reproduction contract

## Handoff — write `stages/01_paper_spec.md`

Template:
```markdown
---
stage_id: 01_literature
status: passed
project: <project_id>
inputs:
  - target_paper/<paper>.pdf
outputs:
  - stages/01_paper_spec.md
stats:
  paper_freq_mhz: <f>
  paper_field_T: <B0>
  paper_type: <optimization-sweep | single-design-demo | comparison>   # drives Stage 03 shape
  excitation_model: <driven-port | passive-structure-with-external-coil>
  metric_criterion: "<verbatim FoM from paper, or 'characterization only'>"   # NO framework default
  requires_sar: <true|false>            # if true → Stage 02/03 solver MUST be TD hexahedral
  sweep_dims: <n>                       # 0 if not optimization-sweep
  total_solves_planned: <N>
  requires_voxel_body: <true|false>
  acceptance_level: <exact | engineering-equivalent | qualitative>
source_sha256: <sha256>
---

# Paper spec: <title>

## Paper analysis brief
- Research question: ...
- Proposed mechanism/design: ...
- Main claim against baseline: ...
- Evidence offered: simulation / bench / imaging / in-vivo

## Claim-to-target map
| Target ID | Paper claim | Source location | Evidence type | Reproduction metric |
| --- | --- | --- | --- | --- |
| T1 | ... | Fig. X / p. Y | simulation | ... |

## Reproduction protocol
- Source identity/hash and environment: ...
- In-scope targets and explicit exclusions: ...
- Predeclared acceptance rules: ...
- Blocking/material/minor unknowns and resolution plans: ...

## Physical setup
(bullets)

## Numerical translation to CST (our plan)
(bullets — this is the SIM plan for stage 02+)

## Parameter sweep space
| Dim | Param | Values | Unit | Solves | Priority |
|-----|-------|--------|------|--------|----------|
| ... | ...   | ...    | ...  | ...    | primary  |

## Evaluation metrics
- Primary: ...
- Secondary: ...
- ROI: ...

## Expected result anchors (from paper)
- Fig X: B1+ peak = ... µT/√W at depth 10 cm
- Table Y: coupling S12 = ... dB
- (Include enough to detect if reproduction is wildly off)

## Out of scope
- ...

## Paper-to-CST traceability matrix
| Item | Paper value | CST value/expression | Provenance | Source | Risk |
| --- | --- | --- | --- | --- | --- |
| Frequency | ... | ... | reported | Methods p. X | low |

## Ambiguities and planned sensitivity checks
| Assumption ID | Chosen value | Alternatives | Expected impact | Stage 99 check |
| --- | --- | --- | --- | --- |
| A1 | ... | ... | ... | ... |

## Downstream needs
- Stage 02 builds baseline at length = <default>, at f = <freq>
- Stage 03 sweeps <primary dim> first
```

## Return value to main loop

3–5 lines only. Example:
```
Paper: Fractionated Dipole @ 7T (298 MHz).
Sweep space: 9 lengths × 15 lumped values, primary = length sweep first.
Metrics: B1+ / 10g SAR / ratio; ROI = 10 cm depth in phantom.
Out of scope: 8-elem array in vivo prostate imaging.
Full spec at stages/01_paper_spec.md.
```

## Common pitfalls
- Don't paste PDF paragraphs into the artifact — synthesize
- Don't invent numbers not in the paper; if unclear, mark `TBD` and ask user in return value
- Do NOT include the full 3–4 page methods section verbatim; a well-structured 60-line spec is enough
- Do not reduce “paper analysis” to a parameter list. The research question, baseline,
  mechanism, evidence type, and claim-to-target map are required demo content.
