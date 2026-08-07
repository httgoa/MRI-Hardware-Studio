# CST HF Simulation Fundamentals (distilled from the official manual High Frequency Simulation 2024)

> Source: `Documentation/CST Studio Suite - High Frequency Simulation.pdf` (119 pages; close-read ch2 workflow + ch3 solver overview).
> Purpose: establish the "correct mental model for doing HF simulation in CST", used as a reference frame during reproduction. Compared against our dipole experience at the end.

---

## 1. Standard HF workflow (12 steps, common to all solvers)
The modeling flow is essentially the same; only the solver/boundary/monitor change per application:
1. Choose a Project Template (application domain → presets the solver/units/background material)
2. Set units (Home: Settings → Units)
3. Set the background material (Modeling: Materials → Background)
4. Build the structure (solid modeler, based on the ACIS kernel)
5. Set the frequency range (Simulation: Settings → Frequency) — **key, determines the mesh and signal bandwidth**
6. Define ports (Simulation: Sources and Loads)
7. Set boundaries + symmetry conditions (Simulation: Settings → Boundaries)
8. Set field monitors (Simulation: Monitors → Field Monitor)
9. (Optional) choose a sweep method
10. Start the solver (Simulation: Solver → Setup Solver → Start)
11. Analyze results (port modes, S-parameters, fields, farfield, result templates)
12. Iterate (parameterize → sweep → optimizer)

**Mental model**: geometry is simplified via the "background material" trick — any unfilled space automatically = the background material. Inside a coaxial cable, the outer conductor can be simplified to a PEC background, building only the dielectric + inner conductor. PEC can overlap a dielectric (PEC dominates), but two dielectrics cannot overlap.

---

## 2. Solver selection (ch3's core table, MRI-relevant rows in bold)
| Application | Recommended solver |
|---|---|
| Connectors/waveguides/transmission lines | Transient (time domain) |
| **Monopole/dipole/multipole antennas** | **Transient** |
| **Patch/conformal antennas** | **Transient or Frequency Domain** |
| Helical/spiral antennas | Transient / Integral Equation |
| Antenna arrays | Transient / FD (Domain Decomposition) |
| **Filters/strongly resonant devices** | **Frequency Domain (FD)** (time domain degrades for strong resonance) |
| Cavities/resonators/traveling-wave structures | **Eigenmode** |
| Planar structures (PCB/microstrip) | Multilayer / Transient |
| Electrically large / RCS | Integral Equation / Asymptotic |
| Periodic structures (non-zero phase shift) | FD or Eigenmode (time domain can only do zero phase shift) |

**Decision intuition**:
- Transient = most general-purpose, gets a broadband result in one simulation; a must for **weak resonance**, broadband, nonlinear, or diode-containing cases.
- FD = faster for **strong resonance/low frequency/filters** (a handful of frequency points + a broadband sweep suffice); but as the mesh grows it's slower and more memory-hungry than time domain. Beyond a few million tetrahedra, switch to time domain/IE.
- Eigenmode = solves the closed cavity's natural modes (frequency + Q), **no ports/monitors needed**. Useful for finding MRI birdcage modes.
- The two major methods cross-validate each other: use one for the primary simulation + optimization, the other for final verification.

---

## 3. Mesh — the primary source of result accuracy
- **Hexahedral**: the default for time domain/TLM; paired with PBA (Perfect Boundary Approximation) + TST (Thin Sheet Technique), so curved surfaces/thin sheets can be modeled accurately without an extremely dense mesh.
- **Tetrahedral**: the default for FD/Eigenmode; curved surfaces use curved elements (the curvature order auto-matches the solver order). The initial mesh is coarse-ish, **adaptive refinement is strongly recommended**.
- **Adaptive Mesh Refinement**:
  - Time domain: each pass runs the whole broadband sweep, convergence is judged by the max S-parameter deviation between adjacent passes (Delta S, default 2%).
  - FD: by default only refines at a **single frequency point**, then computes the broadband sweep on the fixed mesh → **that frequency point's location matters enormously**. For weak resonance choose the highest frequency; for **strong resonance/filters you must choose an in-passband frequency point** (otherwise energy is fully reflected at the port, and the mesh only refines near the port rather than internally).
  - Once converged, adaptivity can be turned off; the expert-system rules carry over to subsequent parameter sweeps/optimization → **refine once, reuse many times**.
- Solver order: FD defaults to 2nd order (fewer mesh elements, high accuracy); fine geometry like PCB/IC can use 1st order to save memory; electrically large smooth regions can use 3rd order or variable order.

---

## 4. Port types (determine S-parameter accuracy)
1. **Discrete edge port**: a lumped element (internal resistance + current source in parallel) + two PEC leads. Most flexible, accurate enough when size ≤ λ/10. Has a fringing effect.
2. **Discrete face port**: same as above but uses a face; lower self-inductance, produces less discontinuity than an edge port when connecting to microstrip/stripline.
3. **Waveguide port**: a 2D eigenmode solver computes the port-plane mode, **the most accurate** (low reflection, low distortion). Requires the port face to enclose the entire field-carrying region. Automatically classifies modes and gives line/wave impedance.

**Practical antenna-feed intuition** (important):
- If you only care about the farfield pattern → use a discrete port to simplify the feed point and get a quick preliminary result.
- If you need an accurate input reflection/S-parameters → you must model the feed geometry precisely (e.g. coax → waveguide port).
- For a new antenna, **start with a discrete port**, and only move to a refined feed model once you understand how it works.

---

## 5. Antenna calculations (directly relevant to MRI coil near fields)
- **Boundary**: an antenna radiating into free space → must use **open (with an air box)** or `open (add space)` (automatically estimates the space). Open boundaries are accurate and only need a small standoff distance.
- **Farfield monitor**: defined before the simulation, each one records the entire spherical pattern; one time-domain run can produce farfields at multiple frequency points. Results live under NT: Farfields, and main-lobe/gain/efficiency/sidelobe/axial-ratio are computed automatically.
- Broadband farfield: transient can use a broadband farfield monitor or a farfield probe (only at a few θ,φ).
- Result Templates (farfield/antenna-properties group): can automatically extract 0D values like the farfield peak location, feeding an optimizer to optimize the main-lobe direction.

> **Mapping to MRI**: MRI coils care about the **near-field B1** (the internal rotating magnetic field), not the farfield. Use an H-field monitor + post-processing (B1+ computation) for the near field; see [[from-scratch-run-findings]] and the compute_b1plus pipeline. The open-boundary + air-box approach applies equally to MRI scenarios containing a body/phantom.

---

## 6. Key result/post-processing navigation paths (nav tree, NT)
- Port modes: `2D/3D Results → Port Modes → PortN` (TEM/TE/TM, beta, line impedance)
- Time signals: `1D Results → Port signals` (i1 = input / o2,1 = output, the second number = excitation port) — **after a run, first check whether the time signal has decayed to zero** (otherwise truncation error → S-parameter ripple)
- S-parameters: `1D Results → S-Parameters`; can display dB/linear/phase/Smith (Z or Y)
- Field monitors: `2D/3D Results → E-Field / H-Field / Surface Current`, f and [excitation port] are marked in the name
- Sectional fields: 2D/3D Plot → Sectional View → Fields on Plane
- Adaptive convergence curve: `1D Results → Adaptive Meshing → Delta S`
- Parameter-sweep result tables: `Tables → 0D Results` (the Tables tree only has content once a result template is defined — see [[from-scratch-run-findings]]; empty is normal)

## 7. Parameterization / sweep / optimization (iteration capability)
- Parameterization: assign variable names to geometry dimensions (the history list records all modeling operations), F7 updates parameters.
- Parameter Sweep: Simulation: Solver -> Par. Sweep, define a sequence (linear/log/arbitrary).
- Result Template: Post-Processing: Tools -> Result Templates, automatically computes a secondary result after every solver run (e.g. x at global y-min -> extracts the resonance frequency).
- Optimizer: Simulation: Solver -> Optimizer, default Trust Region Framework; the goal is based on S-parameters or a result template (e.g. move-min shifts an S21 minimum to the target frequency). Converges in just a handful of solver runs.
- **FD optimization time-saving trick**: check "Move mesh on parameter change if possible" -> reuses the already-refined tetrahedral mesh for small structural changes, without re-running adaptivity.

## 8. Coupled simulation (used by MRI System)
- **Adding circuit elements to external ports**: every 3D model has a 3D view + a Schematic view (the structure becomes a CST block with terminals = waveguide modes/discrete ports). Connect an external circuit network in the schematic -> standard or transient EM/circuit **co-simulation**. -> The core of MRI coil tuning/matching, see [[cst-circuit-sam]] for detail.
- Coupling between HF solvers: one solver's near/far field used as another's field source (antenna placement/EMC); Hybrid Solver Task.
- Coupling with thermal/mechanical: field monitor results used as a heat source -> thermal simulation -> stress -> feedback into EM sensitivity analysis (**MRI System itself contains RF+thermal tasks**). The temperature field can also feed back into temperature-dependent materials.

---

## Comparison with our dipole from-scratch experience
- What we did is exactly the "§1 workflow + Transient solver + near-field post-processing" main line; the manual confirms Transient is the officially recommended choice for a dipole.
- The manual's emphasis on "start with a discrete port" is exactly why our from-scratch approach uses a discrete port (see [[dipole-from-scratch-ground-truth]]).
- B1+ is near-field post-processing; the manual itself only covers farfield — the B1+-specific pipeline is our own compute_b1plus + [[ac-combine-b1-template-are-api]].
- To verify: which solver the MRI Coil case uses (expected Transient, 63 MHz is low frequency but the coil is weakly resonant) + whether eigenmode is used to find modes. Confirm during Phase 2 reproduction.
