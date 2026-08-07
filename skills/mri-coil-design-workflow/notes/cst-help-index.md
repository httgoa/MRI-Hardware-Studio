# CST Online Help Index Map (task → help page / VBA API)

> Source: `D:\ght\softwares\MRI_agent_softwares\Online Help\mergedProjects\` (~1413 HTML pages, not read cover-to-cover).
> Usage: when reproducing a project and you hit "how do I do this operation/dialog/API", locate the specific .htm by task and read that page in detail.
> Path root: `<HELP>` = `Online Help/mergedProjects`. Sub-projects: `3D` (HF/modeling/solver main help), `VBA_3D` (3D's VBA API), `DES` (circuit), `Python` (Python API).
> How to open: Read the .htm (RoboHelp pages contain the body text), or F1 inside CST / the dialog's Help button.
> **Relevance tags**:=frequently used for MRI / =general modeling/simulation /
=magnetostatic/thermal and other extended scenarios.

---

## A. Modeling / Geometry (`3D/common_struct/`, 96 pages)
Filename pattern `common_struct_<shape>.htm`:
- Primitives: `_brick` `_cylinder` `_cone` `_ecylinder`(elliptical cylinder) `_sphere`(see directory)
- Curves: `_curveline` `_curvecircle` `_curvearc` `_curvespline` `_curvepolygon` `_curverectangle` `_curveellipse`
- Curve→face/solid: `_curvecover` `_curveextrude` `_curvesweep` `_curveloft` `_cover_curve_to_face` `_extrude_face`
- Boolean/transform: `_auto_inter`(intersect) `_change_material` `_changecomponent`
- WCS: `_def_wcs` `_store_current_wcs`
- Wire/lead: `_bondwire` `_3dpolygon` `_convert_wire_to_solid` `_create_trace_from_curve`
> Authoritative modeling-operation reference; pair with the Getting Started ch4 (history syntax) in [[cst-manuals-map]].

## B. Mesh (`3D/common_mesh/`, 19 pages)
- `common_mesh_automesh.htm` `_automeshgen` `_automeshref`(adaptive) — mesh generation
- `_shape_automesh_props_hex.htm` / `_tet.htm` / `_srf.htm` — per-mesh-type local properties
- `_fixpoint*` `_denspoint` — fixed points/density points
- `_tetmethod` `_tetsurface` `_tetvolume` — tetrahedral control
- Adaptive refinement detail is in §D's `special_solvopt_adaptive_*`

## C. Ports / Excitation / Monitors (`3D/special_solvopt/`, selected) 
- **Ports**: `_discreteports.htm`  `_discrete_face_port.htm` `_ports.htm` `_define_current_port.htm`
- **Port modes**: `_port_mode_information.htm` `_port_mode_excitation_selection.htm`
- **Boundaries/symmetry**: `_boundary_conditions_boundaries.htm`  `_boundary_conditions_symmetryplanes.htm`  `_boundary_conditions_periodicboundary_phaseshift.htm` `_boundary_conditions_unit_cell.htm`
- **Excitation signals**: `_excitation_signal.htm` `_excitation_functions.htm` `_td_excitation_selection.htm` `_frequency_domain_select_excitation.htm`
- **Field monitors**: `_monitor.htm`  `_time_monitor_3d.htm` `_freqpowerlossesmonitor.htm`(losses) `_farfield_source.htm`
- **Probe**: `_probe.htm` `_probe_general.htm`
- **S-parameter symmetry/acceleration**: `_sparameter_symmetries.htm` `_acceleration.htm`

## D. Solver Settings (`3D/special_solvopt/`)
- **Time domain (Transient)** : `_t3solverspecsolver.htm` `_t3solverspecwave.htm`(waveguide) `_t3solverspecpba.htm`(PBA) `_t3solverspecsteady.htm` `_t3solverspecarfilt.htm`(AR filter) `_adaptive_mesh_refinement_time_domain.htm`
- **Frequency domain (FD)**: `_frequency_domain_solver_sampling.htm` `_adaptive_mesh_refinement_frequency_domain.htm` `_adaptive_tet_mesh_refinement.htm`
- **Eigenmode**: `_eigenmode_solver_specials_tetrahedral.htm` `_eigenmode_solver_specials_jd.htm` (finding coil modes)
- **Integral equation/multilayer/asymptotic**: `_integral_equation_solver_parameters.htm` `_multilayer_solver_parameters.htm` `_asymptotic.htm`
- **TLM**: `_tlmsolver.htm` `_tlmsolverspec.htm`
- **Optimization/sweep**: `_parametersweepoptions.htm`  `_non_parametric_optimizer.htm`
- **Magnetostatic/low-frequency**: `_magnetostatic_solver_dialog.htm` `_low_frequency_solver_dialog.htm` `_coilgroup.htm` `_define_current_coil_from_curves.htm` `_inductance_admittance_matrices.htm`(inductance matrix)→gradient coils
- **Thermal (CHT)** : `_thermal_solver_parameters.htm` `_cht_solver_parameters.htm` `_import_thermal_losses_from_project.htm`(SAR→thermal) `_thermal_current_losses.htm`
- **Field import**: `_import_external_fields.htm` `_import_external_field_from_project.htm`

## E. Post-Processing / Fields / Results (`3D/special_postpr/`, 68 pages) 
- **Combine Results**: `special_postpr_combineresults.htm`  `_combineselection.htm` — **the dialog that produces the rotating-B1 AC combine** (corresponds to [[ac-combine-b1-template-are-api]])
- **Near field**: `_nearfieldscan.htm` — MRI B1 near field
- **De-embedding**: `_deembed.htm`
- **Q factor**: `_qfactor.htm` `_qfactorspecials.htm`(resonant coils)
- **Farfield**: `_farfield.htm` `_farfieldview.htm` `_farfield_1dcuts.htm` `_pp_farfield.htm`
- **1D/S-parameters**: `_pp_onedresults.htm` `_pp_onedsignals.htm` `_pp_smithchart.htm` `_pp_balance.htm`(power balance) `_portinfo.htm`
- **Field selection/storage**: `_select_field.htm` `_resultstorage.htm` `_twothreedresultview.htm`

## F. Import/Export (`3D/common_tools/`, 74 pages)
- **Body/voxel**: `common_tools_import_voxel_data.htm` `common_tools_human_material_macro.htm` — the human body model used in MRI System
- CAD import: `_import_step.htm` `_import_solidworks.htm` `_import_catia.htm` `_import_hfss.htm`
- Export: `_export_step.htm` `_exportsat.htm` `_exportstl.htm` `_exportnastran.htm` `_export_gdsii.htm`
- Curves/data: `_import_1dcurvefromascii.htm` `_settings_for_2d3dplotdata_export.htm`

---

## G. VBA API (`VBA_3D/`) — the direct basis for MCP script execution
> We drive CST's VBA/history commands through MCP; these are the authoritative signatures of the object methods.
- **Solver objects** (`special_vbasolver/`): `solver_object.htm`(time domain) `fdsolver_object.htm`(frequency domain) `eigenmodesolver_object.htm` `iesolver_object.htm` `optimizer_object.htm` `background_object.htm` `boundary_object.htm` `sensitivityanalysis_object.htm`
- **Port objects** (`special_vbaports/`): `special_vbaports_discrete_port_object.htm` `_discrete_face_port_object.htm` `_port_object.htm` `_fieldsource_object.htm` `planewave_object.htm` `floquetport_object.htm`
- **Monitor objects** (`special_vbamonitors/`): `monitor_object.htm` `probe_object.htm` `timemonitor3d_object.htm` `currentmonitor_object.htm` `voltagemonitor_object.htm`
- **Post-processing objects** (`special_vbapostproc/`): `special_vbapostproc_combineresults_object.htm` `_result_3d_object.htm`(Result3D.Combine) `_nearfieldscan_object.htm` `_qfactor_object.htm` `result_0d_object.htm` `result_1d_complex_object.htm` `farfieldploto.htm` `resulttreeo.htm`
- **Static solver objects** (`special_vbastaticsolver/`: `mstaticsolver_object.htm`(magnetostatic) `lfsolver_object.htm` `estaticsolver_object.htm` `stationarycurrentsolver_object.htm`
- Python API: the `Python/` sub-project (consult when using CST's Python rather than VBA)

## H. Circuit / Design Studio (`DES/`)
- **Circuit components** (`components/block/`): `inductor.htm` `capacitor.htm` `resistor.htm` `idealtransformer.htm` `operationalamplifier.htm` `amplifierblock.htm` — tuning/matching-network components
- **Couplers/transmission lines**: `microstriplinecoupler(2ports)block.htm` `directionalcouplerblock.htm` `microstripbranchlinecouplerblock.htm` etc.
- **Ports/connections** (`components/port/`,`/connector/`,`/probe/`): external ports, connections, probes
- **Analysis settings** (`analysis/`): `units.htm` `local_units.htm` `enable_interpolation.htm` `updatefilereferences.htm`
- Thermal components: `thermalcapacitor.htm` `thermalresistor.htm`

---

## Quick lookup (most-asked questions during reproduction → where to go)
| I want to… | Go to |
|---|---|
| Add a discrete port | §C `_discreteports` + §G `discrete_port_object` |
| Set boundaries/symmetry | §C `_boundary_conditions_*` + §G `boundary_object` |
| Define a field monitor | §C `_monitor` + §G `monitor_object` |
| Combine into rotating B1 | §E `combineresults` + §G `combineresults_object` / `result_3d_object` |
| Near-field scan | §E `_nearfieldscan` + §G `nearfieldscan_object` |
| Tuning/matching network | §H components/block + [[cst-circuit-sam]] |
| Import body/phantom | §F `import_voxel_data` / `human_material_macro` |
| SAR→thermal coupling | §D `import_thermal_losses` + [[cst-manuals-map]] Thermal ch2 |
| Gradient/magnetostatic coils | §D `magnetostatic` / `coilgroup` / `inductance_matrices` |
| Parameter sweep/optimization | §D `parametersweepoptions` + §G `optimizer_object` |

## To verify/fill in during reproduction (Phase 2 markers)
- [ ] Open a page to confirm the path spelling is correct (RoboHelp sometimes uses different suffixes).
- [ ] The actual method signatures of the combineresults / result_3d objects vs. our remembered usage ([[ac-combine-b1-template-are-api]]).
- [ ] Whether the body import used by MRI System goes through `import_voxel_data`.
- [ ] Backfill any high-frequency pages discovered during reproduction into the corresponding section.
