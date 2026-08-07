# VBA Blocks — Dipole + Phantom (from-scratch build)

Reusable, parameterized CST VBA history blocks distilled from a verified dipole+phantom MRI project (5T, 210 MHz). Send each via `cst_add_to_history_tool(title, vba_code)` in the order below. Values are the verified defaults; expose the marked ones as tunable parameters.

Units in this project: **Length mm, Frequency GHz** (so 0.21 GHz = 210 MHz). Keep this consistent everywhere.

## Parameters (define first, via StoreParameter)

Send these as one history block titled `define parameters`:
```vba
MakeSureParameterExists("L_line", "300")      ' dipole arm length (mm) — key tunable
MakeSureParameterExists("W_line", "5")        ' dipole width (mm)
MakeSureParameterExists("T", "0.35")          ' conductor thickness (mm)
MakeSureParameterExists("hole", "1")          ' feed-gap half-height (mm)
MakeSureParameterExists("W_total", "50")      ' substrate width (mm)
MakeSureParameterExists("L_total", "L_line+50") ' substrate length (mm)
MakeSureParameterExists("T_FR4", "1.5")       ' FR-4 thickness (mm)
MakeSureParameterExists("T_polycarbonate", "18")
MakeSureParameterExists("T_foam", "1")
MakeSureParameterExists("T_dipolet_to_plantom", "T_FR4+T_polycarbonate+T_foam")
MakeSureParameterExists("x_plantom", "270")   ' phantom size X (mm)
MakeSureParameterExists("y_plantom", "650")   ' phantom size Y (mm)
MakeSureParameterExists("z_plantom", "300")   ' phantom depth Z (mm)
```

## Setup: units / frequency / background / boundary
```vba
With Units
    .SetUnit "Length", "mm"
    .SetUnit "Frequency", "GHz"
    .SetUnit "Time", "ns"
End With
Solver.FrequencyRange "0", "2"
With Background
    .Type "Normal"
    .Epsilon "1.0" : .Mu "1.0"
    .XminSpace "0.0" : .XmaxSpace "0.0" : .YminSpace "0.0"
    .YmaxSpace "0.0" : .ZminSpace "0.0" : .ZmaxSpace "0.0"
End With
With Boundary
    .Xmin "expanded open" : .Xmax "expanded open"
    .Ymin "expanded open" : .Ymax "expanded open"
    .Zmin "expanded open" : .Zmax "expanded open"
    .Xsymmetry "none" : .Ysymmetry "none" : .Zsymmetry "none"
End With
```

## Materials

Each material should have a distinct `.Colour` so models are visually clear. The Colour API takes 3 floats in [0,1] for R,G,B.

```vba
' FR-4 substrate — tan/khaki
With Material
    .Reset : .Name "FR-4 (lossy)" : .Folder "" : .Type "Normal"
    .Epsilon "4.3" : .Mu "1.0" : .TanD "0.025" : .TanDGiven "True" : .TanDModel "ConstTanD"
    .Colour "0.94", "0.82", "0.76"
    .Create
End With
' Polycarbonate (holder) — light blue
With Material
    .Reset : .Name "polycarbonate" : .Folder "Folder_MyTong" : .Type "Normal"
    .Epsilon "2.9" : .Mu "1" : .TanD "0.01" : .TanDGiven "True" : .TanDModel "ConstTanD"
    .Colour "0.65", "0.81", "0.94"
    .Create
End With
' Foam (spacer) — very light grey
With Material
    .Reset : .Name "foam" : .Folder "Folder_MyTong" : .Type "Normal"
    .Epsilon "1.05" : .Mu "1"
    .Colour "0.90", "0.90", "0.90"
    .Create
End With
' Tissue phantom (lossy) — ε=78, σ=0.47 S/m @210MHz — translucent red/pink
With Material
    .Reset : .Name "plantom" : .Folder "Folder_MyTong" : .Type "Normal"
    .Epsilon "78" : .Mu "1" : .Sigma "0.47" : .Rho "1000"
    .Colour "0.85", "0.35", "0.35"
    .Transparency "0.6"
    .Create
End With
```
> Note: verify exact ε/σ against your tissue target; these are the project's values. Each material gets a distinct colour for easy visual identification in the 3D viewport. The phantom is made semi-transparent (.Transparency "0.6") so the dipole underneath is visible.

## Geometry

Dipole conductor (PEC), with feed gap subtracted:
```vba
Component.New "component1"
With Brick
    .Reset : .Name "Dipole1" : .Component "component1" : .Material "PEC"
    .Xrange "W_line/2", "-W_line/2" : .Yrange "L_line/2", "-L_line/2" : .Zrange "0", "T" : .Create
End With
With Brick
    .Reset : .Name "hole" : .Component "component1" : .Material "FR-4 (lossy)"
    .Xrange "-W_line/2", "W_line/2" : .Yrange "-hole", "hole" : .Zrange "0", "T" : .Create
End With
Solid.Subtract "component1:Dipole1", "component1:hole"
```

Substrate + holder + foam + phantom (stacked below the dipole in −Z):
```vba
With Brick
    .Reset : .Name "FR4_board" : .Component "component1" : .Material "FR-4 (lossy)"
    .Xrange "-W_total/2", "W_total/2" : .Yrange "-L_total/2", "L_total/2" : .Zrange "-T_FR4", "0" : .Create
End With
With Brick
    .Reset : .Name "polycarbonate_board" : .Component "component1" : .Material "Folder_MyTong/polycarbonate"
    .Xrange "-W_total/2", "W_total/2" : .Yrange "-L_total/2", "L_total/2" : .Zrange "-T_FR4", "-T_FR4-T_polycarbonate" : .Create
End With
With Brick
    .Reset : .Name "foam" : .Component "component1" : .Material "Folder_MyTong/foam"
    .Xrange "-W_total/2", "W_total/2" : .Yrange "-L_total/2", "L_total/2" : .Zrange "-T_dipolet_to_plantom", "-T_dipolet_to_plantom+T_foam" : .Create
End With
With Brick
    .Reset : .Name "plantom" : .Component "component1" : .Material "Folder_MyTong/plantom"
    .Xrange "-x_plantom/2", "x_plantom/2" : .Yrange "-y_plantom/2", "y_plantom/2" : .Zrange "-T_dipolet_to_plantom", "-T_dipolet_to_plantom-z_plantom" : .Create
End With
```

## Feed port (discrete port across the feed gap) — VERIFIED from-scratch

Use a coordinate-based discrete port across the feed gap. **Critical**: `SetP1`/`SetP2` first arg is `"False"` = use free coordinates (NOT a picked point). Passing `"True"` without having pre-picked a point fails with `"No points picked for location of discrete port"`. This block was verified building from an empty project:
```vba
With DiscretePort
    .Reset
    .PortNumber "1"
    .Type "SParameter"
    .Label ""
    .Impedance "50.0"
    .Voltage "1.0"
    .Current "1.0"
    .Monitor "True"
    .Radius "0.0"
    .SetP1 "False", "0", "-hole", "T/2"   ' False = free coordinates
    .SetP2 "False", "0", "hole", "T/2"
    .InvertDirection "False"
    .LocalCoordinates "False"
    .Wire ""
    .Position "end1"
    .Create
End With
```
The port spans the feed gap (Y from −hole to +hole) at X=0, mid-thickness Z=T/2. A discrete port at the feed gap is the essential requirement.

> The original interactive project used a `DiscreteFacePort` with edge-picks (`SetP1 "True",...` after `Pick.PickEdgeFromId`), which is model-specific and fragile from scratch. The coordinate-based `DiscretePort` above is the robust from-scratch choice.

## Monitors (at Larmor frequency 0.21 GHz)
```vba
With Monitor
    .Reset : .Name "h-field (f=0.21)" : .Dimension "Volume" : .Domain "Frequency"
    .FieldType "Hfield" : .MonitorValue "0.21" : .UseSubvolume "False" : .Create
End With
With Monitor
    .Reset : .Name "e-field (f=0.21)" : .Dimension "Volume" : .Domain "Frequency"
    .FieldType "Efield" : .MonitorValue "0.21" : .UseSubvolume "False" : .Create
End With
With Monitor
    .Reset : .Name "loss (f=0.21)" : .Dimension "Volume" : .Domain "Frequency"
    .FieldType "Powerloss" : .MonitorValue "0.21" : .UseSubvolume "False" : .Create
End With
```
> h-field → B1+; loss (Powerloss) → SAR. Set MonitorValue to your Larmor frequency in the project's frequency unit.

## Solver (HF Frequency Domain, tetrahedral)
```vba
ChangeSolverType "HF Frequency Domain"
Solver.FrequencyRange "0.15", "0.25"    ' narrow band around 0.21 GHz (high-Q coil)
With FDSolver
    .Reset : .SetMethod "Tetrahedral", "General purpose"
    .OrderTet "Second" : .Stimulation "All", "1"
    .AccuracyTet "1e-4" : .MeshAdaptionTet "True"
    .CalcPowerLoss "True"
    .SetKeepSolutionCoefficients "MonitorsAndMeshAdaptation"
End With
```
> `SetKeepSolutionCoefficients` matters: keeps field solution so the later circuit co-sim can back-substitute and produce the `[AC*]` field.
