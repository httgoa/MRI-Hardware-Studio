# MRI Hardware Studio · Autonomous Dipole Workflow

Open `index.html` directly in Chrome or Edge. No build step or web server is required.

## Scope

This walkthrough presents the frozen `dipole_scratch` matched-reference case:

- 5 T-class MRI baseline simulated at a 210 MHz target frequency;
- 300 mm × 5 mm regular dipole above a homogeneous tissue phantom;
- parameterized construction from a blank CST MWS project;
- HF frequency-domain solve and inductive L-match (`Lt=88 nH`, `Lp=37 nH`);
- AC co-simulation and B1+ post-processing normalized to 1 W accepted power;
- quantitative metrics, spatial maps, line profiles, CSV data, and JSON statistics.

The page validates the autonomous matched-B1+ workflow. It does not claim native SAR validation or coil-design superiority.

## Presentation controls

1. Select **Explore the workflow**.
2. Reveal the evidence in each stage.
3. Select either result figure to open the full-resolution view.
4. Use **Reset** or press `R` before another presentation. Press `F` for fullscreen.

Direct links use `#stage-01-reveal` through `#stage-04-reveal`. The equivalent query form, such as `?stage=4&reveal=1`, is available for automated review.

Append `?reveal=all` to expand the complete evidence package for review or printing.
