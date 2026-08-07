#!/usr/bin/env python3
"""Extract and plot the complete Raaijmakers 2016 Fig. 3/4 reproduction."""

from __future__ import annotations

import argparse
import csv
import json
import math
from io import BytesIO
from pathlib import Path

import h5py
import numpy as np

from paper_fractionated_dipole_live import longitudinal_export_y_half_mm


MU0 = 4.0e-7 * math.pi
DEPTHS_CM = (5, 10, 15)


def _load_hfield(path: Path, p_accepted: float):
    with h5py.File(path, "r") as h5:
        x = np.asarray(h5["Mesh line x"]).ravel()
        y = np.asarray(h5["Mesh line y"]).ravel()
        z = np.asarray(h5["Mesh line z"]).ravel()
        field = h5["H-Field"]

        def component(name):
            re = np.asarray(field[name]["re"], dtype=float)
            im = np.asarray(field[name]["im"], dtype=float)
            return (re + 1j * im).reshape((z.size, y.size, x.size), order="F")

        hx, hy = component("x"), component("y")
    b1 = MU0 * np.abs(hx - 1j * hy) / 2.0 * 1e6 / math.sqrt(p_accepted)
    return x, y, z, b1


def _load_sar(path: Path, p_accepted: float):
    with h5py.File(path, "r") as h5:
        x = np.asarray(h5["Mesh line x"]).ravel()
        y = np.asarray(h5["Mesh line y"]).ravel()
        z = np.asarray(h5["Mesh line z"]).ravel()
        sar = np.asarray(h5["SAR"], dtype=float) / p_accepted
    return x, y, z, sar


def _assert_longitudinal_coverage(y, length_mm: float, source: Path | str) -> None:
    """Reject a field/profile clipped to the conductor instead of the phantom ROI."""
    y = np.asarray(y, dtype=float).ravel()
    if y.size < 2 or not np.all(np.isfinite(y)):
        raise ValueError(f"invalid longitudinal coordinate array in {source}")
    required = longitudinal_export_y_half_mm(length_mm)
    spacing = float(np.median(np.diff(np.unique(np.sort(y)))))
    tolerance = max(abs(spacing) * 0.51, 1.0e-6)
    actual_min, actual_max = float(y.min()), float(y.max())
    if actual_min > -required + tolerance or actual_max < required - tolerance:
        raise ValueError(
            "longitudinal SAR coverage is truncated: "
            f"{source} spans [{actual_min:g}, {actual_max:g}] mm, but "
            f"L={float(length_mm):g} mm requires at least "
            f"[-{required:g}, {required:g}] mm "
            "(160 mm through L=300 mm; L/2+15 mm above 300 mm). "
            "Re-export the H/SAR case; "
            "do not plot this profile."
        )


def _upsert_csv(path: Path, row: dict, key: str, sort_key: str) -> None:
    rows = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as stream:
            rows = [item for item in csv.DictReader(stream) if item[key] != str(row[key])]
    rows.append({name: str(value) for name, value in row.items()})
    rows.sort(key=lambda item: float(item[sort_key]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerows(rows)


def _canonical_fig4_element(value) -> str:
    """Normalize supported Fig. 4 element names to the CSV plotting contract.

    Older/reference summaries use ``C``/``L`` while some live runners emitted
    the descriptive names ``capacitor``/``inductor``.  Accept both spellings,
    but fail loudly for an unknown value so panels (a)/(d) cannot silently lose
    every loaded curve.
    """
    key = str(value).strip().lower()
    aliases = {
        "c": "C",
        "cap": "C",
        "capacitor": "C",
        "l": "L",
        "ind": "L",
        "inductor": "L",
        "plain": "plain",
    }
    if key not in aliases:
        raise ValueError(
            f"unsupported Fig. 4 element {value!r}; expected "
            "C/capacitor, L/inductor, or plain"
        )
    return aliases[key]


def extract_case(args) -> dict:
    pacc = float(args.p_accepted)
    if not math.isfinite(pacc) or pacc <= 0.0:
        raise ValueError(f"p_accepted must be finite and > 0 W, got {pacc!r}")
    x, y, z, b1 = _load_hfield(Path(args.hfield), pacc)
    sx, sy, sz, sar = _load_sar(Path(args.sar), pacc)
    _assert_longitudinal_coverage(sy, args.length_mm, Path(args.sar))
    ix = int(np.argmin(abs(x)))
    iy = int(np.argmin(abs(y)))
    inside = z <= 0
    line_z = z[inside]
    line_b1 = b1[inside, iy, ix]
    order = np.argsort(line_z)
    line_z, line_b1 = line_z[order], line_b1[order]
    b1_depth = {
        depth: float(b1[int(np.argmin(abs(z + depth * 10))), iy, ix])
        for depth in DEPTHS_CM
    }
    sarmax = float(sar.max())
    iz, _, ixs = np.unravel_index(int(np.argmax(sar)), sar.shape)
    sar_line = sar[iz, :, ixs]
    imax = int(np.argmax(sar_line))
    icenter = int(np.argmin(abs(sy)))
    y_max = float(sy[imax])
    center_ratio = float(sar_line[icenter] / sar_line[imax])
    # Merge grid-scale duplicates of a flat central cap.  The 300 mm baseline
    # has equal maxima at y=+/-1 mm (one physical peak), while the 50 mm case
    # has resolved lobes near +/-8 mm and the 150 nH case is much wider still.
    candidates = []
    threshold = 0.5 * sar_line.max()
    for index in range(1, len(sar_line) - 1):
        if (
            sar_line[index] > threshold
            and sar_line[index] >= sar_line[index - 1]
            and sar_line[index] >= sar_line[index + 1]
        ):
            candidates.append(float(sy[index]))
    clusters = []
    for position in candidates:
        if not clusters or position - clusters[-1][-1] > 8.0:
            clusters.append([position])
        else:
            clusters[-1].append(position)
    double_peak = len(clusters) >= 2
    shape = "double_offcenter_peak" if double_peak else "central_single_peak"
    fom = {depth: b1_depth[depth] / math.sqrt(sarmax) for depth in DEPTHS_CM}

    profiles = Path(args.profile_dir)
    profiles.mkdir(parents=True, exist_ok=True)
    prefix = "len_" + str(int(round(args.length_mm))) + "mm" if args.kind == "length" else "seg_" + args.case_id
    with (profiles / f"b1p_indepth_{prefix}.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["z_mm", "B1p_uT_per_sqrtW_1Wacc"])
        writer.writerows(zip(line_z, line_b1))
    with (profiles / f"sar_alongY_{prefix}.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["y_mm", "SAR10g_Wkg_1Wacc", "z_slice_mm"])
        writer.writerows((yy, value, sz[iz]) for yy, value in zip(sy, sar_line))

    common = {
        "P_acc_W": round(pacc, 9),
        "peak_B1p_uT": round(float(b1[inside].max()), 6),
        **{f"B1p_d{d}cm_uT": round(b1_depth[d], 6) for d in DEPTHS_CM},
        "SARmax_Wkg": round(sarmax, 6),
        **{f"FoM_d{d}cm": round(fom[d], 6) for d in DEPTHS_CM},
        "SAR_shape": shape,
        "sar_ymax_mm": round(y_max, 3),
        "sar_center_ratio": round(center_ratio, 6),
        "sar_peak_clusters": len(clusters),
    }
    if args.kind == "length":
        row = {"len_mm": int(round(args.length_mm)), **common}
        _upsert_csv(Path(args.summary), row, "len_mm", "len_mm")
    else:
        row = {
            "tag": args.case_id,
            "Z_seg_ohm": round(args.reactance_ohm, 6),
            "element": _canonical_fig4_element(args.element),
            "value": args.value,
            **common,
        }
        _upsert_csv(Path(args.summary), row, "tag", "Z_seg_ohm")
    print(json.dumps(row))
    return row


def _read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _read_profile(path: Path):
    return np.loadtxt(path, delimiter=",", skiprows=1)


def _is_plain_segment_row(row) -> bool:
    return _canonical_fig4_element(row["element"]) == "plain"


def _fig4_display_subset_label(row):
    """Return the paper-panel label for a displayed Fig. 4 subset row.

    Case IDs are intentionally not part of this contract: live/demo runners may
    use descriptive IDs, while the physical element and value columns are the
    stable interface shared by extraction and plotting.
    """
    if _is_plain_segment_row(row):
        return "plain"
    element = _canonical_fig4_element(row["element"])
    value = float(row["value"])
    displayed = {"C": (1.0, 5.0), "L": (50.0, 100.0, 150.0)}
    if element not in displayed or not any(math.isclose(value, target) for target in displayed[element]):
        return None
    unit = "pF" if element == "C" else "nH"
    return f"{value:g} {unit}"


def plot_fig3(args) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = sorted(_read_rows(Path(args.summary)), key=lambda row: float(row["len_mm"]))
    profiles = Path(args.profile_dir)
    lengths = np.array([float(row["len_mm"]) for row in rows])
    reference = min(rows, key=lambda row: abs(float(row["len_mm"]) - 250))
    ref_b1 = _read_profile(profiles / "b1p_indepth_len_250mm.csv")
    ref_fom = ref_b1[:, 1] / math.sqrt(float(reference["SARmax_Wkg"]))
    colors = plt.cm.viridis(np.linspace(0, 1, len(rows)))
    fig, ax = plt.subplots(2, 3, figsize=(18, 10.5))
    for row, color in zip(rows, colors):
        length = int(float(row["len_mm"]))
        b = _read_profile(profiles / f"b1p_indepth_len_{length}mm.csv")
        s = _read_profile(profiles / f"sar_alongY_len_{length}mm.csv")
        _assert_longitudinal_coverage(
            s[:, 0], length, profiles / f"sar_alongY_len_{length}mm.csv"
        )
        depth = -b[:, 0] / 10
        order = np.argsort(depth)
        depth, values = depth[order], b[:, 1][order]
        ref_values = np.interp(depth, -ref_b1[:, 0][::-1] / 10, ref_b1[:, 1][::-1])
        fom_values = values / math.sqrt(float(row["SARmax_Wkg"]))
        ref_fom_values = np.interp(depth, -ref_b1[:, 0][::-1] / 10, ref_fom[::-1])
        label = f"{length/10:g} cm"
        ax[0, 0].plot(depth, values, color=color, label=label)
        ax[0, 1].plot(depth, values / ref_values, color=color, label=label)
        ax[1, 0].plot(s[:, 0] / 10, s[:, 1], color=color, label=label)
        ax[1, 1].plot(depth, fom_values / ref_fom_values, color=color, label=label)
    for d, color in zip(DEPTHS_CM, ("#8db255", "#00a02b", "#064f53")):
        b1 = np.array([float(row[f"B1p_d{d}cm_uT"]) for row in rows])
        fom = np.array([float(row[f"FoM_d{d}cm"]) for row in rows])
        ax[0, 2].plot(lengths / 10, b1 / b1.max(), "o-", color=color, label=f"{d} cm")
        ax[1, 2].plot(lengths / 10, fom / fom.max(), "o-", color=color, label=f"{d} cm")
    titles = ["(a) B1+ vs depth", "(b) relative B1+ vs 25 cm", "(c) relative B1+ vs length",
              "(d) native 10g SAR profile", "(e) relative B1+/sqrt(SARmax)", "(f) relative FoM vs length"]
    for axis, title in zip(ax.flat, titles):
        axis.set_title(title); axis.grid(alpha=.3)
    ax[0,0].set_ylabel("B1+ [uT/sqrt(W)]"); ax[1,0].set_ylabel("SAR10g [W/kg/W]")
    for axis in (ax[0,0], ax[0,1], ax[1,1]): axis.set_xlim(0, 20); axis.set_xlabel("depth [cm]")
    ax[1,0].set_xlabel("longitudinal y [cm]")
    for axis in (ax[0,2], ax[1,2]): axis.set_xlabel("dipole length [cm]"); axis.legend()
    ax[0,0].legend(ncol=2, fontsize=8); ax[1,0].legend(ncol=2, fontsize=8)
    fig.suptitle("Raaijmakers 2016 Fig. 3 reproduction - complete six panels")
    fig.tight_layout(rect=(0, 0, 1, .96))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=170); plt.close(fig)


def plot_fig4(args) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = sorted(_read_rows(Path(args.summary)), key=lambda row: float(row["Z_seg_ohm"]))
    profiles = Path(args.profile_dir)
    plain_rows = [row for row in rows if _is_plain_segment_row(row)]
    if len(plain_rows) != 1:
        raise ValueError(f"Fig. 4 requires exactly one element=plain baseline row, found {len(plain_rows)}")
    base = plain_rows[0]
    base_b = _read_profile(profiles / f"b1p_indepth_seg_{base['tag']}.csv")
    base_fom = base_b[:,1] / math.sqrt(float(base["SARmax_Wkg"]))
    zaxis = np.array([float(row["Z_seg_ohm"]) for row in rows])
    fig, ax = plt.subplots(2, 3, figsize=(18, 10.5))
    displayed_labels = []
    for row in rows:
        tag = row["tag"]
        b = _read_profile(profiles / f"b1p_indepth_seg_{tag}.csv")
        s = _read_profile(profiles / f"sar_alongY_seg_{tag}.csv")
        _assert_longitudinal_coverage(
            s[:, 0], 300.0, profiles / f"sar_alongY_seg_{tag}.csv"
        )
        depth = -b[:,0] / 10; order = np.argsort(depth); depth, values = depth[order], b[:,1][order]
        base_values = np.interp(depth, -base_b[:,0][::-1]/10, base_b[:,1][::-1])
        base_fom_values = np.interp(depth, -base_b[:,0][::-1]/10, base_fom[::-1])
        color = "black" if _is_plain_segment_row(row) else plt.cm.coolwarm((float(row["Z_seg_ohm"])-zaxis.min())/(zaxis.max()-zaxis.min()))
        label = _fig4_display_subset_label(row)
        if label is not None:
            displayed_labels.append(label)
            ax[0,0].plot(depth, values, color=color, label=label)
            ax[1,0].plot(s[:,0]/10, s[:,1], color=color, label=label)
        ax[0,1].plot(depth, values/base_values, color=color)
        fom_values = values/math.sqrt(float(row["SARmax_Wkg"]))
        ax[1,1].plot(depth, fom_values/base_fom_values, color=color)
    for d, color in zip(DEPTHS_CM, ("#8db255", "#00a02b", "#064f53")):
        b1 = np.array([float(row[f"B1p_d{d}cm_uT"]) for row in rows])
        fom = np.array([float(row[f"FoM_d{d}cm"]) for row in rows])
        b0 = float(base[f"B1p_d{d}cm_uT"]); f0 = float(base[f"FoM_d{d}cm"])
        ax[0,2].plot(zaxis, b1/b0, "o-", color=color, label=f"{d} cm")
        ax[1,2].plot(zaxis, fom/f0, "o-", color=color, label=f"{d} cm")
    expected_displayed = ["1 pF", "5 pF", "plain", "50 nH", "100 nH", "150 nH"]
    if displayed_labels != expected_displayed:
        raise ValueError(
            "Fig. 4 panels (a)/(d) require exactly the paper display subset "
            f"{expected_displayed!r}, got {displayed_labels!r}"
        )
    titles = ["(a) B1+ vs depth", "(b) relative B1+ vs plain", "(c) relative B1+ vs impedance",
              "(d) native 10g SAR profile", "(e) relative B1+/sqrt(SARmax)", "(f) relative FoM vs impedance"]
    for axis, title in zip(ax.flat, titles): axis.set_title(title); axis.grid(alpha=.3)
    for axis in (ax[0,0], ax[0,1], ax[1,1]): axis.set_xlim(0,20); axis.set_xlabel("depth [cm]")
    ax[1,0].set_xlabel("longitudinal y [cm]")
    for axis in (ax[0,2], ax[1,2]): axis.set_xlabel("intersegment reactance [ohm]"); axis.legend()
    ax[0,0].legend(fontsize=8); ax[1,0].legend(fontsize=8)
    fig.suptitle("Raaijmakers 2016 Fig. 4 reproduction - complete six panels")
    fig.tight_layout(rect=(0,0,1,.96)); Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=170); plt.close(fig)


def paper_compare(args) -> None:
    """Extract the target paper figure and stack it above the current reproduction."""
    from PIL import Image, ImageDraw, ImageFont
    from pypdf import PdfReader

    page_index = 3 if args.figure == 3 else 4  # zero-based PDF pages
    page = PdfReader(args.paper_pdf).pages[page_index]
    if not page.images:
        raise RuntimeError(f"no embedded image found on PDF page {page_index + 1}")
    paper = Image.open(BytesIO(page.images[0].data)).convert("RGB")
    reproduction = Image.open(args.reproduction).convert("RGB")
    target_width = paper.width
    target_height = max(1, round(reproduction.height * target_width / reproduction.width))
    reproduction = reproduction.resize((target_width, target_height), Image.Resampling.LANCZOS)
    label_height = 72
    canvas = Image.new("RGB", (target_width, paper.height + target_height + 2 * label_height), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    draw.text((22, 18), f"Paper Fig. {args.figure} (original)", fill="black", font=font)
    canvas.paste(paper, (0, label_height))
    y = label_height + paper.height
    draw.text((22, y + 18), f"Current demo Fig. {args.figure} reproduction", fill="black", font=font)
    canvas.paste(reproduction, (0, y + label_height))
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    print(json.dumps({
        "figure": args.figure,
        "paper_page": page_index + 1,
        "reproduction": str(Path(args.reproduction)),
        "output": str(output),
        "size_px": list(canvas.size),
    }))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("--kind", choices=("length", "segment"), required=True)
    extract.add_argument("--case-id", required=True)
    extract.add_argument("--length-mm", type=float, default=300)
    extract.add_argument("--reactance-ohm", type=float, default=0)
    extract.add_argument("--element", default="plain")
    extract.add_argument("--value", type=float, default=0)
    extract.add_argument("--p-accepted", type=float, required=True)
    extract.add_argument("--hfield", required=True); extract.add_argument("--sar", required=True)
    extract.add_argument("--summary", required=True); extract.add_argument("--profile-dir", required=True)
    for name, function in (("plot-fig3", plot_fig3), ("plot-fig4", plot_fig4)):
        command = sub.add_parser(name); command.add_argument("--summary", required=True)
        command.add_argument("--profile-dir", required=True); command.add_argument("--output", required=True)
        command.set_defaults(function=function)
    compare = sub.add_parser("paper-compare")
    compare.add_argument("--figure", type=int, choices=(3, 4), required=True)
    compare.add_argument("--paper-pdf", required=True)
    compare.add_argument("--reproduction", required=True)
    compare.add_argument("--output", required=True)
    compare.set_defaults(function=paper_compare)
    args = parser.parse_args()
    if args.command == "extract": extract_case(args)
    else: args.function(args)


if __name__ == "__main__":
    main()
