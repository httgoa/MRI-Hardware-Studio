# Fractionated dipole - complete Fig. 3 and Fig. 4 reproduction

Use this case recipe for Raaijmakers et al., *The Fractionated Dipole Antenna - A New
Antenna for Body Imaging at 7 Tesla* (MRM 2016). Follow the paper-reproduction stages,
with the paper-specific rules below.

## Inputs and outputs

- Paper: `target_paper/The Fractionated Dipole Antenna A New Antenna forBody Imaging at 7 Tesla.pdf`
- Deterministic artifact generator: `../../../../scripts/paper_fractionated_dipole.py`
- Default project id: `paper_fractionated_dipole`
- Results root: use the user's explicit `outroot`; do not hardcode `results/`.

Generate both artifact sets before opening CST:

```powershell
python -B ../../../../scripts/paper_fractionated_dipole.py --outroot <outroot> --project paper_fractionated_dipole --variant plain --segments-per-arm 1
python -B ../../../../scripts/paper_fractionated_dipole.py --outroot <outroot> --project paper_fractionated_dipole --variant segmented --segments-per-arm 3
python -B ../../../../scripts/lint_vba.py --fix <outroot>/paper_fractionated_dipole/artifacts
```

Replay each manifest with `batch_execute.py` in `batch_quiet` mode. Use separate CST
projects for the plain and segmented topologies so topology changes never contaminate a
parameter-only sweep. The same emitted blocks are suitable for later `demo_stepwise` replay.
For a visible recording, use `demo-recording.md` and generate the
recording-specific fine-grained manifests; do not improvise camera steps from this production
recipe.

## Fixed model contract

- 298 MHz, HF Time Domain hexahedral, steady-state limit -30 dB.
- 500 mm cubic phantom, top at z=0, epsilon-r 34, conductivity 0.4 S/m, density 1000 kg/m3.
- PEC strip: 10 mm wide, 0.5 mm thick, y-directed, 20 mm above phantom.
- Center feed gap 2 mm, one 50-ohm coordinate-based discrete port.
- H-field and power-loss monitors at 0.298 GHz.
- Normalize B1+ by `1/sqrt(Paccepted)` and native IEEE 10g SAR by `1/Paccepted`.
  Never trust `scale accepted` for strongly mismatched cases.

## Stage 02 gate

Build the 300 mm plain project first. Require selectable H-field and power-loss results,
B1+ on the order of microtesla/sqrt(W), finite native 10g SAR, and a central SAR maximum.
Stop before sweeping if the gate fails.

## Fig. 3 - length sweep

Sweep `L_total` over 50, 100, 150, 200, 250, 300, 350, 400, 450 mm. This is a scalar
parameter update: use `StoreParameter`, rebuild, save, solve, and export; do not rebuild
the topology. For every case:

1. Export H-field before `SAR.Create`.
2. Create native IEEE 10g SAR with `no rescale`.
3. Export SAR in the fresh post-solve session with `export_native_sar.py`.
4. Read accepted power from the newest run id at 0.298 GHz.
5. Save H/SAR HDF5, depth B1+ CSV, longitudinal SAR CSV, and one summary row.

The H-field and SAR longitudinal export ROI is a fixed paper-reproduction
contract, not a caller-selected plotting window:

```text
Yhalf = 160 mm                         when L_total <= 300 mm
Yhalf = L_total/2 + 15 mm              when L_total > 300 mm
Y export range = [-Yhalf, +Yhalf]
```

Thus 50-300 mm dipoles use `[-160,+160]` mm; 350/400/450 mm use
`[-190,+190]`, `[-215,+215]`, and `[-240,+240]` mm. This retains lossy phantom
beyond both conductor ends for Fig. 3(d). **Never pass `L_total/2` as the
export half-span.** Call `paper_fractionated_dipole_live.export_case` with
`length_mm=L_total` and let the helper derive the ROI. The helper rejects any
explicit smaller ROI.

Produce all six panels. Panel (b) is relative to the 250 mm profile; panel (e) is
`B1+/sqrt(SARmax)` relative to 250 mm. Panels (c) and (f) normalize each depth curve to
its own maximum.

## Fig. 4 - intersegment sweep

Use 300 mm total length, three PEC segments per arm, two 2 mm gaps per arm, and four
passive `RLCSerial` bridges. A pure inductor is `L_seg>0, C_seg=0`; a pure capacitor is
`L_seg=0, C_seg>0`. Sweep:

- capacitors: 1, 2, 5, 10, 20, 50, 100, 500, 1000 pF;
- inductors: 10, 20, 50, 75, 100, 150 nH;
- add the plain 300 mm result at Z=0 as the normalization baseline.

All Fig. 4 H/SAR exports use the same longitudinal rule above; at 300 mm this
is exactly `[-160,+160]` mm.

Map the horizontal axis to reactance at 298 MHz: `Z=2*pi*f*L` for inductors and
`Z=-1/(2*pi*f*C)` for capacitors. Produce all six panels. Panels (a) and (d) may show the
paper's displayed subset (1 pF, 5 pF, plain, 50 nH, 100 nH, 150 nH); panels (b/c/e/f)
must use the full 16-point axis including the plain baseline.

## Required evidence

- Source hash and frozen acceptance rules, paper analysis/claim map, two `.cst` projects, both
  artifact manifests, L0/L1 reports, per-case HDF5/CSV files, sweep summaries, full six-panel
  Fig. 3 and Fig. 4 PNGs, and stage artifacts 01/02/03/04/99.
- Record retries and SAR export failures per case. Solver completion without selectable
  results is not success.
- Before accepting or plotting a case, verify the SAR HDF5/CSV Y coordinates
  cover `[-Yhalf,+Yhalf]` from the formula above. The paper-specific postprocessor
  treats shorter coverage as a blocking error; finite values and a correct SAR
  maximum do not waive this gate.
- Validate the Fig. 3 plateau near 300 mm at 10 cm depth and the Fig. 4 FoM optimum near
  75-100 nH with the collapse near 150 nH.
- Audit each predeclared target quantitatively when the paper provides a readable value and
  record digitization uncertainty otherwise in Stage 99.
