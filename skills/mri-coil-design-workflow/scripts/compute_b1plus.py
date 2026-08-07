#!/usr/bin/env python3
"""
compute_b1plus.py — compute MRI transmit field |B1+| from a CST-exported H-field HDF5,
and visualize its three central orthogonal slices (x=const, y=const, z=const planes).

Pure Python (h5py + numpy + matplotlib), NO CST needed. Works on the HDF5 produced by the
field-export macro (SelectTreeItem + ASCIIExport, fileType=hdf5) in
`../building-blocks/vba-blocks/field-export.md`.

    |B1+| = mu0 * mu_r * |Hx + s*i*Hy| / 2      [Tesla]
    s = -1 when B0 is along +z (CST default, b0_plus_z=True), else s = +1.

This is the CP-transmit component, NOT |H|. It matches cst_calc_b1_field_tool's math
(Result3D.Combine + mu0*mu_r scaling + circular-polarization decomposition). Runs standalone
when you'd rather export the raw H-field and derive B1+ yourself than fight post-processing
templates.

KEY HDF5 FACTS (see ../building-blocks/vba-blocks/field-export.md — Post-Processing traps):
  f["H-Field"] is a STRUCTURED array, shape (Nz, Ny, Nx), FORTRAN order, dtype:
      [('x',[('re','<f4'),('im','<f4')]), ('y',...), ('z',...)]
  * It is NOT a group. Do NOT call .keys() on it (AttributeError).
  * component = f["H-Field"]["x"]["re"] + 1j*f["H-Field"]["x"]["im"]
  * reshape to (Nz, Ny, Nx) with order="F" (order="C" scrambles the field).
  * "Mesh line x/y/z" are plain 1D arrays; unit = mm when ExportCoordinatesInMeter False.

Usage: edit CONFIG below, then  python compute_b1plus.py
"""
import os
import sys
import json
import numpy as np
import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def L(msg):
    try:
        print(str(msg))
    except UnicodeEncodeError:
        print(str(msg).encode("ascii", "replace").decode("ascii"))
    sys.stdout.flush()


# ============================== CONFIG =====================================
H5_FILE   = r"hfield_ac.h5"                 # output of the field-export macro
OUT_DIR   = r"."                            # where to write the 3 PNGs
FIELD_NAME = "H-Field"                      # CST HDF5 dataset name (E-field -> "E-Field")
# Geometric center for slice selection, in mesh units (mm). Use the model's true
# center; (0,0,0) only if the model is centered at origin.
CENTER = (0.0, 0.0, 0.0)
MU0 = 4.0 * np.pi * 1e-7                    # H/m
MU_R = 1.0                                  # tissue ~1; B = mu0*mu_r*H
# B0 direction. True = +z (CST default) -> B1+ uses (Hx - i*Hy)/2.
# Must match the cst_calc_b1_field_tool(b0_plus_z=...) used upstream, or B1+/B1- swap.
B0_PLUS_Z = True
# Analysis ROI in Z (mm). Peak-finding + stats are restricted to this range so the
# PEC near-field singularity at the conductor (z~0) does not hijack the anchor.
# Set ROI_ZMAX to the phantom top (just below the coil). None = no restriction.
# Plotting always uses the full exported window regardless of these.
ROI_ZMIN = None
ROI_ZMAX = None
# "abs"  -> |B1+| in microtesla (uT)
# "norm" -> |B1+| normalized to global max (0..1)
PLOT_MODE = "abs"
# Optional power normalization: peak/mean are reported at the AC excitation power.
# To normalize to 1 W set SCALE_TO_1W and P_ACCEPTED_W (peak *= 1/sqrt(P_accepted/1W)).
SCALE_TO_1W = False
P_ACCEPTED_W = 49.86                        # dipole reference accepted power
CMAP = "plasma"
# ==========================================================================


def load_field(h5):
    """Return (mx, my, mz, Hx, Hy, Hz): 1D coord arrays + complex 3D arrays (Nz,Ny,Nx)."""
    for k in ("Mesh line x", "Mesh line y", "Mesh line z"):
        if k not in h5:
            raise KeyError("Missing %r in HDF5. Available keys: %s" % (k, list(h5.keys())))
    mx = np.asarray(h5["Mesh line x"]).ravel()
    my = np.asarray(h5["Mesh line y"]).ravel()
    mz = np.asarray(h5["Mesh line z"]).ravel()
    L("mesh sizes: X=%d Y=%d Z=%d" % (mx.size, my.size, mz.size))

    fld = h5[FIELD_NAME]
    # Structured array: fld["x"]["re"], fld["x"]["im"], ... ; (Nz, Ny, Nx) Fortran order.
    def comp3d(sub):
        re = np.asarray(fld[sub]["re"], dtype=np.float64)
        im = np.asarray(fld[sub]["im"], dtype=np.float64)
        c = re + 1j * im
        return c.reshape((mz.size, my.size, mx.size), order="F")

    return mx, my, mz, comp3d("x"), comp3d("y"), comp3d("z")


def compute_b1plus(Hx, Hy):
    """|B1+| = mu0*mu_r*|Hx + s*i*Hy|/2 (Tesla). s=-1 for B0 along +z (CST default)."""
    s = -1.0 if B0_PLUS_Z else 1.0
    b1p = (Hx + s * 1j * Hy) / 2.0
    return MU0 * MU_R * np.abs(b1p)


def nearest_index(coord, target):
    return int(np.argmin(np.abs(coord - target)))


def plot_2d_maps(b1, mx, my, mz, ix, iy, iz, fname, sag_zrange=None, vmax=None):
    """2D panel figure (both panels use Y as the horizontal axis):
      - coronal : XY plane at the peak Z slice — horiz=Y, vert=X, full XY range.
      - sagittal: YZ plane at the peak X slice — horiz=Y, vert=Z, Z clipped to sag_zrange
                  (e.g. the phantom, excluding the PCB/coil layer).
    sag_zrange = (zmin, zmax) mm for the sagittal Z axis.
    vmax = explicit color-scale top in uT (default: 99th percentile of the phantom data,
    which keeps the distribution shape readable and lets the hot core saturate slightly)."""
    coronal = b1[iz, :, :] * 1e6    # (Ny, Nx) at fixed Z -> XY plane
    sagittal = b1[:, :, ix] * 1e6   # (Nz, Ny) at fixed X -> YZ plane
    if vmax is None:
        vmax = 1.0   # fixed 0-1.0 uT color scale with clear ticks
    cbar_ticks = np.linspace(0, vmax, 6) if abs(vmax - 1.0) < 1e-9 else None
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    # Coronal: XY plane. horiz=Y (my), vert=X (mx). C shape must be (Nx, Ny) -> transpose.
    im0 = axes[0].pcolormesh(my, mx, coronal.T, shading="auto", cmap="turbo", vmin=0, vmax=vmax)
    axes[0].set_title("|B1+| coronal (Z=%.0f mm)" % mz[iz])
    axes[0].set_xlabel("Y [mm]"); axes[0].set_ylabel("X [mm]"); axes[0].set_aspect("equal")
    fig.colorbar(im0, ax=axes[0], label="|B1+| [uT]", shrink=0.8, ticks=cbar_ticks)
    # Sagittal: YZ plane. horiz=Y (my), vert=Z (mz). C shape (Nz, Ny).
    im1 = axes[1].pcolormesh(my, mz, sagittal, shading="auto", cmap="turbo", vmin=0, vmax=vmax)
    axes[1].set_title("|B1+| sagittal (X=%.0f mm)" % mx[ix])
    axes[1].set_xlabel("Y [mm]"); axes[1].set_ylabel("Z [mm]"); axes[1].set_aspect("equal")
    if sag_zrange is not None:
        axes[1].set_ylim(sag_zrange)
    fig.colorbar(im1, ax=axes[1], label="|B1+| [uT]", shrink=0.8, ticks=cbar_ticks)
    fig.suptitle("B1+ 2D profiles", fontweight="bold")
    fig.savefig(fname, dpi=150)
    plt.close(fig)


def plot_1d_profiles(my, mz, line_y, line_z, px_mm, py_mm, pz_mm, fname,
                     y_xrange=None, z_xrange=None):
    """Reference-format 1D curve panel figure: |B1+| along Y and along Z through the peak, side by side.
    y_xrange/z_xrange = (min,max) mm to clip each curve's abscissa (e.g. z clipped to the
    phantom so the PEC near-field spike at z~0 does not dominate the Z curve)."""
    fig, ax = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    # Y curve (optionally clipped in Y)
    my_p, ly_p = my, line_y
    if y_xrange is not None:
        m = (my >= y_xrange[0]) & (my <= y_xrange[1])
        my_p, ly_p = my[m], line_y[m]
    ax[0].plot(my_p, ly_p, "-", color="C0", lw=2)
    ax[0].set_title("B1+ along Y  (X=%.0f, Z=%.0f mm)" % (px_mm, pz_mm))
    ax[0].set_xlabel("Y [mm]"); ax[0].set_ylabel("|B1+| [uT]")
    ax[0].set_ylim(bottom=0); ax[0].grid(alpha=0.3)
    if y_xrange is not None:
        ax[0].set_xlim(y_xrange)
    # Z curve (clip to phantom to drop the conductor near-field spike)
    mz_p, lz_p = mz, line_z
    if z_xrange is not None:
        m = (mz >= z_xrange[0]) & (mz <= z_xrange[1])
        mz_p, lz_p = mz[m], line_z[m]
    ax[1].plot(mz_p, lz_p, "-", color="C0", lw=2)
    ax[1].set_title("B1+ along Z  (X=%.0f, Y=%.0f mm)" % (px_mm, py_mm))
    ax[1].set_xlabel("Z [mm]"); ax[1].set_ylabel("|B1+| [uT]")
    ax[1].set_ylim(bottom=0); ax[1].grid(alpha=0.3)
    # give the Z curve breathing room so its ends don't touch the axes
    zlo, zhi = (z_xrange if z_xrange is not None else (float(mz_p.min()), float(mz_p.max())))
    zpad = 0.05 * (zhi - zlo)
    ax[1].set_xlim(zlo - zpad, zhi + zpad)
    fig.suptitle("B1+ 1D line profiles", fontweight="bold")
    fig.savefig(fname, dpi=150)
    plt.close(fig)


def plot_slice(b1, mx, my, mz, axis, idx, fname, mode):
    """Plot a central slice of |B1+| (b1 shaped (Nz, Ny, Nx)).
    axis 0 -> x plane (yz) via b1[:,:,ix]
    axis 1 -> y plane (xz) via b1[:,iy,:]
    axis 2 -> z plane (xy) via b1[iz,:,:]"""
    if axis == 0:
        data = b1[:, :, idx]; X, Y = my, mz; xlab, ylab = "y", "z"
    elif axis == 1:
        data = b1[:, idx, :]; X, Y = mx, mz; xlab, ylab = "x", "z"
    else:
        data = b1[idx, :, :]; X, Y = mx, my; xlab, ylab = "x", "y"

    if mode == "norm":
        gmax = b1.max()
        data = data / gmax if gmax > 0 else data
        unit, title = "a.u.", "|B1+| / max (normalized)"
    else:
        data = data * 1e6
        unit, title = "uT", "|B1+| (uT)"

    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    im = ax.imshow(data.T, origin="lower",
                   extent=[X.min(), X.max(), Y.min(), Y.max()],
                   aspect="equal", cmap=CMAP)
    cb = fig.colorbar(im, ax=ax)
    cb.set_label(unit)
    ax.set_xlabel("%s (mm)" % xlab)
    ax.set_ylabel("%s (mm)" % ylab)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(fname, dpi=150)
    plt.close(fig)


def main():
    # Optional CLI overrides so the per-project output folder can be targeted
    # without editing the CONFIG block each run. All are optional; if omitted
    # the CONFIG values above are used.
    import argparse
    global H5_FILE, OUT_DIR, B0_PLUS_Z, SCALE_TO_1W, P_ACCEPTED_W, ROI_ZMIN, ROI_ZMAX
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5", default=None, help="HDF5 H-field export (overrides H5_FILE)")
    ap.add_argument("--outroot", default=None, help="results root (used with --project)")
    ap.add_argument("--project", default=None, help="stable per-project id; writes to <outroot>/<project>/output/")
    ap.add_argument("--out-dir", default=None, help="explicit output dir (overrides OUT_DIR/--project)")
    ap.add_argument("--b0-plus-z", dest="b0", action="store_true", default=None)
    ap.add_argument("--b0-minus-z", dest="b0", action="store_false")
    ap.add_argument("--norm-1w", dest="norm1w", action="store_true", default=None,
                    help="normalize |B1+| to 1 W accepted power (peak *= 1/sqrt(P_accepted))")
    ap.add_argument("--p-accepted", type=float, default=None,
                    help="accepted power in W at the AC excitation (measure via 0.5*Re(V*conj(I)) at the port); used with --norm-1w")
    ap.add_argument("--roi-zmax", type=float, default=None,
                    help="restrict peak-finding/stats to z <= this (mm); set to the phantom top to avoid the PEC near-field spike. Plotting still uses the full window.")
    ap.add_argument("--roi-zmin", type=float, default=None,
                    help="restrict peak-finding/stats to z >= this (mm)")
    ap.add_argument("--sag-zrange", default=None,
                    help="sagittal panel Z display range 'zmin,zmax' mm (e.g. -100,-24 to show only phantom, exclude PCB)")
    ap.add_argument("--cor-zrange", default=None,
                    help="coronal panel Z display range 'zmin,zmax' mm (default: full)")
    args, _ = ap.parse_known_args()
    if args.roi_zmax is not None:
        ROI_ZMAX = args.roi_zmax
    if args.roi_zmin is not None:
        ROI_ZMIN = args.roi_zmin
    sag_zrange = tuple(float(v) for v in args.sag_zrange.split(",")) if args.sag_zrange else None
    cor_zrange = tuple(float(v) for v in args.cor_zrange.split(",")) if args.cor_zrange else None
    if args.h5:
        H5_FILE = args.h5
    if args.out_dir:
        OUT_DIR = args.out_dir
    elif args.project and args.outroot:
        OUT_DIR = os.path.join(args.outroot, args.project, "output")
    if args.b0 is not None:
        B0_PLUS_Z = args.b0
    if args.p_accepted is not None:
        P_ACCEPTED_W = args.p_accepted
    if args.norm1w is not None:
        SCALE_TO_1W = args.norm1w

    if not os.path.exists(H5_FILE):
        raise FileNotFoundError("HDF5 not found: %s\nRun the field-export macro first." % H5_FILE)
    os.makedirs(OUT_DIR, exist_ok=True)

    with h5py.File(H5_FILE, "r") as h5:
        L("HDF5 keys: %s" % list(h5.keys()))
        mx, my, mz, Hx, Hy, Hz = load_field(h5)

    b1 = compute_b1plus(Hx, Hy)

    scale = 1.0
    if SCALE_TO_1W and P_ACCEPTED_W > 0:
        scale = 1.0 / np.sqrt(P_ACCEPTED_W / 1.0)
        b1 = b1 * scale
        L("Normalized to 1 W: scale=%.4g (P_accepted=%.3f W)" % (scale, P_ACCEPTED_W))

    gmax_full = b1.max()
    L("Global max |B1+| (whole export) = %.4f uT" % (gmax_full * 1e6))

    # Analysis ROI: restrict peak-finding + stats to inside the phantom so the
    # near-field singularity at the PEC conductor edge (just above/at the coil,
    # z~0) does NOT hijack the anchor. Plotting still uses the full window.
    # roi_zmax defaults to the phantom top (a bit below the coil).
    roi_mask = np.ones_like(b1, dtype=bool)
    if ROI_ZMAX is not None:
        roi_mask &= (mz[:, None, None] <= ROI_ZMAX)
    if ROI_ZMIN is not None:
        roi_mask &= (mz[:, None, None] >= ROI_ZMIN)
    b1_roi = np.where(roi_mask, b1, 0.0)
    gmax = b1_roi.max()
    L("Peak |B1+| inside analysis ROI (z<=%s) = %.4f uT" % (str(ROI_ZMAX), gmax * 1e6))

    # Anchor slices/lines on the ROI-peak voxel (like the reference case)
    pz, py, px = np.unravel_index(int(np.argmax(b1_roi)), b1.shape)
    L("Peak voxel: x=%.2f@%d  y=%.2f@%d  z=%.2f@%d"
      % (mx[px], px, my[py], py, mz[pz], pz))

    # Reference-format deliverables: ONE 2D panel figure (coronal+sagittal) + ONE 1D curve panel figure (Y+Z)
    plot_2d_maps(b1, mx, my, mz, px, py, pz, os.path.join(OUT_DIR, "B1p_2D_maps.png"),
                 sag_zrange=sag_zrange)
    line_y = b1[pz, :, px] * 1e6   # vary Y at fixed X,Z (through peak)
    line_z = b1[:, py, px] * 1e6   # vary Z at fixed X,Y (through peak)
    plot_1d_profiles(my, mz, line_y, line_z, mx[px], my[py], mz[pz],
                     os.path.join(OUT_DIR, "B1p_1D_profiles.png"),
                     z_xrange=sag_zrange)
    L("Saved B1p_2D_maps.png + B1p_1D_profiles.png to %s" % OUT_DIR)

    central = b1[pz, :, :]
    mean = central.mean()
    cv = central.std() / mean if mean > 0 else float("nan")
    L("Peak-Z xy-slice: mean=%.4f uT, std=%.4f uT, CV=%.3f"
      % (mean * 1e6, central.std() * 1e6, cv))

    # 1D profile CSVs (through the peak)
    np.savetxt(os.path.join(OUT_DIR, "B1p_1D_alongY.csv"),
               np.column_stack([my, line_y]), delimiter=",",
               header="Y_mm,B1plus_uT", comments="")
    np.savetxt(os.path.join(OUT_DIR, "B1p_1D_alongZ.csv"),
               np.column_stack([mz, line_z]), delimiter=",",
               header="Z_mm,B1plus_uT", comments="")

    stats = {
        "h5_file": H5_FILE,
        "out_dir": OUT_DIR,
        "normalized_to_1W": bool(SCALE_TO_1W),
        "p_accepted_W": P_ACCEPTED_W if SCALE_TO_1W else None,
        "b0_plus_z": bool(B0_PLUS_Z),
        "mu_r": MU_R,
        "peak_uT": float(gmax * 1e6),
        "peak_uT_whole_export": float(gmax_full * 1e6),
        "roi_zmin_mm": ROI_ZMIN,
        "roi_zmax_mm": ROI_ZMAX,
        "peak_xyz_mm": [float(mx[px]), float(my[py]), float(mz[pz])],
        "central_slice_z_mm": float(mz[pz]),
        "central_mean_uT": float(mean * 1e6),
        "central_std_uT": float(central.std() * 1e6),
        "central_cv": float(cv),
        "unit": "uT",
    }
    with open(os.path.join(OUT_DIR, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    L("Wrote stats.json + 1D CSVs (alongY, alongZ) to %s" % OUT_DIR)
    L("DONE.")


if __name__ == "__main__":
    main()
