"""Built-in analyses for common electrical-engineering bench records."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .stats import interpolate_crossing, linear_regression, summary
from .uncertainty import from_records
from .workspace import Workspace, utc_now


def _numeric_rows(path: Path) -> tuple[list[str], list[dict[str, float]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = []
        for row_number, row in enumerate(reader, start=2):
            converted = {}
            for field in fields:
                value = (row.get(field) or "").strip()
                if value == "":
                    raise ValueError(f"{path.name}:{row_number}: empty value in {field}")
                try:
                    converted[field] = float(value)
                except ValueError as error:
                    raise ValueError(
                        f"{path.name}:{row_number}: non-numeric value in {field}: {value}"
                    ) from error
            rows.append(converted)
    if not rows:
        raise ValueError(f"{path.name}: no data rows")
    return fields, rows


def _frequency_response(rows: list[dict[str, float]]) -> dict[str, Any]:
    required = {"frequency_hz", "vin_v", "vout_v"}
    missing = required - rows[0].keys()
    if missing:
        raise ValueError(f"frequency response needs columns: {', '.join(sorted(required))}")
    ordered = sorted(rows, key=lambda row: row["frequency_hz"])
    frequencies = [row["frequency_hz"] for row in ordered]
    gains = []
    gain_db = []
    for row in ordered:
        if row["vin_v"] == 0.0:
            raise ValueError("vin_v may not be zero")
        gain = abs(row["vout_v"] / row["vin_v"])
        gains.append(gain)
        gain_db.append(20.0 * math.log10(gain) if gain > 0 else -math.inf)
    passband_count = max(1, min(5, len(gain_db) // 5 or 1))
    passband_db = sum(gain_db[:passband_count]) / passband_count
    cutoff_target = passband_db - 3.010299956639812
    log_frequencies = [math.log10(value) for value in frequencies]
    cutoff_log = interpolate_crossing(log_frequencies, gain_db, cutoff_target)
    cutoff = 10**cutoff_log if cutoff_log is not None else None
    return {
        "kind": "frequency_response",
        "observations": len(rows),
        "passband_gain_db": passband_db,
        "cutoff_target_db": cutoff_target,
        "cutoff_frequency_hz": cutoff,
        "peak_gain": max(gains),
        "points": [
            {
                "frequency_hz": frequency,
                "gain": gain,
                "gain_db": level,
                **({"phase_deg": row["phase_deg"]} if "phase_deg" in row else {}),
            }
            for frequency, gain, level, row in zip(
                frequencies, gains, gain_db, ordered, strict=True
            )
        ],
    }


def _efficiency(rows: list[dict[str, float]]) -> dict[str, Any]:
    required = {"vin_v", "iin_a", "vout_v", "iout_a"}
    missing = required - rows[0].keys()
    if missing:
        raise ValueError(f"efficiency analysis needs columns: {', '.join(sorted(required))}")
    points = []
    for row in rows:
        input_power = row["vin_v"] * row["iin_a"]
        output_power = row["vout_v"] * row["iout_a"]
        if input_power <= 0:
            raise ValueError("input power must be positive")
        points.append(
            {
                "input_power_w": input_power,
                "output_power_w": output_power,
                "efficiency_percent": 100.0 * output_power / input_power,
                "loss_w": input_power - output_power,
                **({"load_ohm": row["load_ohm"]} if "load_ohm" in row else {}),
            }
        )
    peak = max(points, key=lambda item: item["efficiency_percent"])
    return {
        "kind": "power_efficiency",
        "observations": len(rows),
        "peak_efficiency_percent": peak["efficiency_percent"],
        "peak_output_power_w": peak["output_power_w"],
        "mean_efficiency_percent": summary([point["efficiency_percent"] for point in points])[
            "mean"
        ],
        "points": points,
    }


def _linear_calibration(rows: list[dict[str, float]]) -> dict[str, Any]:
    required = {"reference", "observed"}
    missing = required - rows[0].keys()
    if missing:
        raise ValueError(f"linear calibration needs columns: {', '.join(sorted(required))}")
    result = linear_regression(
        [row["reference"] for row in rows], [row["observed"] for row in rows]
    )
    errors = [row["observed"] - row["reference"] for row in rows]
    return {
        "kind": "linear_calibration",
        "observations": len(rows),
        **result,
        "error_summary": summary(errors),
        "points": rows,
    }


def _summaries(fields: list[str], rows: list[dict[str, float]]) -> dict[str, Any]:
    return {
        "kind": "column_summary",
        "observations": len(rows),
        "columns": {field: summary([row[field] for row in rows]) for field in fields},
    }


def detect_kind(fields: list[str]) -> str:
    field_set = set(fields)
    if {"frequency_hz", "vin_v", "vout_v"} <= field_set:
        return "frequency_response"
    if {"vin_v", "iin_a", "vout_v", "iout_a"} <= field_set:
        return "power_efficiency"
    if {"reference", "observed"} <= field_set:
        return "linear_calibration"
    return "column_summary"


def analyze_run(
    workspace: str | Path | Workspace,
    run_id: str,
    *,
    kind: str = "auto",
    uncertainty_components: list[dict] | None = None,
    coverage_factor: float = 2.0,
) -> dict[str, Any]:
    bench = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    bench.require()
    run_path = bench.root / "runs" / f"{run_id}.json"
    if not run_path.is_file():
        raise FileNotFoundError(f"run not found: {run_id}")
    run = read_json(run_path)
    files = []
    for relative in run["raw_files"]:
        path = bench.root / relative
        fields, rows = _numeric_rows(path)
        selected_kind = detect_kind(fields) if kind == "auto" else kind
        if selected_kind == "frequency_response":
            result = _frequency_response(rows)
        elif selected_kind == "power_efficiency":
            result = _efficiency(rows)
        elif selected_kind == "linear_calibration":
            result = _linear_calibration(rows)
        elif selected_kind == "column_summary":
            result = _summaries(fields, rows)
        else:
            raise ValueError(f"unsupported analysis kind: {selected_kind}")
        files.append({"path": relative, "columns": fields, "result": result})
    record: dict[str, Any] = {
        "schema": "benchlineage/analysis/v1",
        "run_id": run_id,
        "study_id": run["study_id"],
        "created_at": utc_now(),
        "files": files,
    }
    if uncertainty_components:
        record["uncertainty_budget"] = from_records(
            uncertainty_components, coverage_factor=coverage_factor
        )
    output = bench.root / "analysis" / f"{run_id}.json"
    write_json(output, record)
    return record
