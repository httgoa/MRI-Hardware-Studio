#!/usr/bin/env python3
"""Deterministic artifacts for Raaijmakers 2016 Fig. 3/4 reproduction.

This module is intentionally paper-specific.  It emits small CST history blocks
for either the plain length-study dipole or the three-segments-per-arm model.
The emitted artifacts are replayed through ``batch_execute.py``; this script
never opens CST.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FREQ_GHZ = 0.298


def _brick(name: str, y0: str, y1: str) -> str:
    return f'''With Brick
    .Reset
    .Name "{name}"
    .Component "dipole"
    .Material "PEC"
    .Xrange "-W_line/2", "W_line/2"
    .Yrange "{y0}", "{y1}"
    .Zrange "H_height", "H_height+T"
    .Create
End With'''


def _segment_bounds(n_segments_per_arm: int, k: int) -> tuple[str, str, str]:
    if n_segments_per_arm < 1:
        raise ValueError("n_segments_per_arm must be >= 1")
    if n_segments_per_arm == 1:
        seg_len = "L_total/2-hole"
    else:
        seg_len = (
            f"((L_total/2-hole)-{n_segments_per_arm - 1}*seg_gap)"
            f"/{n_segments_per_arm}"
        )
    if k == 0:
        start = "hole"
    else:
        start = f"hole+{k}*({seg_len}+seg_gap)"
    stop = f"({start})+({seg_len})"
    return seg_len, start, stop


def _geometry(n_segments_per_arm: int) -> str:
    blocks = ['Component.New "dipole"']
    for k in range(n_segments_per_arm):
        _, start, stop = _segment_bounds(n_segments_per_arm, k)
        blocks.append(_brick(f"arm_pY_{k}", start, stop))
        blocks.append(_brick(f"arm_nY_{k}", f"-({stop})", f"-({start})"))
    return "\n\n".join(blocks)


def _bridge(n_segments_per_arm: int, side: str, k: int) -> str:
    seg_len, _, _ = _segment_bounds(n_segments_per_arm, k)
    y0 = f"hole+({k + 1})*({seg_len})+{k}*seg_gap"
    y1 = f"({y0})+seg_gap"
    if side == "pY":
        p1, p2 = y0, y1
    elif side == "nY":
        p1, p2 = f"-({y0})", f"-({y1})"
    else:
        raise ValueError(f"unknown bridge side: {side}")
    return f'''With LumpedElement
    .Reset
    .SetType "RLCSerial"
    .Folder "segments"
    .SetName "bridge_{side}_{k}"
    .SetR "0"
    .SetL "L_seg*1e-9"
    .SetC "C_seg*1e-12"
    .SetMonitor "True"
    .SetP1 "False", "0", "{p1}", "H_height+T/2"
    .SetP2 "False", "0", "{p2}", "H_height+T/2"
    .SetInvert "False"
    .SetRadius "0.0"
    .Create
End With'''


def _bridges(n_segments_per_arm: int) -> str | None:
    if n_segments_per_arm < 2:
        return None
    blocks: list[str] = []
    for k in range(n_segments_per_arm - 1):
        for side in ("pY", "nY"):
            blocks.append(_bridge(n_segments_per_arm, side, k))
    return "\n\n".join(blocks)


def build_blocks(n_segments_per_arm: int = 1) -> list[tuple[str, str]]:
    # Parameter definitions live in the history tree and are replayed by every
    # Rebuild.  MakeSureParameterExists creates missing parameters without
    # overwriting values changed by the Fig. 3/4 sweep.  StoreParameter here
    # triggers CST's "Prevented attempt to change the value ... inside history
    # rebuild" warning and can break parametrization.
    params = f'''MakeSureParameterExists "freq", "{FREQ_GHZ:g}"
MakeSureParameterExists "L_total", "300"
MakeSureParameterExists "W_line", "10"
MakeSureParameterExists "T", "0.5"
MakeSureParameterExists "hole", "1"
MakeSureParameterExists "H_height", "20"
MakeSureParameterExists "seg_gap", "2"
MakeSureParameterExists "L_seg", "75"
MakeSureParameterExists "C_seg", "0"
MakeSureParameterExists "eps_ph", "34"
MakeSureParameterExists "sigma_ph", "0.4"
MakeSureParameterExists "ph_size", "500"
MakeSureParameterExists "segments_per_arm", "{n_segments_per_arm}"'''

    setup = '''With Units
    .Geometry "mm"
    .Frequency "GHz"
    .Time "ns"
End With
Solver.FrequencyRange "0.198", "0.398"
With Background
    .Type "Normal"
    .Epsilon "1.0"
    .Mu "1.0"
    .XminSpace "0"
    .XmaxSpace "0"
    .YminSpace "0"
    .YmaxSpace "0"
    .ZminSpace "0"
    .ZmaxSpace "0"
End With
With Boundary
    .Xmin "expanded open"
    .Xmax "expanded open"
    .Ymin "expanded open"
    .Ymax "expanded open"
    .Zmin "expanded open"
    .Zmax "expanded open"
    .Xsymmetry "none"
    .Ysymmetry "none"
    .Zsymmetry "none"
End With'''

    material = '''With Material
    .Reset
    .Name "phantom"
    .Folder ""
    .Type "Normal"
    .Epsilon "eps_ph"
    .Mu "1"
    .Sigma "sigma_ph"
    .Rho "1000"
    .Colour "0.85", "0.35", "0.35"
    .Transparency "0.6"
    .Create
End With'''

    phantom = '''Component.New "phantom"
With Brick
    .Reset
    .Name "phantom"
    .Component "phantom"
    .Material "phantom"
    .Xrange "-ph_size/2", "ph_size/2"
    .Yrange "-ph_size/2", "ph_size/2"
    .Zrange "-ph_size", "0"
    .Create
End With'''

    port = '''With DiscretePort
    .Reset
    .PortNumber "1"
    .Type "SParameter"
    .Label ""
    .Impedance "50.0"
    .Voltage "1.0"
    .Current "1.0"
    .Monitor "True"
    .Radius "0.0"
    .SetP1 "False", "0", "-hole", "H_height+T/2"
    .SetP2 "False", "0", "hole", "H_height+T/2"
    .InvertDirection "False"
    .LocalCoordinates "False"
    .Wire ""
    .Position "end1"
    .Create
End With'''

    monitors = '''With Monitor
    .Reset
    .Name "h-field (f=0.298)"
    .Dimension "Volume"
    .Domain "Frequency"
    .FieldType "Hfield"
    .MonitorValue "freq"
    .UseSubvolume "False"
    .Create
End With
With Monitor
    .Reset
    .Name "loss (f=0.298)"
    .Dimension "Volume"
    .Domain "Frequency"
    .FieldType "Powerloss"
    .MonitorValue "freq"
    .UseSubvolume "False"
    .Create
End With'''

    solver = '''ChangeSolverType "HF Time Domain"
Solver.FrequencyRange "0.198", "0.398"
With MeshSettings
    .SetMeshType "Hex"
    .Set "Version", 1
End With
With Mesh
    .MeshType "PBA"
End With
With Solver
    .Method "Hexahedral"
    .SteadyStateLimit "-30"
    .StimulationMode "1"
    .CalculateModesOnly "False"
End With'''

    blocks = [
        ("define paper parameters", params),
        ("set units background boundary", setup),
        ("define phantom material", material),
        ("create phantom", phantom),
        ("create dipole geometry", _geometry(n_segments_per_arm)),
        ("define direct feed port", port),
    ]
    bridges = _bridges(n_segments_per_arm)
    if bridges:
        blocks.append(("define inter-segment bridges", bridges))
    blocks.extend([
        ("define field monitors", monitors),
        ("set time-domain solver", solver),
    ])
    return blocks


def build_recording_blocks(n_segments_per_arm: int = 1) -> list[dict]:
    """Return fine-grained blocks plus camera/milestone metadata for demos."""
    base = dict(build_blocks(n_segments_per_arm))
    blocks: list[dict] = []

    def add(title: str, code: str, *, reset_view: bool = False,
            milestone_after: str | None = None, visible: str = "") -> None:
        blocks.append({
            "title": title,
            "code": code,
            "reset_view": reset_view,
            "milestone_after": milestone_after,
            "visible": visible,
        })

    add("define paper parameters", base["define paper parameters"])
    add("set units background boundary", base["set units background boundary"])
    add("define phantom material", base["define phantom material"])
    add("create dipole component", 'Component.New "dipole"')
    for k in range(n_segments_per_arm):
        _, start, stop = _segment_bounds(n_segments_per_arm, k)
        code = "\n\n".join((
            _brick(f"arm_pY_{k}", start, stop),
            _brick(f"arm_nY_{k}", f"-({stop})", f"-({start})"),
        ))
        pair_name = ("continuous arms" if n_segments_per_arm == 1
                     else ("inner", "middle", "outer")[k] + " segment pair")
        add(
            f"create {pair_name}", code, reset_view=True,
            visible=f"PEC {pair_name} centered on the feed gap",
        )
    add(
        "define direct feed port", base["define direct feed port"],
        reset_view=True, visible="50-ohm discrete feed port in the center gap",
    )
    if n_segments_per_arm > 1:
        for k in range(n_segments_per_arm - 1):
            for side in ("pY", "nY"):
                add(
                    f"create bridge {side} {k}",
                    _bridge(n_segments_per_arm, side, k),
                    reset_view=(side == "nY"),
                    visible=f"inter-segment bridge pair {k + 1}" if side == "nY" else "",
                )
    topology = "plain" if n_segments_per_arm == 1 else "segmented"
    add(
        "create phantom", base["create phantom"], reset_view=True,
        visible="transparent 500 mm phantom with the complete antenna above it",
    )
    add("define field monitors", base["define field monitors"])
    add(
        "set time-domain solver", base["set time-domain solver"],
        milestone_after=("fig3_pre_solve" if topology == "plain" else "fig4_pre_solve"),
        visible="complete model and configured simulation tree",
    )
    return blocks


def emit_artifacts(
    outroot: Path,
    project: str,
    n_segments_per_arm: int,
    variant: str | None = None,
    presentation_mode: str = "production",
) -> dict:
    root = outroot / project / "artifacts"
    if presentation_mode == "recording":
        root = root / "demo"
    if variant:
        root = root / variant
    root.mkdir(parents=True, exist_ok=True)
    emitted = []
    if presentation_mode == "recording":
        source_blocks = build_recording_blocks(n_segments_per_arm)
    elif presentation_mode == "production":
        source_blocks = [
            {"title": title, "code": code, "reset_view": False,
             "milestone_after": None, "visible": ""}
            for title, code in build_blocks(n_segments_per_arm)
        ]
    else:
        raise ValueError(f"unknown presentation mode: {presentation_mode}")
    for index, block in enumerate(source_blocks, start=1):
        title, code = block["title"], block["code"]
        slug = "_".join(title.lower().replace("-", " ").split())
        step = root / f"{index:02d}_{slug}"
        step.mkdir(parents=True, exist_ok=True)
        path = step / f"{slug}.bas"
        path.write_text(code.rstrip() + "\n", encoding="utf-8")
        emitted.append({
            "index": index - 1,
            "title": title,
            "path": str(path.resolve()),
            "reset_view": bool(block["reset_view"]),
            "milestone_after": block["milestone_after"],
            "visible": block["visible"],
        })
    manifest = {
        "schema": "paper-fractionated-dipole-artifacts-v1",
        "project": project,
        "outroot": str(outroot),
        "paper": "Raaijmakers et al., MRM 75:1366-1374 (2016)",
        "frequency_ghz": FREQ_GHZ,
        "segments_per_arm": n_segments_per_arm,
        "variant": variant,
        "presentation_mode": presentation_mode,
        "blocks": emitted,
    }
    manifest_path = root / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"manifest": str(manifest_path.resolve()), "blocks": emitted}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outroot", default="results")
    parser.add_argument("--project", required=True)
    parser.add_argument("--segments-per-arm", type=int, choices=(1, 3), default=1)
    parser.add_argument("--variant", default=None)
    parser.add_argument(
        "--presentation-mode", choices=("production", "recording"),
        default="production",
    )
    args = parser.parse_args()
    report = emit_artifacts(
        Path(args.outroot), args.project, args.segments_per_arm, args.variant,
        args.presentation_mode,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
