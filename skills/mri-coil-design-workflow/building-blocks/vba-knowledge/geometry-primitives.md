# Geometry Primitives — Tier B few-shot reference (CST VBA)

Canonical CST history VBA for the basic solids and 2.5D curves. This is the
**Tier B unit library** (LEAM `modeling_3d.md` analog): when generating a NOVEL
topology, the generator picks primitives from here and fills in
parameter expressions — it does NOT invent VBA. Blocks are **raw history
commands (no `Sub Main`)**, sent via `add_to_history`.

Conventions (always):
- Give every solid a `.Name` and `.Component` (`Component.New "component1"` once).
- Set `.Material` to a material that already exists (define materials first — see `mri-setup.md`).
- One primitive per named history block keeps the tree readable and lets
  `demo_stepwise` repaint per step.
- Coordinates in model units (mm). No units suffix inside expressions.

## Main focus (covers most antennas/coils): Brick + Cylinder

### Cuboid (Brick)
```vba
With Brick
    .Reset
    .Name "solid1"
    .Component "component1"
    .Material "PEC"
    .Xrange "-2", "2"
    .Yrange "-2", "2"
    .Zrange "0", "4"
    .Create
End With
```

### Cylinder (rod / ring; set InnerRadius > 0 for a tube)
```vba
With Cylinder
    .Reset
    .Name "solid5"
    .Component "component1"
    .Material "PEC"
    .OuterRadius "1"
    .InnerRadius "0"
    .Axis "z"
    .Zrange "0", "6"
    .Xcenter "-17"
    .Ycenter "-3"
    .Segments "0"
    .Create
End With
```
`.Segments "N"` (N≥3) turns the cylinder into an **N-sided prism**.

### Circular planar patch on substrate
Distilled from `notes/repro-07-circular-patch-td.md`. This Component Library
pattern is a PEC disk plus a PEC feed strip embedded into a dielectric substrate.
It is useful for circular patch / circular resonator variants.

```vba
With Cylinder
     .Reset
     .Name "solid1"
     .Layer "PEC"
     .OuterRadius "17"
     .InnerRadius "0"
     .Axis "z"
     .Zrange "0", "0.05"
     .Xcenter "0"
     .Ycenter "0"
     .Create
End With

With Brick
     .Reset
     .Name "solid2"
     .Layer "PEC"
     .Xrange "-2", "2"
     .Yrange "-56", "0"
     .Zrange "0", "0.05"
     .Create
End With
```

Then define a substrate layer/material and insert the PEC shapes into the
substrate with `Solid.Insert`. Keep the official pick-point blocks when the
substrate extents depend on `xp()/yp()/zp()` values from picked geometry.

### Circular resonator annulus
Distilled from `notes/repro-08-circular-resonator.md`. This is a two-port
resonator pattern: an annular conductor plus a small coupling brick that is
rotated and boolean-added.

```vba
With Cylinder
     .Reset
     .Name "solid1"
     .Layer "default"
     .OuterRadius "7"
     .InnerRadius "4"
     .Axis "z"
     .Zrange "0", "0.05"
     .Xcenter "0"
     .Ycenter "0"
     .Create
End With
```

The official case uses parameters `k=5.76` and `h=0.635`; define them before
port/mesh history replay when reproducing from `ModelHistory.json`.

## Secondary primitives

### Sphere
```vba
With Sphere
    .Reset
    .Name "solid2"
    .Component "component1"
    .Material "PEC"
    .Axis "z"
    .CenterRadius "2"
    .TopRadius "0"
    .BottomRadius "0"
    .Center "-6", "8", "0"
    .Segments "0"
    .Create
End With
```

### Cone (TopRadius ≠ BottomRadius)
```vba
With Cone
    .Reset
    .Name "solid3"
    .Component "component1"
    .Material "PEC"
    .BottomRadius "3"
    .TopRadius "1"
    .Axis "z"
    .Zrange "0", "5"
    .Xcenter "10"
    .Ycenter "7"
    .Segments "0"
    .Create
End With
```

### Torus (end-rings for birdcage)
```vba
With Torus
    .Reset
    .Name "solid4"
    .Component "component1"
    .Material "PEC"
    .OuterRadius "3"
    .InnerRadius "1"
    .Axis "z"
    .Xcenter "5"
    .Ycenter "-7"
    .Zcenter "0"
    .Segments "0"
    .Create
End With
```

### Elliptical cylinder
```vba
With ECylinder
    .Reset
    .Name "solid7"
    .Component "component1"
    .Material "PEC"
    .Xradius "2.5"
    .Yradius "3.5"
    .Axis "z"
    .Zrange "0", "8"
    .Xcenter "-12"
    .Ycenter "-6"
    .Segments "0"
    .Create
End With
```

### Analytic face (curved surfaces, e.g. saddle)
```vba
With AnalyticalFace
    .Reset
    .Name "solid8"
    .Component "component1"
    .Material "PEC"
    .LawX "u"
    .LawY "v"
    .LawZ "0.25*(u^2 - v^2)"
    .ParameterRangeU "-4", "4"
    .ParameterRangeV "-4", "4"
    .Create
End With
```

## 2.5D: draw a planar curve, then extrude/rotate into a solid

Use for slots, traces, tapered/curved conductors. First draw a **closed profile**
curve (`Polygon`/`Circle`/`Ellipse`/`Arc`/`Spline`), then turn it into a solid.

### Planar curve (Polygon example — close the loop by returning to the start)
```vba
With Polygon
    .Reset
    .Name "polygon1"
    .Curve "curve1"
    .Point "-6", "2"
    .LineTo "-6", "-2"
    .LineTo "-0", "-2"
    .LineTo "0", "2"
    .LineTo "-6", "2"
    .Create
End With
```
Other curves: `Line`, `Circle` (`.Radius/.Xcenter/.Ycenter`), `Ellipse`
(`.XRadius/.YRadius`), `Arc` (`.Orientation/.Angle`), `Spline`, `AnalyticalCurve`
(`.LawX/.LawY/.LawZ/.ParameterRange`). Same `.Curve "curve1"` groups them.

### Extrude a closed curve to a solid
```vba
With ExtrudeCurve
    .Reset
    .Name "solid1"
    .Component "component1"
    .Material "Copper (pure)"
    .Thickness "1"
    .Twistangle "0.0"
    .Taperangle "0.0"
    .DeleteProfile "True"
    .Curve "curve1:polygon1"
    .Create
End With
```

### Rotate a profile (surface of revolution)
```vba
With Rotate
    .Reset
    .Name "solid10"
    .Component "component1"
    .Material "PEC"
    .Mode "Pointlist"
    .StartAngle "0.0"
    .Angle "360"
    .Height "0.0"
    .RadiusRatio "1.0"
    .NSteps "0"
    .SplitClosedEdges "True"
    .SegmentedProfile "False"
    .SimplifySolid "False"
    .UseAdvancedSegmentedRotation "True"
    .CutEndOff "False"
    .Origin "0.0", "0.0", "0.0"
    .Rvector "0.0", "1.0", "0.0"
    .Zvector "1.0", "0.0", "0.0"
    .Point "-0", "-28.5"
    .LineTo "-3", "-24.5"
    .LineTo "-5", "-30"
    .LineTo "-0.5", "-33.5"
    .LineTo "-2.5", "-29.5"
    .LineTo "-0", "-28.5"
    .Create
End With
```

## Rules
- Compose complex shapes from primitives + booleans (`boolean-transform.md`), not from one exotic call.
- If a shape is not here, prefer extrude/rotate of a drawn profile over inventing a solid API.
- On any "Method or property not found", STOP — check the official VBA reference (SKILL iron rule); do not guess.
