# Fractionated Dipole Paper Brief — Demo Literature Input

Use this verified, paper-specific brief to make Stage 01 visible in the Raaijmakers Fig. 3/4
demo without performing generic PDF dependency discovery on camera. It does not replace the
target PDF: Stage 01 must hash the PDF, final comparisons must extract images from that same
file, and any source mismatch blocks the demo.

## Scientific question and proposed mechanism

At 7 T body MRI (298 MHz), the RF wavelength in tissue is short enough that a conventional
dipole's current distribution and local electric fields constrain transmit efficiency and SAR.
The paper studies whether shortening the conductor and then fractionating it with distributed
reactive loading can preserve useful deep `B1+` while improving the `B1+/sqrt(SARmax)` tradeoff.

## Claims targeted by this demo

| ID | Paper evidence | Claim tested | Demo metric |
| --- | --- | --- | --- |
| T1 | Fig. 3 | Increasing plain-dipole length improves deep transmit performance until the useful gain plateaus near 300 mm | Depth `B1+`, peak 10 g SAR, and `B1+/sqrt(SARmax)` across nine lengths |
| T2 | Fig. 4 | Intersegment reactance reshapes current/SAR; an inductive region near 75–100 nH gives the favorable FoM and excessive inductance causes collapse | Full reactance sweep, depth profiles, longitudinal SAR, and FoM |
| T3 | Fig. 3/4 methods and captions | Trends must be compared at common accepted power, not equal incident stimulus | Per-case `Paccepted`, `B1+ / sqrt(Paccepted)`, and `SAR / Paccepted` |

## Paper-to-CST contract used by the demo

- Frequency: 298 MHz (7 T proton MRI).
- Driven-port, single-dipole characterization above a homogeneous phantom.
- Plain geometry: 10 mm PEC strip, 2 mm feed gap, 20 mm above phantom; nine total lengths
  from 50 to 450 mm.
- Segmented geometry: 300 mm total length, three PEC segments per arm, two gaps per arm, four
  passive series-RLC bridges; the feed remains the only port.
- Phantom translation: 500 mm cube, relative permittivity 34, conductivity 0.4 S/m,
  density 1000 kg/m3.
- Solver translation: CST HF Time Domain, hexahedral mesh, H-field and power-loss monitors;
  native IEEE 10 g SAR.
- Normalization: measure accepted power for every case; never assume the stimulus equals 1 W
  accepted for severely mismatched antennas.
- Longitudinal export ROI: use +/-160 mm through `L_total=300 mm`; above 300 mm
  retain 15 mm of phantom beyond each conductor end, giving +/-190, +/-215, and
  +/-240 mm at 350, 400, and 450 mm. This is an evidence-coverage rule, not a
  plotting preference.

## Expected anchors and acceptance framing

- T1 trend anchor: deep-field/FoM gains flatten near 300 mm; agreement is primarily trend and
  optimum-region agreement unless a value is explicitly digitized from the paper.
- T2 optimum-region anchor: inductive loading near 75–100 nH; collapse near 150 nH.
- B1+ must be on the order of microtesla per square-root watt and SAR must be finite with a
  physically plausible central/localized maximum before the full sweep is accepted.
- Finite SAR and a valid SARmax are insufficient if the longitudinal HDF5/CSV is
  clipped. Every case must cover the declared Y ROI before a Fig. 3/4 panel may
  be generated.
- The demo's numeric tolerances must be declared in `01_paper_spec.md`; any value visually
  digitized from the PDF must carry a digitization uncertainty.

## Scope boundary

This demo reproduces paper Figs. 3 and 4 only. It does not claim reproduction of matching
networks, full antenna arrays, experimental bench measurements, in-vivo imaging, or other
paper figures. Those remain explicit exclusions in Stage 01 and the final report.

## Required Stage 01 presentation

Before CST opens, show: the research question, T1–T3 claim map, the paper-to-CST translation,
the case matrix (9 plain + 15 loaded + current-run plain baseline), accepted-power
normalization, expected trend anchors, assumptions, and exclusions.
