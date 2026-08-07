# Field Export — HDF5 via SelectTreeItem + ASCIIExport (verified expert path)

Reliable way to get a 3D field result (H-Field / E-Field / B1+) out of CST and into a file we
can post-process in pure Python. Distilled from a professional's fully-tuned workflow.

**Why this path**: exporting to **HDF5 with a fixed physical step (`FixedWidth` + `.Step`)** on a
subvolume gives a uniform, directly-usable grid without the "points-per-axis ↔ mm" arithmetic that
the old `FixedNumber` recipe forced. Recommended step = **1–2 mm** (per the professional's advice).
This is the preferred B1+ export; it sidesteps the post-processing-template struggle entirely — you
export the raw H-field (or the registered B1+ node) and compute/plot everything in Python.

## When to use which node

- **B1+ node** (after `cst_calc_b1_field_tool`): export `2D/3D Results\B1+ and B1-\B1+ (f=0.21) [AC1]`
  — the scalar B1+ magnitude is already computed by CST; you just visualize it.
- **Raw H-field** (`h-field (f=0.21) [AC1]`): export the complex H components and compute
  `|B1+| = μ0·|Hx − i·Hy|/2` yourself with `scripts/compute_b1plus.py`. This is the most robust —
  it needs no B1+ tree node, only the AC-combined H-field.

## The macro (run via `cst_execute_vba_tool`, in-process — NEVER a standalone COM client)

`SelectTreeItem` path varies by CST version / task suffix, so try a **candidate list** and take the
first that selects without error. Write a log so you can confirm which path won and that `err=0`.

```vba
Sub Main
  Dim f As Integer
  f = FreeFile
  Open "C:\Users\admin\AppData\Local\Temp\b1_export.txt" For Output As #f
  On Error Resume Next
  Dim cands(5) As String
  cands(0) = "2D/3D Results\H-Field\h-field (f=0.21) [AC1]"
  cands(1) = "2D/3D Results\H-Field\h-field (f=0.21 GHz) [AC1]"
  cands(2) = "3D Results\H-Field\h-field (f=0.21) [AC1]"
  cands(3) = "3D Results\H-Field\h-field (f=0.21 GHz) [AC1]"
  cands(4) = "H-Field\h-field (f=0.21) [AC1]"
  cands(5) = "H-Field\h-field (f=0.21 GHz) [AC1]"
  Dim chosen As String
  chosen = ""
  Dim i As Integer
  For i = 0 To 5
    Err.Clear
    SelectTreeItem cands(i)
    If Err.Number = 0 Then
      chosen = cands(i)
      Print #f, "SELECTED OK: " & chosen
      Exit For
    Else
      Print #f, "fail[" & i & "]: " & cands(i) & " -> Err" & Err.Number
    End If
  Next i
  If chosen = "" Then
    Print #f, "NO FIELD NODE FOUND"
    Close #f
    Exit Sub
  End If
  Dim out As String
  out = "D:\ght\SAIS\MRI_agent\results\hfield_ac.h5"
  With ASCIIExport
    .Reset
    .SetfileType "hdf5"
    .FileName out
    .Mode "FixedWidth"
    .Step 1
    .UseSubvolume True
    .SetSubvolume -60, 60, -150, 150, -120.5, -20.5
    .ExportCoordinatesInMeter False
    .Execute
  End With
  Print #f, "EXPORT DONE err=" & Err.Number & " desc=" & Err.Description
  Print #f, "DONE"
  Close #f
End Sub
```

> One statement per line — do NOT use colon `:` multi-statement lines in VBA sent through the MCP
> (the interpreter rejects them). Adjust `out`, the `SetSubvolume` bbox (mm), and `.Step` (1 or 2 mm).

## ASCIIExport options that matter

| Option | Value | Why |
| --- | --- | --- |
| `.Reset` | — | **First**, always. Stale options (file type, subvolume) from a prior export leak otherwise. |
| `.SetfileType` | `"hdf5"` | HDF5 for the structured reader; `"ascii"` for plain text (`plot_field.py`). |
| `.Mode` | `"FixedWidth"` | Step = **physical width**. Pair with `.Step`. (`"FixedNumber"` makes Step = points/axis — avoid unless you specifically need a point count.) |
| `.Step` | `1` or `2` | Uniform grid spacing in **mm**. The professional's recommended B1+ resolution. |
| `.UseSubvolume` + `.SetSubvolume` | mm, `xmin,xmax,ymin,ymax,zmin,zmax` | Clip to ROI (phantom under the coil). Shrinks file + speeds the read. Omit both for a full-domain export. |
| `.ExportCoordinatesInMeter` | `False` | Keep coordinates in **mm** (model units). Default is meters → downstream ÷1000 confusion. |
| `.Execute` | — | **Required.** Without it: no file, no error. |

## Export traps (symptom → fix)

1. **`SelectTreeItem` fails on the first path** → the exact node path varies by version/task suffix.
   Iterate candidates (with/without `2D/3D Results\`, with/without ` GHz`); pick first `Err=0`.
2. **No file, no error** → forgot `.Execute`, or a stale option. `.Reset` first, set every option, `.Execute`, then check `Err.Number`.
3. **Coordinates ~0.001× expected** (0.06 not 60) → default meters. Set `.ExportCoordinatesInMeter False`.
4. **Huge file / slow read** → full-domain export. Add `.UseSubvolume True` + `.SetSubvolume` (mm).
5. **Can't read the temp log via PowerShell** → `Get-Content` may be policy-blocked. Read the `.txt` with the `Read` tool.
6. **`cst_list_results_tool` shows no 3D node** → it enumerates **1D only**. Confirm 3D field presence with a `SelectTreeItem` probe (or `cst.results ... get_3d().get_tree_items()` filtered for `AC1`), never with `cst_list_results_tool`.

## Verify checklist after the run

1. Log contains `SELECTED OK: <path>` → node found.
2. Log contains `EXPORT DONE err=0` → write succeeded.
3. File exists; `h5py` reads the field dataset + 3 `Mesh line *` arrays (HDF5), or `plot_field.py`
   loads the ASCII columns.
4. Peak value is sane and nonzero (dipole reference: peak |B1+| ≈ 1.9 µT @1W; peak |H| ≈ 2.47 A/m).
