#!/usr/bin/env python3
"""Compile validated D1/D2 records into deterministic few-shot learning cards.

The compiler keeps raw field archives and case metrics as the source of truth.
It emits compact global, parent-child delta, and two-parameter interaction
cards for retrieval-time use.  No LLM is used to create labels or summaries.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parents[2]
MATRIX_DIR = SKILL_ROOT / "recipes" / "data-prep" / "complete-case(D1)"

CASE_CARD_SCHEMA = "mri_agent.few_shot.case_card.v1"
DELTA_CARD_SCHEMA = "mri_agent.few_shot.delta_card.v1"
INTERACTION_CARD_SCHEMA = "mri_agent.few_shot.interaction_card.v1"
CATALOG_SCHEMA = "mri_agent.few_shot.catalog.v1"

DEFAULT_RESULTS_ROOT = REPO_ROOT / "results_data_prep"
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_ROOT / "learning"

QA_GATE = {
    "qa_status": "validated",
    "sar_status": "validated_native_h5",
    "field_archive_status": "complete",
    "schema_pass": True,
    "record_hash_match": True,
}


@dataclass(frozen=True)
class Metric:
    name: str
    path: str
    unit: str
    relative: bool = True


@dataclass(frozen=True)
class Parameter:
    name: str
    path: str
    unit: str


METRICS = (
    Metric("s11_210MHz_dB", "electrical_state.s11_210MHz_dB", "dB", False),
    Metric("resonant_frequency_MHz", "electrical_state.resonant_frequency_MHz", "MHz"),
    Metric("input_R_ohm", "electrical_state.input_R_ohm", "ohm"),
    Metric("input_X_ohm", "electrical_state.input_X_ohm", "ohm"),
    Metric(
        "b1p_surface_mean_uT_per_sqrtW",
        "b1_signature.b1p_surface_mean_uT_per_sqrtW",
        "uT/sqrt(W accepted)",
    ),
    Metric(
        "b1p_30mm_mean_uT_per_sqrtW",
        "b1_signature.b1p_30mm_mean_uT_per_sqrtW",
        "uT/sqrt(W accepted)",
    ),
    Metric(
        "b1p_60mm_mean_uT_per_sqrtW",
        "b1_signature.b1p_60mm_mean_uT_per_sqrtW",
        "uT/sqrt(W accepted)",
    ),
    Metric(
        "b1p_at_10cm_mean_uT_per_sqrtW",
        "b1_signature.b1p_at_10cm_mean_uT_per_sqrtW",
        "uT/sqrt(W accepted)",
    ),
    Metric(
        "b1p_peak_uT_per_sqrtW",
        "b1_signature.b1p_peak_uT_per_sqrtW",
        "uT/sqrt(W accepted)",
    ),
    Metric("cov_roi", "b1_signature.cov_roi", "ratio"),
    Metric("half_value_depth_mm", "b1_signature.half_value_depth_mm", "mm"),
    Metric(
        "penetration_auc_0_150_uTmm_per_sqrtW",
        "b1_signature.penetration_auc_0_150_uTmm_per_sqrtW",
        "uT*mm/sqrt(W accepted)",
    ),
    Metric(
        "sar10g_max_W_per_kg_per_W",
        "sar_signature.sar10g_max_W_per_kg_per_W",
        "W/kg @ 1W accepted",
    ),
    Metric(
        "sar10g_p99_W_per_kg_per_W",
        "sar_signature.sar10g_p99_W_per_kg_per_W",
        "W/kg @ 1W accepted",
    ),
    Metric(
        "sar10g_roi_mean_W_per_kg_per_W",
        "sar_signature.sar10g_roi_mean_W_per_kg_per_W",
        "W/kg @ 1W accepted",
    ),
    Metric("sar_hotspot_depth_mm", "sar_signature.sar_hotspot_depth_mm", "mm"),
    Metric(
        "sar_hotspot_distance_to_conductor_mm",
        "sar_signature.sar_hotspot_distance_to_conductor_mm",
        "mm",
    ),
    Metric(
        "sar_hotspot_concentration",
        "sar_signature.sar_hotspot_concentration",
        "ratio",
    ),
    Metric("sar_efficiency_10cm", "sar_signature.sar_efficiency_10cm", "ratio"),
    Metric(
        "current_peak_A_per_sqrtW",
        "current_signature.current_peak_A_per_sqrtW",
        "A/sqrt(W accepted)",
    ),
    Metric(
        "current_mean_A_per_sqrtW",
        "current_signature.current_mean_A_per_sqrtW",
        "A/sqrt(W accepted)",
    ),
    Metric(
        "current_center_to_end_ratio",
        "current_signature.current_center_to_end_ratio",
        "ratio",
    ),
    Metric(
        "current_left_right_symmetry_error",
        "current_signature.current_left_right_symmetry_error",
        "ratio",
    ),
    Metric("current_phase_span_deg", "current_signature.current_phase_span_deg", "deg"),
)

PARAMETERS = {
    item.name: item
    for item in (
        Parameter("L_line_mm", "geometry.L_line_mm", "mm"),
        Parameter("strip_width_mm", "geometry.strip_width_mm", "mm"),
        Parameter("coil_to_phantom_mm", "geometry.coil_to_phantom_mm", "mm"),
        Parameter("feed_gap_mm", "geometry.feed_gap_mm", "mm"),
        Parameter("segment_count_total", "geometry.segment_count_total", "count"),
        Parameter("seg_gap_mm", "geometry.seg_gap_mm", "mm"),
        Parameter(
            "lt_bridge_mode",
            "electrical_design.fractionated_bridge.lt_bridge_mode",
            "category",
        ),
        Parameter(
            "bridge_C_pF",
            "electrical_design.fractionated_bridge.bridge_C_pF",
            "pF",
        ),
        Parameter(
            "bridge_L_nH",
            "electrical_design.fractionated_bridge.bridge_L_nH",
            "nH",
        ),
    )
}

PRIMARY_DESIGN_PARAMETERS = tuple(PARAMETERS)
RELATIVE_EFFECT_THRESHOLD_PCT = 2.0
DEPTH_EFFECT_THRESHOLD_MM = 1.0
RESONANCE_EFFECT_THRESHOLD_MHZ = 1.0
HOTSPOT_SHIFT_THRESHOLD_MM = 5.0
INTERACTION_RATIO_THRESHOLD = 0.25


def _get(data: dict[str, Any], dotted_path: str) -> Any:
    value: Any = data
    for part in dotted_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _round(value: float | None, digits: int = 10) -> float | None:
    if value is None:
        return None
    result = round(value, digits)
    return 0.0 if result == 0 else result


def _relative_percent(before: Any, after: Any) -> float | None:
    old = _as_float(before)
    new = _as_float(after)
    if old is None or new is None or abs(old) < 1e-15:
        return None
    return _round((new - old) / abs(old) * 100.0)


def _numeric_delta(before: Any, after: Any) -> float | None:
    old = _as_float(before)
    new = _as_float(after)
    if old is None or new is None:
        return None
    return _round(new - old)


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_text_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return True


def _write_json_if_changed(path: Path, data: Any) -> bool:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return _write_text_if_changed(path, text)


def _jsonl(cards: Iterable[dict[str, Any]]) -> str:
    return "".join(_canonical_json(card) + "\n" for card in cards)


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: cleaned
            for key, item in value.items()
            if (cleaned := _drop_none(item)) is not None
        }
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value


def _split_params(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def _format_number(value: Any, digits: int = 4) -> str:
    number = _as_float(value)
    return "unknown" if number is None else f"{number:.{digits}f}"


def _state(record: dict[str, Any], role: str) -> dict[str, Any]:
    geometry = record["geometry"]
    electrical = record["electrical_design"]
    bridge = electrical["fractionated_bridge"]
    materials = record["materials_and_load"]
    simulation = record["simulation"]
    return _drop_none(
        {
            "family": geometry.get("family"),
            "topology": geometry.get("topology"),
            "role": role,
            "geometry": {
                "L_line_mm": geometry.get("L_line_mm"),
                "strip_width_mm": geometry.get("strip_width_mm"),
                "coil_to_phantom_mm": geometry.get("coil_to_phantom_mm"),
                "feed_gap_mm": geometry.get("feed_gap_mm"),
                "segment_count_total": geometry.get("segment_count_total"),
                "seg_gap_mm": geometry.get("seg_gap_mm"),
            },
            "bridge": {
                "mode": bridge.get("lt_bridge_mode"),
                "C_pF": bridge.get("bridge_C_pF"),
                "L_nH": bridge.get("bridge_L_nH"),
                "R_ohm": bridge.get("bridge_R_ohm"),
            },
            "environment": {
                "freq_MHz": electrical.get("freq_MHz"),
                "phantom_eps_r": materials.get("phantom_eps_r"),
                "phantom_sigma_S_per_m": materials.get("phantom_sigma_S_per_m"),
                "phantom_rho_kg_per_m3": materials.get("phantom_rho_kg_per_m3"),
                "phantom_size_mm": materials.get("phantom_size_mm"),
            },
            "simulation_contract": {
                "network_role": electrical.get("network_role"),
                "normalization": simulation.get("normalization"),
                "solver_type": simulation.get("solver_type"),
                "mesh_type": simulation.get("mesh_type"),
            },
        }
    )


def _performance(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "electrical": {
            "p_accepted_W": _get(record, "electrical_state.p_accepted_W"),
            "s11_210MHz_dB": _get(record, "electrical_state.s11_210MHz_dB"),
            "s11_min_dB": _get(record, "electrical_state.s11_min_dB"),
            "resonant_frequency_MHz": _get(
                record, "electrical_state.resonant_frequency_MHz"
            ),
            "input_R_ohm": _get(record, "electrical_state.input_R_ohm"),
            "input_X_ohm": _get(record, "electrical_state.input_X_ohm"),
        },
        "b1": {
            metric.name: _get(record, metric.path)
            for metric in METRICS
            if metric.path.startswith("b1_signature.")
        },
        "sar": {
            metric.name: _get(record, metric.path)
            for metric in METRICS
            if metric.path.startswith("sar_signature.")
        },
        "current": {
            metric.name: _get(record, metric.path)
            for metric in METRICS
            if metric.path.startswith("current_signature.")
        },
    }


def _profile_references(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "b1_depth_csv": _get(record, "b1_signature.depth_profile_csv"),
        "b1_lateral_csv": _get(record, "b1_signature.lateral_profile_csv"),
        "b1_slices_48x48_npz": _get(record, "b1_signature.slices_48x48_npz"),
        "sar_depth_csv": _get(record, "sar_signature.depth_profile_csv"),
        "sar_slices_48x48_npz": _get(record, "sar_signature.slices_48x48_npz"),
    }


def make_case_summary(record: dict[str, Any]) -> str:
    geometry = record["geometry"]
    bridge = record["electrical_design"]["fractionated_bridge"]
    design = (
        f"{geometry['family']}; L={_format_number(geometry.get('L_line_mm'), 1)} mm, "
        f"W={_format_number(geometry.get('strip_width_mm'), 1)} mm, "
        f"lift-off={_format_number(geometry.get('coil_to_phantom_mm'), 1)} mm"
    )
    if bridge.get("lt_bridge_mode") == "lumped_C":
        design += f", bridge C={_format_number(bridge.get('bridge_C_pF'), 3)} pF"
    elif bridge.get("lt_bridge_mode") == "lumped_L":
        design += f", bridge L={_format_number(bridge.get('bridge_L_nH'), 1)} nH"
    return (
        f"{design}. At 1 W accepted: B1+(10 cm)="
        f"{_format_number(_get(record, 'b1_signature.b1p_at_10cm_mean_uT_per_sqrtW'))} "
        f"uT/sqrt(W), SAR10g max="
        f"{_format_number(_get(record, 'sar_signature.sar10g_max_W_per_kg_per_W'))} "
        f"W/kg, SAR efficiency="
        f"{_format_number(_get(record, 'sar_signature.sar_efficiency_10cm'))}, "
        f"ROI CoV={_format_number(_get(record, 'b1_signature.cov_roi'))}, "
        f"half-value depth="
        f"{_format_number(_get(record, 'b1_signature.half_value_depth_mm'), 1)} mm; "
        f"current hotspot={_get(record, 'current_signature.current_hotspot_region') or 'unknown'}, "
        f"SAR hotspot depth="
        f"{_format_number(_get(record, 'sar_signature.sar_hotspot_depth_mm'), 1)} mm."
    )


def make_case_card(
    record: dict[str, Any],
    matrix_row: dict[str, str],
    record_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    return {
        "schema_version": CASE_CARD_SCHEMA,
        "card_type": "global_case",
        "card_id": f"case::{record['record_id']}",
        "record_id": record["record_id"],
        "case_matrix_id": record["case_matrix_id"],
        "state": _state(record, matrix_row["role"]),
        "performance": _performance(record),
        "profile_references": _profile_references(record),
        "design_tokens": record["learning_card"].get("design_tokens", []),
        "summary_text": make_case_summary(record),
        "evidence": {
            "record_path": _repo_relative(record_path, repo_root),
            "qa_status": record["qa"].get("qa_status"),
            "sar_status": record["sar_signature"].get("sar_status"),
            "field_archive_status": record["qa"].get("field_archive_status"),
        },
    }


def _metric_outcome(
    parent: dict[str, Any], child: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    outcome: dict[str, dict[str, Any]] = {}
    for metric in METRICS:
        before = _get(parent, metric.path)
        after = _get(child, metric.path)
        item = {
            "before": before,
            "after": after,
            "delta": _numeric_delta(before, after),
            "unit": metric.unit,
        }
        if metric.relative:
            item["relative_change_pct"] = _relative_percent(before, after)
        outcome[metric.name] = item
    return outcome


def _hotspot_shift_mm(parent: dict[str, Any], child: dict[str, Any]) -> float | None:
    before = _get(parent, "sar_signature.sar_hotspot_xyz_mm")
    after = _get(child, "sar_signature.sar_hotspot_xyz_mm")
    if not (
        isinstance(before, list)
        and isinstance(after, list)
        and len(before) == 3
        and len(after) == 3
    ):
        return None
    try:
        return _round(
            math.sqrt(sum((float(new) - float(old)) ** 2 for old, new in zip(before, after)))
        )
    except (TypeError, ValueError):
        return None


def _effect_labels(
    outcome: dict[str, dict[str, Any]], hotspot_shift_mm: float | None
) -> list[str]:
    labels: list[str] = []

    def relative_label(metric: str, increase: str, decrease: str) -> None:
        change = outcome[metric].get("relative_change_pct")
        if change is None:
            return
        if change >= RELATIVE_EFFECT_THRESHOLD_PCT:
            labels.append(increase)
        elif change <= -RELATIVE_EFFECT_THRESHOLD_PCT:
            labels.append(decrease)

    relative_label(
        "b1p_at_10cm_mean_uT_per_sqrtW",
        "deep_b1_increased",
        "deep_b1_decreased",
    )
    relative_label(
        "b1p_surface_mean_uT_per_sqrtW",
        "surface_b1_increased",
        "surface_b1_decreased",
    )
    relative_label(
        "sar10g_max_W_per_kg_per_W",
        "sar10g_increased",
        "sar10g_decreased",
    )
    relative_label(
        "sar_efficiency_10cm",
        "sar_efficiency_improved",
        "sar_efficiency_worsened",
    )

    cov_change = outcome["cov_roi"].get("relative_change_pct")
    if cov_change is not None:
        if cov_change <= -RELATIVE_EFFECT_THRESHOLD_PCT:
            labels.append("uniformity_improved")
        elif cov_change >= RELATIVE_EFFECT_THRESHOLD_PCT:
            labels.append("uniformity_worsened")

    depth_delta = outcome["half_value_depth_mm"].get("delta")
    if depth_delta is not None:
        if depth_delta >= DEPTH_EFFECT_THRESHOLD_MM:
            labels.append("penetration_depth_increased")
        elif depth_delta <= -DEPTH_EFFECT_THRESHOLD_MM:
            labels.append("penetration_depth_decreased")

    resonance_delta = outcome["resonant_frequency_MHz"].get("delta")
    if resonance_delta is not None:
        if resonance_delta >= RESONANCE_EFFECT_THRESHOLD_MHZ:
            labels.append("resonance_shifted_up")
        elif resonance_delta <= -RESONANCE_EFFECT_THRESHOLD_MHZ:
            labels.append("resonance_shifted_down")

    if hotspot_shift_mm is not None and hotspot_shift_mm >= HOTSPOT_SHIFT_THRESHOLD_MM:
        labels.append("sar_hotspot_shifted")
    return labels


def _tradeoff_summary(outcome: dict[str, dict[str, Any]]) -> str:
    def pct(metric: str) -> str:
        value = outcome[metric].get("relative_change_pct")
        return "unknown" if value is None else f"{value:+.1f}%"

    depth = outcome["half_value_depth_mm"].get("delta")
    depth_text = "unknown" if depth is None else f"{depth:+.1f} mm"
    return (
        f"Deep B1 change {pct('b1p_at_10cm_mean_uT_per_sqrtW')}; "
        f"SAR10g max change {pct('sar10g_max_W_per_kg_per_W')}; "
        f"SAR efficiency change {pct('sar_efficiency_10cm')}; "
        f"ROI CoV change {pct('cov_roi')}; "
        f"half-value depth change {depth_text}."
    )


def make_delta_card(
    parent: dict[str, Any],
    child: dict[str, Any],
    matrix_row: dict[str, str],
) -> dict[str, Any]:
    changed_params = _split_params(matrix_row.get("changed_params"))
    if not changed_params:
        raise ValueError(f"{child['case_matrix_id']}: D2 row has no changed_params")

    changes: dict[str, dict[str, Any]] = {}
    for name in changed_params:
        parameter = PARAMETERS.get(name)
        if parameter is None:
            raise ValueError(f"{child['case_matrix_id']}: unsupported changed parameter {name}")
        before = _get(parent, parameter.path)
        after = _get(child, parameter.path)
        item: dict[str, Any] = {
            "before": before,
            "after": after,
            "unit": parameter.unit,
        }
        delta = _numeric_delta(before, after)
        if delta is not None:
            item["delta"] = delta
            item["relative_change_pct"] = _relative_percent(before, after)
        if before == after:
            raise ValueError(
                f"{child['case_matrix_id']}: {name} is declared changed but values match"
            )
        changes[name] = item

    unexpected = []
    for name in PRIMARY_DESIGN_PARAMETERS:
        if name in changed_params:
            continue
        parameter = PARAMETERS[name]
        if _get(parent, parameter.path) != _get(child, parameter.path):
            unexpected.append(name)
    if unexpected:
        raise ValueError(
            f"{child['case_matrix_id']}: unlisted design changes: {', '.join(unexpected)}"
        )

    outcome = _metric_outcome(parent, child)
    hotspot_shift = _hotspot_shift_mm(parent, child)
    labels = _effect_labels(outcome, hotspot_shift)
    return {
        "schema_version": DELTA_CARD_SCHEMA,
        "card_type": "parameter_delta",
        "card_id": f"delta::{parent['record_id']}::{child['record_id']}",
        "parent_record_id": parent["record_id"],
        "child_record_id": child["record_id"],
        "parent_case_matrix_id": parent["case_matrix_id"],
        "child_case_matrix_id": child["case_matrix_id"],
        "family": child["geometry"]["family"],
        "action": {
            "action_type": matrix_row["action_type"],
            "changed_params": changed_params,
            "direction_label": matrix_row["direction_label"],
            "changes": changes,
        },
        "state_before": {
            "design": _state(parent, "parent"),
            "key_performance": {
                "b1p_at_10cm_mean_uT_per_sqrtW": _get(
                    parent, "b1_signature.b1p_at_10cm_mean_uT_per_sqrtW"
                ),
                "sar10g_max_W_per_kg_per_W": _get(
                    parent, "sar_signature.sar10g_max_W_per_kg_per_W"
                ),
                "sar_efficiency_10cm": _get(
                    parent, "sar_signature.sar_efficiency_10cm"
                ),
                "cov_roi": _get(parent, "b1_signature.cov_roi"),
                "half_value_depth_mm": _get(
                    parent, "b1_signature.half_value_depth_mm"
                ),
            },
        },
        "outcome": {
            "metrics": outcome,
            "sar_hotspot_shift_mm": hotspot_shift,
        },
        "effect_labels": labels,
        "tradeoff_summary": _tradeoff_summary(outcome),
        "objective_agnostic": True,
        "action_feasible": child["qa"].get("qa_status") == "validated",
        "evidence": {
            "parent_record_id": parent["record_id"],
            "child_record_id": child["record_id"],
            "child_qa_status": child["qa"].get("qa_status"),
        },
    }


def _target_value(delta_card: dict[str, Any], parameter: str) -> Any:
    return delta_card["action"]["changes"][parameter]["after"]


def _matching_single_delta(
    interaction: dict[str, Any],
    parameter: str,
    single_cards: list[dict[str, Any]],
) -> dict[str, Any] | None:
    expected = _target_value(interaction, parameter)
    matches = [
        card
        for card in single_cards
        if card["parent_record_id"] == interaction["parent_record_id"]
        and card["action"]["changed_params"] == [parameter]
        and _target_value(card, parameter) == expected
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError(
            f"{interaction['child_case_matrix_id']}: expected one single-axis "
            f"component for {parameter} -> {expected}, found {len(matches)}"
        )
    return matches[0]


def make_interaction_card(
    delta_card: dict[str, Any], single_cards: list[dict[str, Any]]
) -> dict[str, Any]:
    changed_params = delta_card["action"]["changed_params"]
    if len(changed_params) != 2:
        raise ValueError(
            f"{delta_card['child_case_matrix_id']}: interaction must change two parameters"
        )
    components = [
        _matching_single_delta(delta_card, parameter, single_cards)
        for parameter in changed_params
    ]
    resolved_components = [card for card in components if card is not None]
    missing_component_params = [
        parameter
        for parameter, card in zip(changed_params, components)
        if card is None
    ]

    metric_effects: dict[str, dict[str, Any]] = {}
    dominant_metrics: list[str] = []
    for metric in METRICS:
        actual = delta_card["outcome"]["metrics"][metric.name]["delta"]
        if missing_component_params:
            metric_effects[metric.name] = {
                "actual_joint_delta": actual,
                "additive_expected_delta": None,
                "interaction_residual": None,
                "nonlinearity_ratio": None,
                "unit": metric.unit,
            }
            continue
        component_deltas = [
            card["outcome"]["metrics"][metric.name]["delta"]
            for card in resolved_components
        ]
        if actual is None or any(value is None for value in component_deltas):
            metric_effects[metric.name] = {
                "actual_joint_delta": actual,
                "additive_expected_delta": None,
                "interaction_residual": None,
                "nonlinearity_ratio": None,
                "unit": metric.unit,
            }
            continue
        expected = sum(component_deltas)
        residual = actual - expected
        denominator = sum(abs(value) for value in component_deltas)
        ratio = abs(residual) / denominator if denominator > 1e-15 else None
        metric_effects[metric.name] = {
            "actual_joint_delta": _round(actual),
            "additive_expected_delta": _round(expected),
            "interaction_residual": _round(residual),
            "nonlinearity_ratio": _round(ratio),
            "unit": metric.unit,
        }
        parent_value = delta_card["outcome"]["metrics"][metric.name]["before"]
        residual_pct = (
            abs(residual) / abs(float(parent_value)) * 100.0
            if _as_float(parent_value) not in (None, 0.0)
            else 0.0
        )
        if (
            ratio is not None
            and ratio >= INTERACTION_RATIO_THRESHOLD
            and residual_pct >= RELATIVE_EFFECT_THRESHOLD_PCT
        ):
            dominant_metrics.append(metric.name)

    return {
        "schema_version": INTERACTION_CARD_SCHEMA,
        "card_type": "two_parameter_interaction",
        "card_id": f"interaction::{delta_card['child_record_id']}",
        "parent_record_id": delta_card["parent_record_id"],
        "child_record_id": delta_card["child_record_id"],
        "child_case_matrix_id": delta_card["child_case_matrix_id"],
        "family": delta_card["family"],
        "joint_action": delta_card["action"],
        "component_delta_card_ids": [
            card["card_id"] for card in resolved_components
        ],
        "missing_component_params": missing_component_params,
        "interaction_analysis_status": (
            "partial_missing_single_axis_components"
            if missing_component_params
            else "complete_additive_decomposition"
        ),
        "metric_effects": metric_effects,
        "dominant_interaction_metrics": dominant_metrics,
        "interaction_detected": (
            None if missing_component_params else bool(dominant_metrics)
        ),
        "interpretation_rule": (
            "residual = actual_joint_delta - sum(single_parameter_deltas); "
            "dominant requires nonlinearity_ratio >= 0.25 and residual >= 2% "
            "of the parent metric magnitude"
        ),
    }


def _validate_manifest_row(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for field, expected in QA_GATE.items():
        actual: Any = row.get(field)
        if isinstance(expected, bool):
            actual = str(actual).strip().lower() == "true"
        if actual != expected:
            errors.append(f"{field}={row.get(field)!r}, expected {expected!r}")
    return errors


def _load_matrix_rows(matrix_dir: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for name in ("RD_case_matrix.csv", "FD_case_matrix.csv"):
        path = matrix_dir / name
        for row in _read_csv(path):
            case_id = row["case_matrix_id"]
            if case_id in rows:
                raise ValueError(f"duplicate case_matrix_id in matrices: {case_id}")
            rows[case_id] = row
    return rows


def _load_records(
    results_root: Path,
    matrix_rows: dict[str, dict[str, str]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, str]],
    dict[str, tuple[Path, Path]],
]:
    manifest_path = results_root / "manifest.csv"
    manifest_rows = _read_csv(manifest_path)
    records: dict[str, dict[str, Any]] = {}
    rows_by_record: dict[str, dict[str, str]] = {}
    paths_by_record: dict[str, tuple[Path, Path]] = {}
    failures: list[str] = []

    for row in manifest_rows:
        record_id = row["record_id"]
        case_id = row["case_matrix_id"]
        gate_errors = _validate_manifest_row(row)
        if gate_errors:
            failures.append(f"{case_id}: " + "; ".join(gate_errors))
            continue
        matrix_row = matrix_rows.get(case_id)
        if matrix_row is None:
            failures.append(f"{case_id}: absent from canonical RD/FD matrices")
            continue
        global_path = results_root / "records" / f"{record_id}.json"
        local_path = (
            results_root / case_id / "cases" / record_id / "output" / "record.json"
        )
        if not global_path.exists() or not local_path.exists():
            failures.append(
                f"{case_id}: missing global/local record "
                f"({global_path.exists()=}, {local_path.exists()=})"
            )
            continue
        global_record = _read_json(global_path)
        local_record = _read_json(local_path)
        if global_record != local_record:
            failures.append(f"{case_id}: global and local records differ")
            continue
        if global_record.get("record_id") != record_id:
            failures.append(f"{case_id}: record_id mismatch in JSON")
            continue
        if global_record.get("case_matrix_id") != case_id:
            failures.append(f"{case_id}: case_matrix_id mismatch in JSON")
            continue
        if record_id in records:
            failures.append(f"{case_id}: duplicate record_id {record_id}")
            continue
        records[record_id] = global_record
        rows_by_record[record_id] = matrix_row
        paths_by_record[record_id] = (global_path, local_path)

    if failures:
        preview = "\n".join(f"  - {item}" for item in failures[:20])
        more = f"\n  ... and {len(failures) - 20} more" if len(failures) > 20 else ""
        raise ValueError(f"QA/input validation failed:\n{preview}{more}")
    if len(records) != len(manifest_rows):
        raise ValueError(
            f"loaded {len(records)} records from {len(manifest_rows)} manifest rows"
        )
    return records, rows_by_record, paths_by_record


def compile_cards(
    repo_root: Path,
    results_root: Path,
    matrix_dir: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    matrix_rows = _load_matrix_rows(matrix_dir)
    records, rows_by_record, paths_by_record = _load_records(results_root, matrix_rows)

    ordered_ids = sorted(
        records,
        key=lambda record_id: (
            records[record_id]["geometry"]["family"],
            records[record_id]["case_matrix_id"],
        ),
    )
    case_cards = [
        make_case_card(
            records[record_id],
            rows_by_record[record_id],
            paths_by_record[record_id][0],
            repo_root,
        )
        for record_id in ordered_ids
    ]

    case_id_to_record = {
        record["case_matrix_id"]: record for record in records.values()
    }
    delta_cards: list[dict[str, Any]] = []
    for record_id in ordered_ids:
        row = rows_by_record[record_id]
        if row["role"] not in {"perturbation", "interaction"}:
            continue
        parent_case_id = row.get("parent_case_matrix_id")
        parent = case_id_to_record.get(parent_case_id or "")
        if parent is None:
            raise ValueError(
                f"{row['case_matrix_id']}: missing parent record for {parent_case_id}"
            )
        delta_cards.append(make_delta_card(parent, records[record_id], row))

    single_cards = [
        card
        for card in delta_cards
        if card["action"]["action_type"] == "single_param_perturbation"
    ]
    interaction_deltas = [
        card
        for card in delta_cards
        if card["action"]["action_type"] == "two_param_interaction"
    ]
    interaction_cards = [
        make_interaction_card(card, single_cards) for card in interaction_deltas
    ]

    delta_by_child = {card["child_record_id"]: card for card in delta_cards}
    interaction_by_child = {
        card["child_record_id"]: card for card in interaction_cards
    }
    resolved_output_dir = output_dir or results_root / "learning"
    prompt_path = _repo_relative(
        resolved_output_dir / "cases_prompt_cards.jsonl", repo_root
    )
    updated_records: dict[str, dict[str, Any]] = {}
    for record_id in ordered_ids:
        record = json.loads(json.dumps(records[record_id]))
        card = next(item for item in case_cards if item["record_id"] == record_id)
        labels = list(delta_by_child.get(record_id, {}).get("effect_labels", []))
        interaction = interaction_by_child.get(record_id)
        if interaction and interaction["interaction_detected"]:
            labels.append("nonlinear_interaction_detected")
        record["learning_card"]["field_summary_text"] = card["summary_text"]
        record["learning_card"]["dominant_effect_labels"] = labels
        record["learning_card"]["prompt_card_jsonl_path"] = prompt_path
        updated_records[record_id] = record

    prompt_cards = [*case_cards, *delta_cards, *interaction_cards]
    counts_by_family: dict[str, int] = {}
    counts_by_role: dict[str, int] = {}
    for record_id in ordered_ids:
        family = records[record_id]["geometry"]["family"]
        role = rows_by_record[record_id]["role"]
        counts_by_family[family] = counts_by_family.get(family, 0) + 1
        counts_by_role[role] = counts_by_role.get(role, 0) + 1

    catalog = {
        "schema_version": CATALOG_SCHEMA,
        "source": {
            "manifest": _repo_relative(results_root / "manifest.csv", repo_root),
            "matrices": [
                _repo_relative(matrix_dir / "RD_case_matrix.csv", repo_root),
                _repo_relative(matrix_dir / "FD_case_matrix.csv", repo_root),
            ],
            "qa_gate": QA_GATE,
        },
        "counts": {
            "case_cards": len(case_cards),
            "delta_cards": len(delta_cards),
            "single_parameter_delta_cards": len(single_cards),
            "interaction_delta_cards": len(interaction_deltas),
            "interaction_cards": len(interaction_cards),
            "complete_interaction_cards": sum(
                card["interaction_analysis_status"]
                == "complete_additive_decomposition"
                for card in interaction_cards
            ),
            "partial_interaction_cards": sum(
                card["interaction_analysis_status"]
                != "complete_additive_decomposition"
                for card in interaction_cards
            ),
            "prompt_cards_total": len(prompt_cards),
            "by_family": counts_by_family,
            "by_role": counts_by_role,
        },
        "files": {
            "global_cases": "cases_global.jsonl",
            "delta_experiences": "cases_delta.jsonl",
            "interaction_effects": "cases_interaction.jsonl",
            "all_prompt_cards": "cases_prompt_cards.jsonl",
        },
        "retrieval_contract": {
            "first_filter": [
                "card_type",
                "family",
                "action.changed_params",
                "state.geometry",
                "state.bridge.mode",
            ],
            "then_rank": [
                "normalized design-parameter distance",
                "goal-relevant outcome direction",
                "QA/evidence completeness",
            ],
            "recommended_context": {
                "global_case_cards": "2-4",
                "parameter_delta_cards": "3-6",
                "interaction_cards": "0-2 when changing two parameters",
            },
            "note": (
                "Cards are objective-agnostic evidence. The optimization agent must "
                "apply the runtime objective and validate every proposed design in CST."
            ),
        },
    }

    return {
        "case_cards": case_cards,
        "delta_cards": delta_cards,
        "interaction_cards": interaction_cards,
        "prompt_cards": prompt_cards,
        "catalog": catalog,
        "updated_records": updated_records,
        "record_paths": paths_by_record,
    }


def write_compilation(
    compilation: dict[str, Any],
    output_dir: Path,
    update_records: bool,
) -> dict[str, Any]:
    changed_files: list[str] = []
    outputs = {
        output_dir / "cases_global.jsonl": _jsonl(compilation["case_cards"]),
        output_dir / "cases_delta.jsonl": _jsonl(compilation["delta_cards"]),
        output_dir / "cases_interaction.jsonl": _jsonl(
            compilation["interaction_cards"]
        ),
        output_dir / "cases_prompt_cards.jsonl": _jsonl(
            compilation["prompt_cards"]
        ),
    }
    for path, text in outputs.items():
        if _write_text_if_changed(path, text):
            changed_files.append(str(path))
    catalog_path = output_dir / "catalog.json"
    if _write_json_if_changed(catalog_path, compilation["catalog"]):
        changed_files.append(str(catalog_path))

    record_files_changed = 0
    if update_records:
        for record_id, record in compilation["updated_records"].items():
            global_path, local_path = compilation["record_paths"][record_id]
            global_changed = _write_json_if_changed(global_path, record)
            local_changed = _write_json_if_changed(local_path, record)
            record_files_changed += int(global_changed) + int(local_changed)
            global_text = global_path.read_text(encoding="utf-8")
            local_text = local_path.read_text(encoding="utf-8")
            if _sha256_text(global_text) != _sha256_text(local_text):
                raise RuntimeError(f"{record_id}: global/local hash mismatch after update")

    return {
        "learning_files_changed": len(changed_files),
        "record_files_changed": record_files_changed,
        "changed_learning_files": changed_files,
    }


def _resolve_path(value: str | None, default: Path, repo_root: Path) -> Path:
    if value is None:
        return default
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile validated D1/D2 records into few-shot learning cards."
    )
    parser.add_argument(
        "--repo-root",
        help="Repository root; defaults to the root inferred from this script.",
    )
    parser.add_argument(
        "--results-root",
        help="Data-prep results root; defaults to results_data_prep.",
    )
    parser.add_argument(
        "--matrix-dir",
        help="Directory containing canonical RD_case_matrix.csv and FD_case_matrix.csv.",
    )
    parser.add_argument(
        "--output-dir",
        help="Learning output directory; defaults to <results-root>/learning.",
    )
    parser.add_argument(
        "--no-update-records",
        action="store_true",
        help="Generate aggregate cards without backfilling record learning_card fields.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and compile in memory without writing files.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    results_root = _resolve_path(
        args.results_root, repo_root / "results_data_prep", repo_root
    ).resolve()
    matrix_dir = _resolve_path(
        args.matrix_dir,
        repo_root
        / ".agents"
        / "skills"
        / "mri-coil-design-workflow"
        / "recipes"
        / "data-prep"
        / "complete-case(D1)",
        repo_root,
    ).resolve()
    output_dir = _resolve_path(
        args.output_dir, results_root / "learning", repo_root
    ).resolve()

    try:
        compilation = compile_cards(
            repo_root, results_root, matrix_dir, output_dir=output_dir
        )
        write_summary = {
            "learning_files_changed": 0,
            "record_files_changed": 0,
            "changed_learning_files": [],
        }
        if not args.dry_run:
            write_summary = write_compilation(
                compilation,
                output_dir,
                update_records=not args.no_update_records,
            )
        summary = {
            "status": "validated_dry_run" if args.dry_run else "written",
            "output_dir": _repo_relative(output_dir, repo_root),
            **compilation["catalog"]["counts"],
            **write_summary,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
