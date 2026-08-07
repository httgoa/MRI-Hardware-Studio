# Ports / Monitors / Mesh — Tier B few-shot reference (CST VBA)

Excitation, field recording, and mesh. Raw history commands (no `Sub Main`),
via `add_to_history`, EXCEPT where noted.

## Discrete port (coordinate-based — robust from scratch)

**CRITICAL** (pitfall #4/#7): `SetP1`/`SetP2` first arg `"False"` = use free
coordinates. Passing `"True"` without a pre-picked point fails with
"No points picked for location of discrete port". Prefer coordinates for scripted runs.
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
    .SetP1 "False", "0", "-hole", "T/2"    ' False = free coordinates
    .SetP2 "False", "0", "hole", "T/2"
    .InvertDirection "False"
    .LocalCoordinates "False"
    .Wire ""
    .Position "end1"
    .Create
End With
```
- `DiscretePort` (2-point) → **4-pin single-ended** MWSSCHEM in the schematic
  (signal pin only, reference implicitly grounded).
- `DiscreteFacePort` (face-to-face) → **8-pin differential** MWSSCHEM (pitfall #15).
  Choose one type up front and never switch mid-model. Face ports need
  `Pick.PickEdgeFromId` for the 2 edges INSIDE the same block before `.Create` (pitfall #7).

## Waveguide port on planar substrate boundary

Distilled from `notes/repro-07-circular-patch-td.md`. Official circular patch
cases use a boundary waveguide `Port`, not a `DiscretePort`, for the feed strip.
The port is placed at `ymin` with free coordinate ranges.

```vba
With Port
     .Reset
     .PortNumber "1"
     .NumberOfModes "1"
     .AdjustPolarization False
     .PolarizationAngle "0.0"
     .ReferencePlaneDistance "yp(1)-yp(0)+17"
     .TextSize "50"
     .Coordinates "Free"
     .Location "ymin"
     .Xrange "-20", "20"
     .Zrange "-3.18", "10"
     .ClipPickedPortToBound("false")
     .Create
End With
```

Use this pattern for planar antenna Component Library replays. For MRI loop
coils that need circuit co-simulation pins, prefer `DiscretePort` or
`DiscreteFacePort` according to the schematic pin behavior required.

## Picked-face waveguide ports with parameter offsets

Distilled from `notes/repro-08-circular-resonator.md`. The official circular
resonator uses `Pick.PickFaceFromId` before each `Port.Create`, then extends the
picked port bounds using parameter expressions. Define `k` and `h` first.

```vba
With Port
     .Reset
     .PortNumber "1"
     .NumberOfModes "1"
     .Coordinates "Picks"
     .Orientation "positive"
     .PortOnBound "True"
     .ClipPickedPortToBound "False"
     .Xrange "-14", "-14"
     .Yrange "-0.3", "0.3"
     .Zrange "0", "0.05"
     .XrangeAdd "0.0", "0.0"
     .YrangeAdd "k*h", "k*h"
     .ZrangeAdd "h", "k*h"
     .SingleEnded "False"
     .Create
End With
```

This is still a 3D MWS port workflow, not a Design Studio matching/cosim
workflow. The schematic contains only the automatic `MWSSCHEM` port exposure.

## Field monitors (at the Larmor frequency)
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
- `Hfield` → B1+; `Powerloss` → SAR; `Efield` for diagnostics.
- Farfield (antenna gain, not usually MRI):
```vba
With Monitor
    .Reset : .Name "farfield (f=0.21)" : .Dimension "Volume" : .Domain "Frequency"
    .FieldType "Farfield" : .MonitorValue "0.21" : .ExportFarfieldSource "False" : .Create
End With
```

## Mesh (global settings; keep minimal — let the solver adapt)
```vba
With Mesh
    .MeshType "Tetrahedral"
    .SetCreator "High Frequency"
End With
With MeshSettings
    .SetMeshType "Tetrahedral"
    .Set "Version", 1
    .Set "CellsPerWavelengthPolicy", "automatic"
End With
```
> For native 10g SAR you need a **hexahedral** mesh + Time Domain solver
> (pitfall #18) — see `solvers.md`. For B1+/S-params, tetrahedral + FD is fine.

## Rules
- One port block per port; name monitors with the frequency so the export candidate
  paths in `../vba-blocks/field-export.md` match.
- Don't over-specify the mesh: set the method + let mesh adaptation refine. Copying a
  full official mesh setter block risks version-mismatch popups (pitfall #11).
- `.Monitor "True"` on the port records port signals needed for S-params / co-sim.
