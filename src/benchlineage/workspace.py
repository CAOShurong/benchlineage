"""Filesystem workspace and durable experiment records."""

from __future__ import annotations

import csv
import datetime as dt
from email.utils import parseaddr
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .io import read_json, safe_identifier, write_json

FORMAT_VERSION = "1.0"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def valid_email(value: str) -> bool:
    """Accept a plain address with one non-empty local part and a dotted domain."""
    if not value or any(character.isspace() for character in value):
        return False
    display_name, address = parseaddr(value)
    if display_name or address != value or address.count("@") != 1:
        return False
    local, domain = address.rsplit("@", 1)
    return bool(local and "." in domain and not domain.startswith(".") and not domain.endswith("."))


def normalize_data_license(
    url: Any = "",
    name: Any = "",
    description: Any = "",
) -> dict[str, str]:
    """Validate and normalize an optional workspace data-license declaration."""

    values: dict[str, str] = {}
    for field, value in (
        ("data license URL", url),
        ("data license name", name),
        ("data license description", description),
    ):
        if value is None:
            values[field] = ""
        elif isinstance(value, str):
            values[field] = value.strip()
        else:
            raise ValueError(f"{field} must be a string")

    license_url = values["data license URL"]
    license_name = values["data license name"]
    license_description = values["data license description"]
    if not license_url:
        if license_name or license_description:
            raise ValueError("data license URL is required when license details are supplied")
        return {}

    parsed = urlparse(license_url)
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(
            "data license URL must be an absolute HTTP(S) URL without embedded credentials"
        )

    result = {"data_license_url": license_url}
    if license_name:
        result["data_license_name"] = license_name
    if license_description:
        result["data_license_description"] = license_description
    return result


class Workspace:
    """A transparent directory of JSON metadata and raw measurement files."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    @property
    def metadata_path(self) -> Path:
        return self.root / "benchlineage.json"

    def initialize(
        self,
        *,
        title: str,
        owner: str,
        owner_email: str = "",
        owner_given_name: str = "",
        owner_family_name: str = "",
        data_license_url: str = "",
        data_license_name: str = "",
        data_license_description: str = "",
    ) -> dict[str, Any]:
        if self.metadata_path.exists():
            raise FileExistsError(f"workspace already exists: {self.root}")
        for directory in (
            "instruments",
            "calibrations",
            "studies",
            "runs",
            "data/raw",
            "analysis",
            "reports",
            "seals",
        ):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        metadata = {
            "format": "benchlineage-workspace",
            "format_version": FORMAT_VERSION,
            "title": title.strip(),
            "owner": owner.strip(),
            "created_at": utc_now(),
            "principles": [
                "raw data is immutable evidence",
                "analysis is derived and replaceable",
                "instrument identity and calibration are explicit",
                "sealed records are content-addressed",
            ],
        }
        optional_owner_fields = {
            "owner_email": owner_email.strip(),
            "owner_given_name": owner_given_name.strip(),
            "owner_family_name": owner_family_name.strip(),
        }
        if optional_owner_fields["owner_email"] and not valid_email(
            optional_owner_fields["owner_email"]
        ):
            raise ValueError("owner email must be a valid plain email address")
        metadata.update({key: value for key, value in optional_owner_fields.items() if value})
        metadata.update(
            normalize_data_license(
                data_license_url,
                data_license_name,
                data_license_description,
            )
        )
        if not metadata["title"] or not metadata["owner"]:
            raise ValueError("title and owner are required")
        write_json(self.metadata_path, metadata)
        return metadata

    def require(self) -> dict[str, Any]:
        if not self.metadata_path.is_file():
            raise FileNotFoundError(f"not a BenchLineage workspace: {self.root}")
        metadata = read_json(self.metadata_path)
        if metadata.get("format") != "benchlineage-workspace":
            raise ValueError("unsupported workspace metadata")
        for field in ("title", "owner"):
            if not isinstance(metadata.get(field), str) or not metadata[field].strip():
                raise ValueError(f"workspace {field} is required")
        return metadata

    def add_instrument(
        self,
        *,
        instrument_id: str,
        kind: str,
        manufacturer: str,
        model: str,
        serial: str,
        asset_tag: str = "",
        notes: str = "",
    ) -> dict:
        self.require()
        instrument_id = safe_identifier(instrument_id, field="instrument id")
        record = {
            "schema": "benchlineage/instrument/v1",
            "id": instrument_id,
            "kind": kind.strip(),
            "manufacturer": manufacturer.strip(),
            "model": model.strip(),
            "serial": serial.strip(),
            "asset_tag": asset_tag.strip(),
            "notes": notes.strip(),
            "created_at": utc_now(),
        }
        required = ("kind", "manufacturer", "model", "serial")
        if any(not record[field] for field in required):
            raise ValueError("kind, manufacturer, model, and serial are required")
        path = self.root / "instruments" / f"{instrument_id}.json"
        if path.exists():
            raise FileExistsError(f"instrument already exists: {instrument_id}")
        write_json(path, record)
        return record

    def add_calibration(
        self,
        *,
        calibration_id: str,
        instrument_id: str,
        performed_at: str,
        due_at: str,
        certificate: str,
        standard_uncertainty: float,
        unit: str,
        coverage_factor: float = 2.0,
        status: str = "valid",
    ) -> dict:
        self.require()
        calibration_id = safe_identifier(calibration_id, field="calibration id")
        instrument_id = safe_identifier(instrument_id, field="instrument id")
        if not (self.root / "instruments" / f"{instrument_id}.json").exists():
            raise ValueError(f"unknown instrument: {instrument_id}")
        if standard_uncertainty < 0:
            raise ValueError("standard uncertainty may not be negative")
        if coverage_factor <= 0:
            raise ValueError("coverage factor must be positive")
        record = {
            "schema": "benchlineage/calibration/v1",
            "id": calibration_id,
            "instrument_id": instrument_id,
            "performed_at": performed_at,
            "due_at": due_at,
            "certificate": certificate.strip(),
            "standard_uncertainty": float(standard_uncertainty),
            "unit": unit.strip(),
            "coverage_factor": float(coverage_factor),
            "status": status,
            "created_at": utc_now(),
        }
        path = self.root / "calibrations" / f"{calibration_id}.json"
        if path.exists():
            raise FileExistsError(f"calibration already exists: {calibration_id}")
        write_json(path, record)
        return record

    def create_study(
        self,
        *,
        study_id: str,
        title: str,
        objective: str,
        hypothesis: str,
        protocol: str,
        tags: list[str] | None = None,
    ) -> dict:
        self.require()
        study_id = safe_identifier(study_id, field="study id")
        record = {
            "schema": "benchlineage/study/v1",
            "id": study_id,
            "title": title.strip(),
            "objective": objective.strip(),
            "hypothesis": hypothesis.strip(),
            "protocol": protocol.strip(),
            "tags": sorted(set(tags or [])),
            "created_at": utc_now(),
        }
        if not record["title"] or not record["objective"] or not record["protocol"]:
            raise ValueError("study title, objective, and protocol are required")
        path = self.root / "studies" / f"{study_id}.json"
        if path.exists():
            raise FileExistsError(f"study already exists: {study_id}")
        write_json(path, record)
        return record

    def add_run(
        self,
        *,
        run_id: str,
        study_id: str,
        operator: str,
        started_at: str,
        instruments: list[str],
        raw_files: list[str],
        conditions: dict[str, Any],
        deviations: list[str] | None = None,
        notes: str = "",
    ) -> dict:
        self.require()
        run_id = safe_identifier(run_id, field="run id")
        study_id = safe_identifier(study_id, field="study id")
        if not (self.root / "studies" / f"{study_id}.json").exists():
            raise ValueError(f"unknown study: {study_id}")
        normalized_instruments = [
            safe_identifier(value, field="instrument id") for value in instruments
        ]
        unknown = [
            value
            for value in normalized_instruments
            if not (self.root / "instruments" / f"{value}.json").exists()
        ]
        if unknown:
            raise ValueError(f"unknown instruments: {', '.join(unknown)}")
        normalized_files = []
        for raw_file in raw_files:
            path = (self.root / raw_file).resolve()
            try:
                relative = path.relative_to(self.root).as_posix()
            except ValueError as error:
                raise ValueError(f"raw file escapes workspace: {raw_file}") from error
            if not path.is_file():
                raise FileNotFoundError(f"raw file not found: {relative}")
            normalized_files.append(relative)
        record = {
            "schema": "benchlineage/run/v1",
            "id": run_id,
            "study_id": study_id,
            "operator": operator.strip(),
            "started_at": started_at,
            "instruments": normalized_instruments,
            "raw_files": normalized_files,
            "conditions": conditions,
            "deviations": deviations or [],
            "notes": notes.strip(),
            "recorded_at": utc_now(),
        }
        if not record["operator"]:
            raise ValueError("operator is required")
        path = self.root / "runs" / f"{run_id}.json"
        if path.exists():
            raise FileExistsError(f"run already exists: {run_id}")
        write_json(path, record)
        return record

    def copy_csv(
        self,
        source: str | Path,
        *,
        destination_name: str,
        required_columns: list[str] | None = None,
    ) -> Path:
        """Validate and copy a CSV as normalized UTF-8 evidence."""
        self.require()
        destination_name = safe_identifier(destination_name, field="data name")
        source_path = Path(source)
        with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("CSV needs a header row")
            fields = [field.strip() for field in reader.fieldnames]
            if len(set(fields)) != len(fields):
                raise ValueError("CSV column names must be unique")
            missing = sorted(set(required_columns or []) - set(fields))
            if missing:
                raise ValueError(f"CSV is missing columns: {', '.join(missing)}")
            rows = list(reader)
        if not rows:
            raise ValueError("CSV needs at least one data row")
        destination = self.root / "data" / "raw" / f"{destination_name}.csv"
        if destination.exists():
            raise FileExistsError(f"raw data already exists: {destination.name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return destination

    def records(self, category: str) -> list[dict]:
        self.require()
        directory = self.root / category
        if not directory.is_dir():
            raise ValueError(f"unknown record category: {category}")
        return [read_json(path) for path in sorted(directory.glob("*.json"))]
