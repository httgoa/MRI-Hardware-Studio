# Boolean & Transform — Tier B few-shot reference (CST VBA)

Combine and move solids. Raw history commands (no `Sub Main`), via `add_to_history`.
Operand syntax is always `"component:solid"`. The FIRST operand is the one that
survives (result keeps its name); the SECOND is consumed.

## Boolean operations
```vba
' Add (union) — keeps solid10, absorbs solid7
Solid.Add "component1:solid10", "component1:solid7"

' Subtract — cut solid7_1 out of solid10 (slots, feed gaps, holes)
Solid.Subtract "component1:solid10", "component1:solid7_1"

' Intersect — keep only the overlap
Solid.Intersect "component1:solid10", "component1:solid2_5"

' Insert — embed one solid into another (shared boundary, both kept)
Solid.Insert "component1:solid6", "component1:solid2_3"

' Imprint — imprint edges of one onto another (no volume change)
Solid.Imprint "component1:solid8", "component1:solid9"

' Delete
Solid.Delete "component1:solid2_6"
```

Common pattern — conductor with a feed gap (dipole): build the metal brick, build
a filler brick spanning the gap, subtract:
```vba
Solid.Subtract "component1:Dipole1", "component1:hole"
```

## Transform: translate / rotate / mirror / scale

Use a fixed `.Vector` + `.UsePickedPoints "False"` so the transform does NOT
depend on a picked point (robust for scripted/batch runs — pitfall #8). Set
`.MultipleObjects "True"` + `.Repetitions N` to array-copy (e.g. birdcage rungs,
MRI Coil's 16 caps).

### Translate
```vba
With Transform
    .Reset
    .Name "component1:solid2"
    .Vector "10", "10", "10"
    .UsePickedPoints "False"
    .InvertPickedPoints "False"
    .MultipleObjects "False"
    .GroupObjects "False"
    .Repetitions "1"
    .MultipleSelection "False"
    .Destination ""
    .Material ""
    .AutoDestination "True"
    .Transform "Shape", "Translate"
End With
```

### Rotate (about an axis through a center)
```vba
With Transform
    .Reset
    .Name "component1:solid2"
    .Origin "Free"
    .Center "0", "0", "0"
    .Angle "0", "0", "30"          ' degrees about X,Y,Z
    .MultipleObjects "True"
    .Repetitions "11"              ' 12 total = 30 deg step (birdcage rungs)
    .GroupObjects "False"
    .Destination ""
    .Material ""
    .AutoDestination "True"
    .Transform "Shape", "Rotate"
End With
```

### Mirror (about a plane through Center with normal PlaneNormal)
```vba
With Transform
    .Reset
    .Name "component1:solid2"
    .Origin "Free"
    .Center "0", "0", "0"
    .PlaneNormal "1", "0", "0"
    .MultipleObjects "True"        ' True = keep original + add mirror
    .Repetitions "1"
    .Destination ""
    .Material ""
    .AutoDestination "True"
    .Transform "Shape", "Mirror"
End With
```

### Scale
```vba
With Transform
    .Reset
    .Name "component1:solid2"
    .Origin "Free"
    .Center "0", "0", "0"
    .ScaleFactor "2", "2", "1"
    .MultipleObjects "False"
    .Transform "Shape", "Scale"
End With
```

## Rules
- Array-copy identical elements with `MultipleObjects "True"` + `Repetitions` instead of re-modeling each — one block builds a whole ring/array.
- After a batch of transforms/booleans the tree order matters: subtract AFTER both solids exist.
- Verify operand names exactly (`component1:Name`); a typo yields "shape not found", not a silent no-op.
