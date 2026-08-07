# CST Circuit Simulation & SAM Basics (distilled from the official manual Circuit Simulation & SAM 2024)

> Source: `Documentation/CST Studio Suite - Circuit Simulation and SAM (System Assembly and Modeling).pdf` (89 pages; close-read ch2 quick tour + ch4 co-sim + ch6 3D embedding).
> Purpose: master CST Design Studio (DES)'s schematic circuit layer — the core of MRI coil **tuning/matching + 3D↔circuit co-simulation**. Compared against our dipole circuit AC1 experience at the end.

---

## 1. What is CST Design Studio (DES)
- CST's **system-level/circuit-level schematic simulator**, tightly coupled with the 3D EM solver.
- Two forms of existence (build and simulation flow are identical):
  1. **Standalone tool**: pure circuit, not connected to any 3D project.
  2. **Associated view of a 3D project**: the Schematic tab at the bottom of a 3D project. Here the schematic has a pre-placed block representing the 3D structure (the MWS block), whose pins = the 3D project's waveguide/discrete ports, one-to-one.
- The 3D view and schematic view **share the same set of project parameters**.

## 2. Schematic building blocks (block terminology)
- **Component / Circuit Model (collectively "block")**:
  - Analytical: analytic/semi-analytic (R/L/C, transmission lines, etc.), parameterized circuit models.
  - Measured: `TOUCHSTONE` blocks (imported S-parameters), IBIS, C/L/Reactance matrix blocks.
  - **Simulated**: references/embeds a 3D EM project (see §5), parameter-controllable.
  - Special: ground, CST DES block (hierarchical subsystem placeholder), reference block.
- **External Port**: the system's source/sink (yellow rectangle). S-parameter calculation requires an external port.
- **Connector**: pure electrical connection, **no electrical length/no physical properties**, only connects internal ports.
- **Probe**: placed on a connector, records voltage/current (used for transient tasks).
- **Connection Label**: same-name labels = electrically connected, used instead of wires to keep the diagram cleaner.

**Build shortcuts** (frequently used): `g`=ground, `p`=port, `l`/`r`=rotate left/right, `c`=auto-connect, `o`=probe, `shift`+drag=snap-in/out (keeps the connection while swapping the component). Red pin=unconnected, blue=connected. T/cross nodes: dragging a pin onto a wire auto-creates a node (up to 4 connections).

## 3. Simulation Task mechanism — DES's core organizational unit
- Analyses are all organized as **Tasks**: Home: Simulation → New Task.
- The task tree lives under NT: Tasks; tasks can be **nested** (e.g. an S-parameter task inside a sweep/optimization task).
- Update (Ctrl+F5) = execute all tasks in sequence; you can also update/disable/enable a single task.
- Common tasks: **Circuit → S-Parameters**, **Transient** (co-sim), **AC (Combine results)** (computes the farfield/driven field), Parameter Sweep, Optimization.
- The S-parameter task has three tabs: S-Parameters (frequency range/sample count/circuit simulator choice of CST or export to HSPICE netlist), Terminations (external port reference impedance, default 50Ω or block-dependent), Results.

## 4. Two kinds of EM/Circuit Co-Simulation (key distinction)
| | Standard EM/circuit co-sim | Transient EM/circuit co-sim |
|---|---|---|
| Task type | S-Parameters | Transient |
| How the 3D block is represented | Characterized by **S-parameters** (the full-port S-matrix is computed beforehand) | Directly **co-solves** circuit + EM, using only the single excitation defined in the circuit |
| Computational cost | Requires an FD frequency sweep or one time-domain simulation per port | Only one coupled simulation |
| When it's faster | Few ports | **Faster with many ports** (no need to compute a generic S-matrix) |
| Setup | New Task → S-Parameters, Update | New Task → Transient, choose "CST transient co-simulation", set Tmax, define the Gaussian excitation on the Excitations tab, add a probe, Update |

**Mental model**: standard co-sim first turns the 3D block into an S-parameter "black box", then lets you wire up arbitrary networks in the circuit and recompute freely — **this is the workhorse for MRI coil tuning/matching** (changing circuit component values doesn't require re-running the 3D solve). If the 3D results already exist, the circuit simulation only takes seconds.

## 5. Three kinds of blocks for embedding a 3D project into DES (ch6, directly relevant to MRI/matching)
| Block type | Storage | Parameter control | Use |
|---|---|---|---|
| **CST Studio Suite File block** | References the original project (relative/absolute path), tracks changes | No (essentially S-parameters) | A fixed, unchanging 3D model (e.g. a finalized antenna) |
| **CST Studio Suite block** | Stores an internal copy of the project | **Yes** — 3D project parameters can be changed from within DES | A 3D model that needs to be parameterized/optimized from the circuit layer |
| **Clone block** | References another block's model | Optional (independent parameters once Inherit is turned off) | Repeated blocks with the same topology but different parameter values only (avoids duplicate copies) |

**File block intelligence**: if the referenced project lacks results (not solved / only some ports excited), DES will **automatically trigger the required 3D simulation** before the circuit simulation.

## 6. Matched Antenna example (full ch6 pipeline, maps to our B1+ workflow)
A patch antenna (dual-fed, ~100Ω) + two impedance transformers (microstrip step) + a 50Ω external port. Design goal = tune w1/w2 to minimize reflection at the 50Ω input. Pipeline:
1. Build the patch (File block) + transformer (SS block, parameterized w) + another transformer (Clone block) separately.
2. Connect: the 100Ω side of the transformer to the antenna, the 50Ω side to the external port.
3. **S-Parameter task** → initial matching result.
4. **Optimization task** (Trust Region Framework): goal = min S11@7GHz + min S22@7.5GHz, parameter 0.7≤w≤2.4 → optimized matching.
5. **AC, Combine results task**: on the Combine Results tab select the antenna block; on the Excitations tab define each port's amplitude (e.g. port1=1, port2=0) → use the farfield monitor pre-set in the antenna's 3D project to compute the **farfield under the driven excitation** (result labeled `[AC1]`, in the Farfields tree of the antenna block's project, without re-running the 3D solve).

> **Mapping to MRI (important)**: this "S-parameters -> optimized matching -> AC combine to get the driven field" pipeline is exactly the official prototype for our dipole B1+ workflow! In MRI coils, farfield is replaced by the **near-field/B1+**, and AC combine is used to combine multi-port/quadrature excitation to obtain the rotating B1 field. See [[ac-combine-b1-template-are-api]] (docombineresults + Result3D.Combine are the official APIs) and [[dipole3-reference-case]].

## 7. SAM (System Assembly and Modeling)
- ch3 covers planar circuits + assemblies + managing variations (parametric variant management).
- SAM = uses hierarchical tasks to orchestrate multiple coupled simulations + post-processing, managing different simulation aspects of a complex system (e.g. MRI System: empty coil/phantom/human voxel model x RF/thermal multi-task).
- PCB Studio makes heavy use of SAM to automatically build equivalent circuits + multi-simulation projects.

---

## Comparison with our dipole experience
- Our dipole's "circuit AC1" stage is exactly §4's **standard EM/circuit co-sim** (3D block + tuning network -> S-parameters -> combined field). The manual confirms this is the official main line, not a workaround. See [[dipole-b1-pipeline]].
- The **AC-combine popup** problem we hit ([[ac-combine-b1-template-are-api]] / [[dipole3-reference-case]]): manual §6 shows AC Combine is a regular task; the popup comes from the filter `*` hitting the non-combinable surface-current, not an API limitation.
- The tuning network ([[dipole-from-scratch-ground-truth]]) = §2's analytical R/L/C blocks built in the schematic + §5's SS block parameterization.
- To verify in Phase 2: whether MRI Coil uses AC combine to combine quadrature ports for rotating B1; how MRI System's SAM multi-task organizes empty coil/phantom/human voxels x RF/thermal.
