#!/usr/bin/env python3
"""
plot_b1_profiles.py — High-fidelity B1+ visualization from targeted CST exports.

This replaces the single-coarse-export approach with a multi-export pipeline
that matches CST's native template output quality:
  1) 2D maps from dedicated plane exports (high-res coronal + sagittal)
  2) 1D profiles from a high-res thin-slab export (sub-mm Z resolution)

Input files (all CST ASCIIExport format: x y z Re1 Im1 Re2 Im2 Re3 Im3):
  --plane-yz <file>   Coronal plane export (thin X slab at X~0, high StepY/Z)
  --plane-xz <file>   Sagittal plane export (thin Y slab at Y~0, high StepX/Z)
  --slab-1d  <file>   High-res thin slab for 1D profiles (thin X slab, high StepY/Z)
                       Can be same file as --plane-yz if resolution is sufficient.

If only --input is given (single full-domain export), falls back to the old
coarse-grid behavior but with improved interpolation.

Usage (preferred, high-fidelity):
    python plot_b1_profiles.py \
        --plane-yz coronal.txt --plane-xz sagittal.txt --slab-1d hires_yz.txt \
        --outroot results --name "B1+" --tag dipole_scratch --unit uT --scale 1e6 \
        --line-z -30  --yrange -325,325  --zrange -50,1

Usage (fallback, single export):
    python plot_b1_profiles.py \
        --input field.txt --outroot results --name "B1+" --scale 141621.5
"""
import argparse, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.interpolate import RegularGridInterpolator


def load_field(path):
    """Load CST ASCII export. Returns (xyz[N,3], components[N,ncols])."""
    d = np.loadtxt(path, skiprows=2)
    return d[:, 0:3], d[:, 3:]


def compute_magnitude(comp, mode, scale):
    """Compute field magnitude from complex components."""
    ncomplex = comp.shape[1] // 2
    cvals = [comp[:, 2*k] + 1j * comp[:, 2*k+1] for k in range(ncomplex)]
    if mode == "auto":
        idx = int(np.argmax([np.abs(c).sum() for c in cvals]))
        mag = np.abs(cvals[idx])
    elif mode == "vector":
        mag = np.sqrt(sum(np.abs(c)**2 for c in cvals))
    else:
        mag = np.abs(cvals[int(mode)])
    return mag * scale


def build_regular_grid(xyz, mag):
    """Build a RegularGridInterpolator from uniformly-sampled data."""
    ux = np.unique(xyz[:, 0])
    uy = np.unique(xyz[:, 1])
    uz = np.unique(xyz[:, 2])
    nx, ny, nz = len(ux), len(uy), len(uz)

    if nx * ny * nz != len(mag):
        raise ValueError(f"Data is not a regular grid: {nx}*{ny}*{nz}={nx*ny*nz} != {len(mag)}")

    cube = np.full((nx, ny, nz), np.nan)
    xi_map = {v: i for i, v in enumerate(ux)}
    yi_map = {v: i for i, v in enumerate(uy)}
    zi_map = {v: i for i, v in enumerate(uz)}
    for (x, y, z), m in zip(xyz, mag):
        cube[xi_map[x], yi_map[y], zi_map[z]] = m

    interp = RegularGridInterpolator((ux, uy, uz), cube,
                                      bounds_error=False, fill_value=0.0)
    return interp, ux, uy, uz


def extract_plane(interp, axis, value, grid_a, grid_b):
    """Extract a 2D plane from the interpolator.
    axis='x' -> plane at X=value, returns (A=Y, B=Z) grid
    axis='y' -> plane at Y=value, returns (A=X, B=Z) grid
    """
    A, B = np.meshgrid(grid_a, grid_b, indexing='ij')
    if axis == 'x':
        pts = np.column_stack([np.full(A.size, value), A.ravel(), B.ravel()])
    elif axis == 'y':
        pts = np.column_stack([A.ravel(), np.full(A.size, value), B.ravel()])
    else:
        pts = np.column_stack([A.ravel(), B.ravel(), np.full(A.size, value)])
    return A, B, interp(pts).reshape(A.shape)


def extract_line(interp, along, fixed, grid):
    """Extract a 1D line profile.
    along='y': vary Y with X,Z fixed
    along='z': vary Z with X,Y fixed
    """
    n = len(grid)
    if along == 'y':
        pts = np.column_stack([np.full(n, fixed['x']), grid, np.full(n, fixed['z'])])
    elif along == 'z':
        pts = np.column_stack([np.full(n, fixed['x']), np.full(n, fixed['y']), grid])
    else:
        pts = np.column_stack([grid, np.full(n, fixed['y']), np.full(n, fixed['z'])])
    return interp(pts)


def auto_subdir(outroot, name, tag):
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
    """Stable per-project folder <outroot>/<project>/output/ (reused across
    runs) when `project` is given; else legacy auto-named numbered subfolder."""
    if project:
        d = os.path.join(outroot, project, "output")
        os.makedirs(d, exist_ok=True)
        return d
    return auto_subdir(outroot, name, tag)


def load_native_curve(path):
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
            pass
    return None


def main():
    ap = argparse.ArgumentParser(description="High-fidelity B1+ profile visualization")

    # Input sources (multi-export or single fallback)
    ap.add_argument("--plane-yz", default="", help="Coronal plane export (thin X slab)")
    ap.add_argument("--plane-xz", default="", help="Sagittal plane export (thin Y slab)")
    ap.add_argument("--slab-1d", default="", help="High-res slab for 1D (thin X, high Y/Z res)")
    ap.add_argument("--input", default="", help="Fallback: single full-domain export")

    # Output
    ap.add_argument("--outroot", required=True)
    ap.add_argument("--project", default="", help="stable per-project id; writes to <outroot>/<project>/output/ (reused across runs). If omitted, legacy auto-named subfolder.")
    ap.add_argument("--name", default="B1+")
    ap.add_argument("--tag", default="")
    ap.add_argument("--unit", default="uT")
    ap.add_argument("--comp", default="auto")
    ap.add_argument("--scale", type=float, default=1e6)

    # 1D profile control
    ap.add_argument("--line-x", type=float, default=0.0, help="X coord for 1D profiles")
    ap.add_argument("--line-y", type=float, default=0.0, help="Y coord for Z-profile")
    ap.add_argument("--line-z", type=float, default=-30.0,
                    help="Z coord for Y-profile (should be INSIDE phantom, e.g. -30)")
    ap.add_argument("--yrange", default="-325,325", help="Y range for profile")
    ap.add_argument("--zrange", default="-50,1", help="Z range for profile (shallow region)")
    ap.add_argument("--npts-1d", type=int, default=400, help="Number of points for 1D interpolation")

    # 2D map control
    ap.add_argument("--coronal-x", type=float, default=0.0)
    ap.add_argument("--sagittal-y", type=float, default=0.0)
    ap.add_argument("--map-yrange", default="", help="Y range for 2D map (default: from data)")
    ap.add_argument("--map-zrange", default="", help="Z range for 2D map (default: from data)")
    ap.add_argument("--npts-2d", type=int, default=200, help="Grid points per axis for 2D maps")

    # Native overlays
    ap.add_argument("--native-y", default="")
    ap.add_argument("--native-z", default="")

    # Stats ROI
    ap.add_argument("--roi", default="120,150,-150,80", help="xabs,yabs,zmin,zmax for stats")
    ap.add_argument("--core", default="60,80,-60,20", help="xabs,yabs,zmin,zmax for CV")

    args = ap.parse_args()
    outdir = resolve_outdir(args.outroot, args.project, args.name, args.tag)

    # Determine which mode we're in
    has_planes = bool(args.plane_yz) or bool(args.plane_xz)
    has_slab = bool(args.slab_1d)
    has_single = bool(args.input)

    if not has_planes and not has_slab and not has_single:
        raise SystemExit("ERROR: provide --plane-yz/--plane-xz/--slab-1d or --input")

    # ========== 2D MAPS ==========
    png2d = None
    if has_planes or has_single:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
        vmax_all = 0
        planes_data = []

        for idx, (src, axis, center, xlabel, ylabel, title_sfx) in enumerate([
            (args.plane_yz or args.input, 'x', args.coronal_x, "Y [mm]", "Z [mm]", "Coronal"),
            (args.plane_xz or args.input, 'y', args.sagittal_y, "X [mm]", "Z [mm]", "Sagittal"),
        ]):
            if not src or not os.path.exists(src):
                planes_data.append(None)
                continue
            xyz, comp = load_field(src)
            mag = compute_magnitude(comp, args.comp, args.scale)
            interp, ux, uy, uz = build_regular_grid(xyz, mag)

            if axis == 'x':
                if args.map_yrange:
                    a0, a1 = [float(v) for v in args.map_yrange.split(",")]
                else:
                    a0, a1 = uy.min(), uy.max()
                if args.map_zrange:
                    b0, b1 = [float(v) for v in args.map_zrange.split(",")]
                else:
                    b0, b1 = uz.min(), uz.max()
                ga = np.linspace(a0, a1, args.npts_2d)
                gb = np.linspace(b0, b1, args.npts_2d)
            else:  # axis == 'y'
                a0, a1 = ux.min(), ux.max()
                if args.map_zrange:
                    b0, b1 = [float(v) for v in args.map_zrange.split(",")]
                else:
                    b0, b1 = uz.min(), uz.max()
                ga = np.linspace(a0, a1, args.npts_2d)
                gb = np.linspace(b0, b1, args.npts_2d)

            A, B, C = extract_plane(interp, axis, center, ga, gb)
            planes_data.append((A, B, C, xlabel, ylabel, title_sfx))
            valid = C[C > 0]
            if valid.size:
                vmax_all = max(vmax_all, float(np.nanpercentile(valid, 99)))

        if vmax_all == 0:
            vmax_all = 1.0

        for idx, pd in enumerate(planes_data):
            if pd is None:
                continue
            A, B, C, xlabel, ylabel, title_sfx = pd
            im = axes[idx].pcolormesh(A, B, C, shading="auto", cmap="turbo",
                                       vmin=0, vmax=vmax_all)
            axes[idx].set_title(f"{args.name} {title_sfx}")
            axes[idx].set_xlabel(xlabel)
            axes[idx].set_ylabel(ylabel)
            axes[idx].set_aspect("equal")
            fig.colorbar(im, ax=axes[idx], label=f"|{args.name}| [{args.unit}]", shrink=0.8)

        fig.suptitle(f"{args.name} 2D profiles", fontweight="bold")
        png2d = os.path.join(outdir, f"{args.name.replace('+','p')}_2D_maps.png")
        fig.savefig(png2d, dpi=150)
        plt.close(fig)

    # ========== 1D PROFILES ==========
    png1d = None
    ymin_1d, ymax_1d = [float(v) for v in args.yrange.split(",")]
    zmin_1d, zmax_1d = [float(v) for v in args.zrange.split(",")]
    grid_y = np.linspace(ymin_1d, ymax_1d, args.npts_1d)
    grid_z = np.linspace(zmin_1d, zmax_1d, args.npts_1d)

    src_1d = args.slab_1d or args.plane_yz or args.input
    if src_1d and os.path.exists(src_1d):
        xyz, comp = load_field(src_1d)
        mag = compute_magnitude(comp, args.comp, args.scale)
        interp, ux, uy, uz = build_regular_grid(xyz, mag)

        # Y profile at (X=line_x, Z=line_z)
        vy = extract_line(interp, 'y', {'x': args.line_x, 'z': args.line_z}, grid_y)
        # Z profile at (X=line_x, Y=line_y)
        vz = extract_line(interp, 'z', {'x': args.line_x, 'y': args.line_y}, grid_z)

        # Save CSV
        np.savetxt(os.path.join(outdir, f"{args.name.replace('+','p')}_1D_alongY.csv"),
                   np.column_stack([grid_y, vy]), delimiter=",", header="Y_mm,value", comments="")
        np.savetxt(os.path.join(outdir, f"{args.name.replace('+','p')}_1D_alongZ.csv"),
                   np.column_stack([grid_z, vz]), delimiter=",", header="Z_mm,value", comments="")

        # Load native overlays
        natY = load_native_curve(args.native_y)
        natZ = load_native_curve(args.native_z)

        # Plot
        fig2, ax2 = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)

        ax2[0].plot(grid_y, vy, "-", color="C0", lw=2, label="from field export")
        if natY is not None:
            ax2[0].plot(natY[0], natY[1], "--", color="C3", lw=1.5, label="CST template (native)")
        ax2[0].set_title(f"{args.name} along Y  (X={args.line_x:.0f}, Z={args.line_z:.0f} mm)")
        ax2[0].set_xlabel("Y [mm]")
        ax2[0].set_ylabel(f"|{args.name}| [{args.unit}]")
        ax2[0].set_ylim(bottom=0)
        ax2[0].set_xlim(ymin_1d, ymax_1d)
        ax2[0].grid(alpha=0.3)
        ax2[0].legend(fontsize=9)

        ax2[1].plot(grid_z, vz, "-", color="C0", lw=2, label="from field export")
        if natZ is not None:
            ax2[1].plot(natZ[0], natZ[1], "--", color="C3", lw=1.5, label="CST template (native)")
        ax2[1].set_title(f"{args.name} along Z  (X={args.line_x:.0f}, Y={args.line_y:.0f} mm)")
        ax2[1].set_xlabel("Z [mm]")
        ax2[1].set_ylabel(f"|{args.name}| [{args.unit}]")
        ax2[1].set_ylim(bottom=0)
        ax2[1].set_xlim(zmin_1d, zmax_1d)
        ax2[1].grid(alpha=0.3)
        ax2[1].legend(fontsize=9)

        fig2.suptitle(f"{args.name} 1D line profiles", fontweight="bold")
        png1d = os.path.join(outdir, f"{args.name.replace('+','p')}_1D_profiles.png")
        fig2.savefig(png1d, dpi=150)
        plt.close(fig2)

        peak_y = float(np.nanmax(vy))
        peak_z = float(np.nanmax(vz))
    else:
        vy = vz = np.array([])
        peak_y = peak_z = None

    # ========== STATS ==========
    stats_src = args.input or args.slab_1d or args.plane_yz
    roi_stats = {}
    if stats_src and os.path.exists(stats_src):
        xyz_s, comp_s = load_field(stats_src)
        mag_s = compute_magnitude(comp_s, args.comp, args.scale)
        xa, ya, zmin_r, zmax_r = [float(v) for v in args.roi.split(",")]
        roi_mask = ((np.abs(xyz_s[:, 0]) <= xa) & (np.abs(xyz_s[:, 1]) <= ya) &
                    (xyz_s[:, 2] >= zmin_r) & (xyz_s[:, 2] <= zmax_r))
        v_roi = mag_s[roi_mask]
        cx, cy, czmin, czmax = [float(v) for v in args.core.split(",")]
        core_mask = ((np.abs(xyz_s[:, 0]) <= cx) & (np.abs(xyz_s[:, 1]) <= cy) &
                     (xyz_s[:, 2] >= czmin) & (xyz_s[:, 2] <= czmax) & (mag_s > 0))
        v_core = mag_s[core_mask]
        roi_stats = {
            "roi_points": int(roi_mask.sum()),
            "roi_peak": float(v_roi.max()) if v_roi.size else None,
            "roi_mean": float(v_roi.mean()) if v_roi.size else None,
            "core_n": int(v_core.size),
            "core_mean": float(v_core.mean()) if v_core.size else None,
            "core_cv_percent": float(100*v_core.std()/v_core.mean()) if v_core.size and v_core.mean() else None,
        }

    stats = {
        "outdir": outdir,
        "png_2d": png2d,
        "png_1d": png1d,
        "line_through": {"x": args.line_x, "y": args.line_y, "z": args.line_z},
        "profile_y_range": [ymin_1d, ymax_1d],
        "profile_z_range": [zmin_1d, zmax_1d],
        "peak_along_y": peak_y,
        "peak_along_z": peak_z,
        "unit": args.unit,
        "native_overlay_y": bool(load_native_curve(args.native_y)),
        "native_overlay_z": bool(load_native_curve(args.native_z)),
        "sources": {
            "plane_yz": args.plane_yz or None,
            "plane_xz": args.plane_xz or None,
            "slab_1d": args.slab_1d or None,
            "input_fallback": args.input or None,
        },
        **roi_stats,
    }
    with open(os.path.join(outdir, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
