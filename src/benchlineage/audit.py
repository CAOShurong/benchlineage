"""Cross-artifact checks for BenchLineage workspaces."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from .io import read_json
from .provenance import latest_seal, verify_seal
from .workspace import Workspace, normalize_data_license, valid_email


def _parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed


def audit_workspace(workspace: str | Path | Workspace) -> dict[str, Any]:
    bench = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def error(code: str, message: str) -> None:
        errors.append({"code": code, "message": message})

    def warning(code: str, message: str) -> None:
        warnings.append({"code": code, "message": message})

    try:
        metadata = bench.require()
    except (FileNotFoundError, ValueError) as exception:
        return {
            "status": "fail",
            "errors": [{"code": "workspace.invalid", "message": str(exception)}],
            "warnings": [],
            "counts": {},
        }
    if metadata.get("format_version") != "1.0":
        warning(
            "workspace.version", f"unrecognized format version: {metadata.get('format_version')}"
        )
    if metadata.get("owner_email") and not valid_email(str(metadata["owner_email"])):
        error("workspace.owner.email", "workspace owner email is invalid")
    try:
        normalize_data_license(
            metadata.get("data_license_url"),
            metadata.get("data_license_name"),
            metadata.get("data_license_description"),
        )
    except ValueError as exception:
        error("workspace.data_license", str(exception))

    categories = ("instruments", "calibrations", "studies", "runs", "analysis")
    records: dict[str, dict[str, dict]] = {}
    for category in categories:
        records[category] = {}
        for path in sorted((bench.root / category).glob("*.json")):
            try:
                record = read_json(path)
            except Exception as exception:  # noqa: BLE001 - audit must report malformed evidence
                error("json.invalid", f"{path.relative_to(bench.root)}: {exception}")
                continue
            key = str(record.get("id") or record.get("run_id") or path.stem)
            if key in records[category]:
                error("id.duplicate", f"duplicate {category} id: {key}")
            records[category][key] = record

    for calibration_id, record in records["calibrations"].items():
        instrument_id = record.get("instrument_id")
        if instrument_id not in records["instruments"]:
            error(
                "calibration.instrument",
                f"{calibration_id} references unknown instrument {instrument_id}",
            )
        try:
            if _parse_time(record["due_at"]) < _parse_time(record["performed_at"]):
                error("calibration.dates", f"{calibration_id} is due before it was performed")
        except (KeyError, TypeError, ValueError) as exception:
            error("calibration.dates", f"{calibration_id} has invalid dates: {exception}")

    referenced_raw: set[str] = set()
    for run_id, record in records["runs"].items():
        study_id = record.get("study_id")
        if study_id not in records["studies"]:
            error("run.study", f"{run_id} references unknown study {study_id}")
        for instrument_id in record.get("instruments", []):
            if instrument_id not in records["instruments"]:
                error("run.instrument", f"{run_id} references unknown instrument {instrument_id}")
        for relative in record.get("raw_files", []):
            referenced_raw.add(relative)
            path = (bench.root / relative).resolve()
            try:
                path.relative_to(bench.root)
            except ValueError:
                error("run.raw.escape", f"{run_id} raw path escapes workspace: {relative}")
                continue
            if not path.is_file():
                error("run.raw.missing", f"{run_id} raw file is missing: {relative}")
        try:
            run_time = _parse_time(record["started_at"])
        except (KeyError, TypeError, ValueError) as exception:
            error("run.time", f"{run_id} has invalid start time: {exception}")
            continue
        try:
            recorded_time = _parse_time(record.get("recorded_at", record["started_at"]))
        except (KeyError, TypeError, ValueError) as exception:
            error("run.time", f"{run_id} has invalid recorded time: {exception}")
            continue
        if recorded_time < run_time:
            error("run.time.order", f"{run_id} was recorded before it started")
        for instrument_id in record.get("instruments", []):
            candidates = [
                value
                for value in records["calibrations"].values()
                if value.get("instrument_id") == instrument_id and value.get("status") == "valid"
            ]
            covering = []
            for candidate in candidates:
                try:
                    if (
                        _parse_time(candidate["performed_at"])
                        <= run_time
                        <= _parse_time(candidate["due_at"])
                    ):
                        covering.append(candidate)
                except (KeyError, TypeError, ValueError):
                    continue
            if not covering:
                warning(
                    "run.calibration",
                    f"{run_id} has no in-date calibration for {instrument_id}",
                )

    for raw_path in sorted((bench.root / "data" / "raw").glob("**/*")):
        if raw_path.is_file():
            relative = raw_path.relative_to(bench.root).as_posix()
            if relative not in referenced_raw:
                warning("raw.orphan", f"raw file is not referenced by a run: {relative}")

    for analysis_id, record in records["analysis"].items():
        run_id = record.get("run_id")
        if run_id not in records["runs"]:
            error("analysis.run", f"{analysis_id} references unknown run {run_id}")
            continue
        try:
            analysis_time = _parse_time(record["created_at"])
            run_recorded_time = _parse_time(
                records["runs"][run_id].get("recorded_at", records["runs"][run_id]["started_at"])
            )
        except (KeyError, TypeError, ValueError) as exception:
            error("analysis.time", f"{analysis_id} has invalid time metadata: {exception}")
            continue
        if analysis_time < run_recorded_time:
            error("analysis.time.order", f"{analysis_id} was created before its run was recorded")

    seal_result = None
    seal_path = latest_seal(bench)
    if seal_path:
        seal_result = verify_seal(bench, seal_path)
        if not seal_result["valid"]:
            error("seal.invalid", f"{seal_path.name} does not match current evidence")
    else:
        warning("seal.missing", "workspace has not been sealed")

    return {
        "status": "pass" if not errors else "fail",
        "workspace": metadata["title"],
        "counts": {
            category: len(records[category])
            for category in ("instruments", "calibrations", "studies", "runs", "analysis")
        }
        | {"raw_files": len(referenced_raw)},
        "errors": errors,
        "warnings": warnings,
        "seal": seal_result,
    }
