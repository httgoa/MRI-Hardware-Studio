# MRI Setup — Tier B few-shot reference (units, boundary, background, materials)

The non-geometry assembly blocks every MRI model needs. Raw history commands
(no `Sub Main`), via `add_to_history`. For the verified dipole values see
`../vba-blocks/dipole-build.md`; this file is the generalized reference. Note:
the deterministic Tier-A path renders `templates/common_setup.vba.j2` +
`templates/materials.vba.j2` — use those for known designs; use this file only
when a novel model needs hand-composed setup.

## Units / background / boundary
```vba
With Units
    .SetUnit "Length", "mm"
    .SetUnit "Frequency", "GHz"
    .SetUnit "Time", "ns"
End With
Solver.FrequencyRange "0", "2"        ' full range; narrow it in the solver block
With Background
    .Type "Normal"
    .Epsilon "1.0"
    .Mu "1.0"
    .XminSpace "0.0" : .XmaxSpace "0.0"
    .YminSpace "0.0" : .YmaxSpace "0.0"
    .ZminSpace "0.0" : .ZmaxSpace "0.0"
End With
With Boundary
    .Xmin "expanded open" : .Xmax "expanded open"
    .Ymin "expanded open" : .Ymax "expanded open"
    .Zmin "expanded open" : .Zmax "expanded open"
    .Xsymmetry "none" : .Ysymmetry "none" : .Zsymmetry "none"
End With
```
> `expanded open` = radiating (antenna/coil). Use symmetry planes only when the
> geometry AND excitation share that symmetry (halves/quarters the mesh).
> Frequency in GHz → 210 MHz Larmor = `0.21`.

## Materials — every material gets a distinct colour for a readable viewport

The `.Colour` API takes 3 floats in [0,1] (R,G,B). Make lossy tissue
semi-transparent so the coil underneath stays visible.

```vba
' PEC — CST default metallic grey (no Material block needed; use .Material "PEC")

' Copper (conductor) — built-in "Copper (pure)"; reference by name, or:
With Material
    .Reset : .Name "Copper (pure)" : .Folder "" : .Type "Normal"
    .Epsilon "1" : .Mu "1" : .Sigma "5.8e7"
    .Colour "0.85", "0.55", "0.35"
    .Create
End With

' FR-4 substrate — tan/khaki
With Material
    .Reset : .Name "FR-4 (lossy)" : .Folder "" : .Type "Normal"
    .Epsilon "4.3" : .Mu "1.0" : .TanD "0.025" : .TanDGiven "True" : .TanDModel "ConstTanD"
    .Colour "0.94", "0.82", "0.76"
    .Create
End With

' Polycarbonate holder — light blue
With Material
    .Reset : .Name "polycarbonate" : .Folder "Folder_MyTong" : .Type "Normal"
    .Epsilon "2.9" : .Mu "1" : .TanD "0.01" : .TanDGiven "True" : .TanDModel "ConstTanD"
    .Colour "0.65", "0.81", "0.94"
    .Create
End With

' Foam spacer — very light grey
With Material
    .Reset : .Name "foam" : .Folder "Folder_MyTong" : .Type "Normal"
    .Epsilon "1.05" : .Mu "1"
    .Colour "0.90", "0.90", "0.90"
    .Create
End With

' Tissue phantom (lossy, dispersive-equivalent point) — translucent red/pink
With Material
    .Reset : .Name "plantom" : .Folder "Folder_MyTong" : .Type "Normal"
    .Epsilon "78" : .Mu "1" : .Sigma "0.47" : .Rho "1000"
    .Colour "0.85", "0.35", "0.35"
    .Transparency "0.6"
    .Create
End With
```

## Rules
- Define ALL materials BEFORE geometry (a `.Material "name"` on a Brick must resolve).
- ε/σ of tissue are frequency-dependent — set them at the Larmor frequency of the study; the values above are the verified dipole@210 MHz set.
- Give the phantom a density `.Rho` (kg/m³) — required for SAR normalization.
- Distinct colours + phantom transparency are not cosmetic-only: they make the `demo_stepwise` recording and inspection legible.
