#!/usr/bin/env python3
"""
plan_export_box.py — Adaptive B1+ field-export box + step, derived from geometry.

Given the model bounding boxes (phantom = imaging ROI, coil = field source), compute
a sensible ASCIIExport SetSubvolume box and a step (1 or 2 mm) that keeps the point
count reasonable. Prints a JSON plan the caller feeds into the export macro.

Rule (physics-motivated, coil-agnostic):
  X, Y  -> phantom full extent, but clamped to +/- `xy_halfwin` so a very long phantom
           doesn't produce a mostly-empty, extremely wide figure (matches the textbook
           reference display window). Default xy_halfwin = 160 mm.
  Z     -> from (coil_zmax + margin_up) down to (phantom_top - depth). This spans the
           air just above the coil through the useful depth into the phantom, matching
           the reference Z window (~-150 .. +80 mm). margin_up=80, depth=140 by default.
  step  -> adaptive: 1 mm if max points/axis <= max_pts (default 300), else 2 mm.

Usage:
  python plan_export_box.py \
      --phantom -135 135 -325 325 -320.5 -20.5 \
      --coil    -2.5 2.5 -150 150 0 0.35 \
      [--xy-halfwin 160] [--margin-up 80] [--depth 140] [--max-pts 300]
"""
import argparse
import json


def plan(phantom, coil, xy_halfwin, margin_up, depth, max_pts):
    pxmin, pxmax, pymin, pymax, pzmin, pzmax = phantom
    _, _, _, _, _, czmax = coil

    # X / Y: phantom extent, clamped to the display half-window.
    xmin = max(pxmin, -xy_halfwin)
    xmax = min(pxmax, xy_halfwin)
    ymin = max(pymin, -xy_halfwin)
    ymax = min(pymax, xy_halfwin)

    # Z: air above the coil down to a useful depth into the phantom.
    phantom_top = pzmax          # phantom's shallowest face (closest to coil)
    zmax = czmax + margin_up     # a margin above the coil
    zmin = phantom_top - depth   # `depth` mm into the phantom from its top

    spans = [xmax - xmin, ymax - ymin, zmax - zmin]
    step = 1 if (max(spans) / 1.0) <= max_pts else 2
    npts = [int(round(s / step)) + 1 for s in spans]

    return {
        "box_mm": [round(xmin, 3), round(xmax, 3),
                   round(ymin, 3), round(ymax, 3),
                   round(zmin, 3), round(zmax, 3)],
        "step_mm": step,
        "approx_points_per_axis": npts,
        "approx_total_points": npts[0] * npts[1] * npts[2],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phantom", nargs=6, type=float, required=True,
                    metavar=("XMIN", "XMAX", "YMIN", "YMAX", "ZMIN", "ZMAX"),
                    help="phantom bounding box in mm")
    ap.add_argument("--coil", nargs=6, type=float, required=True,
                    metavar=("XMIN", "XMAX", "YMIN", "YMAX", "ZMIN", "ZMAX"),
                    help="coil/dipole bounding box in mm")
    ap.add_argument("--xy-halfwin", type=float, default=160.0)
    ap.add_argument("--margin-up", type=float, default=80.0)
    ap.add_argument("--depth", type=float, default=140.0)
    ap.add_argument("--max-pts", type=int, default=300)
    args = ap.parse_args()
    result = plan(args.phantom, args.coil, args.xy_halfwin,
                  args.margin_up, args.depth, args.max_pts)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
