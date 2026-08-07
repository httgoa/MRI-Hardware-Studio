# Reproduction 02: Dipole Antenna Array (official Component Library)

> Phase 2, second case. Official reference (read-only): `references_cases/Dipole Antenna Array/`. Reproduction project: `results/dipole_array_repro/`.
> Result: **successful** — farfield peak directivity **7.50 dBi**, matching the expectation for "variant 3 (array-factor / mutual coupling ignored)".

## Key insight for this case: one example name has 4 variants
The tutorial `dipole_antenna_array.htm` describes 4 ways to implement the same 2×2 array:
1. **Combine Nearfield Results**: build the full 4-dipole solid, excite each individually (4 simulations), post-process with `Combine Results` to superpose a 90° phase shift → **includes mutual coupling**. Important: this is exactly the same mechanism as MRI rotating B1!
2. **Simultaneous Excitation**: excite all 4 solids at once (1 simulation, excitation table carries a 90° phase shift), 4x faster, but the phase shift is fixed at a single frequency and can't be changed in post-processing.
3. **Farfield Array Feature**: **builds only a single dipole**, multiplies by an array-factor pattern to compute the array, **ignores mutual coupling**. ← This is the one we downloaded.
4. **Mix Farfield Results Template**: builds the full structure but only excites port1, combines farfield rotation + phase shift (the mix farfield results template), includes mutual coupling, phase shift is adjustable, needs only 1 simulation.

What we downloaded, "Dipole Antenna Array", = **variant 3**. Geometry = a single dipole (nearly identical to reproduction 01, only the gap brick uses `-2*r..2*r`). The core is the history's `FarfieldArray` block:
```
With FarfieldArray
  .UseArray "TRUE" : .Arraytype "Rectangular"
  .XSet "2", "lambda0/4", "90.0"   '2 elements, lambda/4 spacing, 90 deg phase shift
  .YSet "2", "lambda0/4", "90.0"
  .ZSet "1", "0.0", "0.0"          '1 element along Z -> 2x2 planar array
End With
```
Solver SteadyStateLimit **-30dB** (looser than reproduction 01's -60, since the array factor doesn't need to be that strict).

## Results comparison
- The tutorial states the array's main lobe at phi≈225° with directivity **≈8.6 dB** — but that's the value for **variants 1/2/4 (with mutual coupling)**.
- Our variant 3 got **7.50 dBi**, about 1.1 dB lower. **This is correct**: the tutorial text explicitly states variant 3 "differs clearly...due to the negligence of the coupling between the array elements". Ignoring mutual coupling → lower directivity is expected behavior.
- The single-dipole resonance matches reproduction 01's geometry (27GHz), no need to re-verify.

## MCP/VBA reproduction pitfalls (new to the knowledge base, important)
1. **Correct usage of the farfield list API** (I initially fabricated all of it, incorrectly):
   - Wrong: there is no `GetListLength`/`GetListAngle`/`SetArrayScaling`.
   - Correct: the flow is `AddListEvaluationPoint theta, phi, radius, "spherical", "frequency", freq` added point-by-point → `CalculateList("")` → `GetList(component)` to get the whole Double array / `GetListItem(i, component)` for a single point / **`GetMax`** for the peak value.
   - Correct: a valid fieldComponent must include the component, e.g. `"Spherical linear theta abs"`, `"Spherical linear phi abs"`, `"Point_T"`, `"Point_P"`. There is **no** generic `"Spherical linear abs"`.
   - Correct: simplest way to verify peak directivity: `FarfieldPlot.Reset : .SetPlotMode "Directivity" : .Plottype "polar" : .Vary "angle2" : .Theta "90" : .SetFrequency f : .Plot` then `.GetMax`.
2. **Warning: `StoreDoubleParameter` triggers a parameter-change event → deletes the run_id=0 solve results!** I used it to store an analysis result, which caused subsequent reads of S1,1 to report "ResultItem does not exist for run id=0".
   - **Lesson**: don't use StoreDoubleParameter to store an "analysis output value". To retrieve a VBA-computed value, write it via `ReportInformationToWindow("KEY=" & CStr(val))`, then read it back from `cst_project_info_tool`'s `messages_tail`. **This read path doesn't contaminate the project.**
   - If mistakenly stored, `DeleteParameter` + re-store, but the lost results need to be re-run.
3. Retrieving the farfield `GetMax` value: `ReportInformationToWindow` + reading `messages_tail` is the stable return channel (`cst_run_python`'s `project.get_parameter` isn't available in this version).

## Knowledge-base validation conclusion
- The HF notes' farfield/array judgment confirmed; added the correct farfield list API signature (the help index §E/§G entries were hit but method details needed empirical verification — now backfilled).
- Added a new red-line "never use StoreDoubleParameter for analysis output" → should be added to [[from-scratch-run-findings]]'s pitfall pool, same category as [[repro-01-dipole-antenna]].
- Variant concept: **the same-named example can have multiple implementation variants; read the tutorial before reproducing to confirm which one you downloaded** → a general lesson.
- Related: [[cst-hf-fundamentals]] [[cst-help-index]] [[repro-01-dipole-antenna]] [[textbook-case-readonly]].

## Value for MRI
Variant 1's "excite each port individually + Combine Results to superpose a 90° phase shift" = **the exact same math used by MRI quadrature coils to generate a rotating B1**. The next MRI Coil case will use this mechanism (see [[ac-combine-b1-template-are-api]]).
