#!/usr/bin/env python3
"""
plot_field.py — Visualize a CST ASCII-exported field as 2D plane maps + 1D line profiles.

Runs STANDALONE in the mri_agent conda env (numpy/scipy/matplotlib):
    python plot_field.py --input <field.txt> --outroot <results_dir> --name "B1+" [options]

Input: a CST `ASCIIExport` field file, columns:
    x y z  <c1Re c1Im> [<c2Re c2Im> <c3Re c3Im> ...]
Scalar fields (e.g. B1+) put the value in ONE component column (Bz: cols 8,9),
others zero. Vector fields populate all three complex components.

Outputs (into an AUTO-NAMED subfolder under --outroot):
  <name>_2D_profiles.png    coronal (X~c) + sagittal (Y~c) magnitude maps
  <name>_1D_profiles.png    line profiles along Y and Z through a fixed point,
                            optionally overlaid with a CST-native 1D curve (CSV)
  <name>_1D_alongY.csv      extracted 1D data (Y, value)
  <name>_1D_alongZ.csv      extracted 1D data (Z, value)
  stats.json                peak/mean/CV + file paths

Design intent: the ONE stable plotting helper. Recipes call it; we do not spawn
a new ad-hoc plotting script per task.
"""

import argparse
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.interpolate import griddata


def load_field(path):
    d = np.loadtxt(path, skiprows=2)
    return d[:, 0:3], d[:, 3:]


def field_magnitude(comp, mode, scale):
    ncomplex = comp.shape[1] // 2
    cvals = [comp[:, 2 * k] + 1j * comp[:, 2 * k + 1] for k in range(ncomplex)]
    if mode == "auto":
        idx = int(np.argmax([np.abs(c).sum() for c in cvals]))
        mag = np.abs(cvals[idx])
    elif mode == "vector":
        mag = np.sqrt(sum(np.abs(c) ** 2 for c in cvals))
    else:
        mag = np.abs(cvals[int(mode)])
    return mag * scale


def plane_slice(coords, vals, axis, center, half, grid_a, grid_b):
    a_idx, b_idx = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    ax_col = {"x": 0, "y": 1, "z": 2}[axis]
    sel = np.abs(coords[:, ax_col] - center) <= half
    A, B = np.meshgrid(grid_a, grid_b)
    Z = griddata((coords[sel, a_idx], coords[sel, b_idx]), vals[sel], (A, B), method="linear")
    return A, B, Z


def line_profile(coords, vals, along, fixed, half, grid):
    """Extract a 1D profile along one axis, other two axes fixed near `fixed`.

    along: "y" or "z"; fixed: dict of the two fixed axis centers, e.g. {"x":0,"z":-11}
    half: slab half-width (mm) for gathering nearby points; grid: sample positions.
    Returns (grid, interpolated values).
    """
    col = {"x": 0, "y": 1, "z": 2}[along]
    sel = np.ones(len(coords), dtype=bool)
    for ax, ctr in fixed.items():
        sel &= np.abs(coords[:, {"x": 0, "y": 1, "z": 2}[ax]] - ctr) <= half
    xs, ys = coords[sel, col], vals[sel]
    if xs.size < 2:
        return grid, np.full_like(grid, np.nan, dtype=float)
    order = np.argsort(xs)
    return grid, np.interp(grid, xs[order], ys[order], left=np.nan, right=np.nan)


def load_native_curve(path):
    """Load a CST-native 1D curve exported as CSV [axis, value]. Returns (x, y) or None."""
    if not path or not os.path.exists(path):
        return None
    try:
        d = np.loadtxt(path, delimiter=",")
        if d.ndim == 2 and d.shape[1] >= 2:
            return d[:, 0], d[:, 1]
    except Exception:
        try:
            d = np.loadtxt(path)
            if d.ndim == 2 and d.shape[1] >= 2:
                return d[:, 0], d[:, 1]
        except Exception:
            return None
    return None


def auto_subdir(outroot, name, tag):
    """Create results/<name>_<tag>_NN/ (NN increments to avoid clobber)."""
    safe = name.replace("+", "p").replace("/", "_").replace(" ", "_")
    base = f"{safe}_{tag}" if tag else safe
    n = 1
    while True:
        d = os.path.join(outroot, f"{base}_{n:02d}")
        if not os.path.exists(d):
            os.makedirs(d)
            return d
        n += 1
        if n > 999:
            os.makedirs(d, exist_ok=True)
            return d


def resolve_outdir(outroot, project, name, tag):
    """Resolve the output directory.

    If `project` is given, use a STABLE per-project folder
    `<outroot>/<project>/output/` that is reused across runs (final results
    are overwritten in place). Otherwise fall back to the legacy auto-named
    numbered subfolder (one new folder per run)."""
    if project:
        d = os.path.join(outroot, project, "output")
        os.makedirs(d, exist_ok=True)
        return d
    return auto_subdir(outroot, name, tag)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CST ASCII field export file")
    ap.add_argument("--outroot", required=True, help="results root")
    ap.add_argument("--project", default="", help="stable per-project id; writes to <outroot>/<project>/output/ (reused across runs). If omitted, a legacy auto-named numbered subfolder is created.")
    ap.add_argument("--name", default="field")
    ap.add_argument("--tag", default="", help="extra tag in the subfolder name (legacy mode only)")
    ap.add_argument("--unit", default="uT")
    ap.add_argument("--comp", default="auto", help="'auto' | 'vector' | component index")
    ap.add_argument("--scale", type=float, default=1e6)
    ap.add_argument("--roi", default="120,150,-150,80", help="xabs,yabs,zmin,zmax mm")
    ap.add_argument("--coronal-x", type=float, default=0.0)
    ap.add_argument("--sagittal-y", type=float, default=0.0)
    ap.add_argument("--slab", type=float, default=12.0)
    ap.add_argument("--core", default="60,80,-60,20", help="xabs,yabs,zmin,zmax mm for CV")
    # 1D line: fixed point the lines pass through (defaults to peak location if 'peak')
    ap.add_argument("--line-through", default="peak",
                    help="'peak' or 'x,y,z' mm — the point the 1D lines pass through")
    ap.add_argument("--native-y", default="", help="CSV of CST-native 1D curve along Y (for overlay)")
    ap.add_argument("--native-z", default="", help="CSV of CST-native 1D curve along Z (for overlay)")
    args = ap.parse_args()

    outdir = resolve_outdir(args.outroot, args.project, args.name, args.tag)

    xyz, comp = load_field(args.input)
    mag = field_magnitude(comp, args.comp, args.scale)

    xa, ya, zmin, zmax = [float(v) for v in args.roi.split(",")]
    roi = (np.abs(xyz[:, 0]) <= xa) & (np.abs(xyz[:, 1]) <= ya) & (xyz[:, 2] >= zmin) & (xyz[:, 2] <= zmax)
    c, v = xyz[roi], mag[roi]

    zi = np.linspace(zmin, zmax, 160)
    yi = np.linspace(-ya, ya, 160)
    xi = np.linspace(-xa, xa, 160)

    # ---- 2D maps ----
    Yc, Zc, Cc = plane_slice(c, v, "x", args.coronal_x, args.slab, yi, zi)
    Xs, Zs, Cs = plane_slice(c, v, "y", args.sagittal_y, args.slab, xi, zi)
    allv = np.concatenate([Cc[~np.isnan(Cc)], Cs[~np.isnan(Cs)]])
    vmax = float(np.nanpercentile(allv, 99)) if allv.size else 1.0

    fig, ax = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    im0 = ax[0].pcolormesh(Yc, Zc, Cc, shading="auto", cmap="turbo", vmin=0, vmax=vmax)
    ax[0].set_title(f"{args.name} Coronal (X~{args.coronal_x:g})")
    ax[0].set_xlabel("Y [mm]"); ax[0].set_ylabel("Z [mm]"); ax[0].set_aspect("equal")
    fig.colorbar(im0, ax=ax[0], label=f"|{args.name}| [{args.unit}]")
    im1 = ax[1].pcolormesh(Xs, Zs, Cs, shading="auto", cmap="turbo", vmin=0, vmax=vmax)
    ax[1].set_title(f"{args.name} Sagittal (Y~{args.sagittal_y:g})")
    ax[1].set_xlabel("X [mm]"); ax[1].set_ylabel("Z [mm]"); ax[1].set_aspect("equal")
    fig.colorbar(im1, ax=ax[1], label=f"|{args.name}| [{args.unit}]")
    fig.suptitle(f"{args.name} 2D profiles (MRI Agent, CST via MCP)", fontweight="bold")
    png2d = os.path.join(outdir, f"{args.name.replace('+','p')}_2D_profiles.png")
    fig.savefig(png2d, dpi=130)
    plt.close(fig)

    # ---- 1D line profiles ----
    if args.line_through == "peak":
        pk = int(np.argmax(v))
        px, py, pz = float(c[pk, 0]), float(c[pk, 1]), float(c[pk, 2])
    else:
        px, py, pz = [float(t) for t in args.line_through.split(",")]

    gy, vy = line_profile(c, v, "y", {"x": px, "z": pz}, args.slab, yi)
    gz, vz = line_profile(c, v, "z", {"x": px, "y": py}, args.slab, zi)

    np.savetxt(os.path.join(outdir, f"{args.name.replace('+','p')}_1D_alongY.csv"),
               np.column_stack([gy, vy]), delimiter=",", header="Y_mm,value", comments="")
    np.savetxt(os.path.join(outdir, f"{args.name.replace('+','p')}_1D_alongZ.csv"),
               np.column_stack([gz, vz]), delimiter=",", header="Z_mm,value", comments="")

    natY = load_native_curve(args.native_y)
    natZ = load_native_curve(args.native_z)

    fig2, ax2 = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    ax2[0].plot(gy, vy, "-", color="C0", lw=2, label="from field (extracted)")
    if natY is not None:
        ax2[0].plot(natY[0], natY[1], "--", color="C3", lw=1.5, label="CST template (native)")
    ax2[0].set_title(f"{args.name} along Y  (X={px:.0f}, Z={pz:.0f} mm)")
    ax2[0].set_xlabel("Y [mm]"); ax2[0].set_ylabel(f"|{args.name}| [{args.unit}]")
    ax2[0].set_ylim(bottom=0)
    ax2[0].grid(alpha=0.3); ax2[0].legend(fontsize=9)
    ax2[1].plot(gz, vz, "-", color="C0", lw=2, label="from field (extracted)")
    if natZ is not None:
        ax2[1].plot(natZ[0], natZ[1], "--", color="C3", lw=1.5, label="CST template (native)")
    ax2[1].set_title(f"{args.name} along Z  (X={px:.0f}, Y={py:.0f} mm)")
    ax2[1].set_xlabel("Z [mm]"); ax2[1].set_ylabel(f"|{args.name}| [{args.unit}]")
    ax2[1].set_ylim(bottom=0)
    ax2[1].grid(alpha=0.3); ax2[1].legend(fontsize=9)
    fig2.suptitle(f"{args.name} 1D line profiles (MRI Agent, CST via MCP)", fontweight="bold")
    png1d = os.path.join(outdir, f"{args.name.replace('+','p')}_1D_profiles.png")
    fig2.savefig(png1d, dpi=130)
    plt.close(fig2)

    # ---- stats ----
    cx, cy, czmin, czmax = [float(t) for t in args.core.split(",")]
    core = (np.abs(c[:, 0]) < cx) & (np.abs(c[:, 1]) < cy) & (c[:, 2] > czmin) & (c[:, 2] < czmax) & (v > 0)
    cc = v[core]
    stats = {
        "outdir": outdir,
        "png_2d": png2d,
        "png_1d": png1d,
        "line_through_xyz_mm": [px, py, pz],
        "roi_points": int(roi.sum()),
        "peak": float(v.max()) if v.size else None,
        "mean": float(v.mean()) if v.size else None,
        "unit": args.unit,
        "core_n": int(cc.size),
        "core_mean": float(cc.mean()) if cc.size else None,
        "core_cv_percent": float(100 * cc.std() / cc.mean()) if cc.size and cc.mean() else None,
        "native_overlay_y": bool(natY is not None),
        "native_overlay_z": bool(natZ is not None),
    }
    with open(os.path.join(outdir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
