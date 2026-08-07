# Repro 06 — Fractionated Dipole @ 7T (Raaijmakers 2016, MRM)

**Source**: distilled from the `mri-coil-agent-pack-716-psh` FD_Optimize case (M2+M3, run successfully 2026-07-15/16). This is **someone else's already-successful reproduction**, which we treat as a second ground truth; numerical anchors in `results/paper_fractionated_dipole/stages/00_reference_reproduction.md`.

**Paper**: Raaijmakers et al., MRM 75:1366-1374 (2016). 298 MHz, 7T body imaging fractionated dipole, two-stage optimization (length -> inter-segment lumped elements), FoM = B1+/sqrt(SARmax).

## Reproduction scope and method

- **Completed through M3** (length sweep Fig.3 + inter-segment element sweep Fig.4); M4 (meander+matching+SSAD comparison)/M5 not done.
- **Solver = HF Time Domain hexahedral** (native 10g SAR only supports hex; FD Tet can't produce SAR). Frequency 298 MHz.
- **Geometry**: a thin PEC dipole (10mm wide, 2mm center feed gap), suspended Z=+20mm above the top face of a 0.5m cubic phantom (eps=34, sigma=0.4). Long axis = Y. Depth d = -Z.
- **Inter-segment elements**: `LumpedElement` (RLCSerial) in series across each gap, 2 per leg, 4 total across the whole model + 1 feed DiscretePort (the inter-segment elements are passive components, they don't create ports).
- **FoM normalization iron rule**: normalize everything to 1W **accepted** power (measure P_acc per case); the antenna is linear, so no per-case matching is needed (length/element optimization is decoupled from matching). Never assume 1W excitation = 1W accepted (a bare dipole's P_acc varies by 2000x across cases).

## Results alignment (core physics fully reproduced)

- **Length**: optimal pure-transmit length per depth ~10/17.5/22.5cm; FoM@10cm plateaus ~300mm -> settled on 30cm.
- **Inter-segment inductance**: flattening the current reduces SAR, FoM peaks at 75-100nH; Z>=281 Ohm (150nH) gives two half-wavelengths -> a double-peaked SAR -> FoM collapses.
- **Inter-segment capacitance**: shortens the effective electrical length -> raises shallow B1+, raises SAR.
- **Chosen design**: 30cm + 4x75nH (matches the paper's meander-estimated inductance).

## Case-specific pitfalls (general pitfalls already in mcp-pitfalls.md #18-26 + cst-simulation-sop.md)

1. **SAR `scale accepted` silently fails on severe mismatch** -> use `no rescale` and manually divide by P_acc (once produced a paper-contradicting result, with the FoM optimum landing on the shortest antenna).
2. **Native 10g SAR only supports hexahedral meshes** -> SAR requires TD.
3. **SAR 3D field headless export is fragile**: the simple pipeline (M2) exported automatically; the complex pipeline (M3, many reopens/aborts) hit instability -> fall back to the GUI or use `export_native_sar.py`'s two-hop method. **The E-field proxy `0.5*sigma*|E|^2/rho` was falsified** (peaks at the ends, opposite to the true SAR).
4. **TD's first solve often doesn't produce the 3D volume field** -> re-solve if missing. **H-field export must happen before `SAR.Create`** (otherwise "not available for current view").
5. **SteadyStateLimit -30dB** speeds up high-Q mismatched points (must be consistent across all cases in a sweep).
6. **Port topology**: the inter-segment elements are passive `LumpedElement`s, the whole model has only 1 feed port (the original outline's "element ports 2-5" was a typo).
7. **Session stability**: an independently-launched script self-starting a DE hits "Simulation already running" / orphaned locks -> switched to MCP-managed `de`, single-point sequential driving; batch abort/close can cascade and crash the whole DE.

## Reproduction asset locations

- Numerical anchors: read the target paper plus the latest stage artifacts under the selected output root; historical results are evidence only, not a runtime dependency.
- Paper-specific recipe: `recipes/paper-reproduction/cases/raaijmakers-2016-fractionated-dipole/reproduction.md`.
- Deterministic generator: `scripts/paper_fractionated_dipole.py`. It replaces the stale dependency on `results/paper_fractionated_dipole/scripts/` and emits plain and segmented manifests beneath the selected output root.
- General scripts (skill): `scripts/export_native_sar.py`, `compute_b1plus.py`
- Original pack files (read-only reference, do not modify): `mri-coil-agent-pack-716-psh/cases/FD_Optimize/` (contains the full M2/M3 reports + result figures)

## Relationship to our framework

The pack was run **inline sequentially within a single session**; when we re-run it ourselves using the multi-stage subagent framework, Stage 03's `paper_type = optimization-sweep`, `metric_criterion = "B1+/sqrt(SARmax) at 10cm"`, `requires_sar = true` (-> TD-hex). Trial 3+3 = length{15,30,45}cm + inductance{10,75,150}nH. After running, point-for-point alignment against `00_reference_reproduction.md` confirms the framework works end-to-end.
