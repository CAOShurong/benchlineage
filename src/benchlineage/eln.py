"""Deterministic ELN Consortium exchange archives built from sealed workspaces."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from collections import Counter
from contextlib import suppress
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, unquote, urlparse

from .audit import audit_workspace
from .io import canonical_json, digest_file, read_json, relative_files
from .provenance import latest_seal, verify_seal
from .workspace import Workspace

ELN_CONTEXT = "https://w3id.org/ro/crate/1.1/context"
ELN_CONFORMS_TO = "https://w3id.org/ro/crate/1.1"
ELN_FORMAT_VERSION = "1.0"
ELN_SHA256_TERM = "https://the.elnconsortium.org/specification/#sha256"
BENCHLINEAGE_URL = "https://github.com/CAOShurong/benchlineage"
BENCHLINEAGE_VERSION = "0.3.1"
MEDIA_TYPES = {
    ".csv": "text/csv",
    ".gz": "application/gzip",
    ".h5": "application/x-hdf5",
    ".hdf5": "application/x-hdf5",
    ".htm": "text/html",
    ".html": "text/html",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".json": "application/json",
    ".mat": "application/x-matlab-data",
    ".mp4": "video/mp4",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".tsv": "text/tab-separated-values",
    ".txt": "text/plain",
    ".wav": "audio/wav",
    ".xml": "application/xml",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".zip": "application/zip",
}


def _file_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _write_file(archive: zipfile.ZipFile, name: str, path: Path) -> None:
    """Stream one member so large evidence files are not loaded into memory."""
    info = _file_info(name)
    info.file_size = path.stat().st_size
    with (
        path.open("rb") as source,
        archive.open(
            info,
            "w",
            force_zip64=info.file_size >= 2_000_000_000,
        ) as destination,
    ):
        shutil.copyfileobj(source, destination, length=1024 * 1024)


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and not name.startswith("/")
        and all(":" not in part for part in path.parts)
    )


def _file_id(relative: str) -> str:
    return "./workspace/" + quote(relative, safe="/-._~")


def _person_id(name: str) -> str:
    digest = hashlib.sha256(name.strip().casefold().encode("utf-8")).hexdigest()[:16]
    return f"#person-{digest}"


def _reference(identifier: str) -> dict[str, str]:
    return {"@id": identifier}


def _references(identifiers: list[str]) -> dict[str, str] | list[dict[str, str]]:
    references = [_reference(identifier) for identifier in identifiers]
    if len(references) == 1:
        return references[0]
    return references


def _media_type(path: Path) -> str:
    return MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")


def _file_description(relative: str) -> str:
    if relative.startswith("data/raw/"):
        return "Raw evidence recorded by the BenchLineage workspace."
    if relative.startswith("analysis/"):
        return "Derived analysis record with explicit source-file lineage."
    if relative.startswith("instruments/"):
        return "Instrument identity record."
    if relative.startswith("calibrations/"):
        return "Instrument calibration record."
    if relative.startswith("studies/"):
        return "Study intent and protocol record."
    if relative.startswith("runs/"):
        return "Experimental run record."
    if relative.startswith("seals/"):
        return "Content-addressed BenchLineage evidence seal."
    if relative.startswith("reports/"):
        return "Self-contained human-readable evidence report."
    return "File preserved from the BenchLineage workspace."


def _load_records(bench: Workspace, category: str) -> list[tuple[Path, dict[str, Any]]]:
    result = []
    for path in sorted((bench.root / category).glob("*.json")):
        result.append((path, read_json(path)))
    return result


def _metadata_document(
    bench: Workspace,
    files: list[Path],
    seal: dict[str, Any],
) -> dict[str, Any]:
    workspace = bench.require()
    owner_name = workspace["owner"]
    owner_id = _person_id(owner_name)
    file_ids: dict[str, str] = {}
    file_entities: list[dict[str, Any]] = []
    tags: set[str] = set()

    for path in files:
        relative = path.relative_to(bench.root).as_posix()
        identifier = _file_id(relative)
        file_ids[relative] = identifier
        file_entities.append(
            {
                "@id": identifier,
                "@type": "File",
                "name": path.name,
                "description": _file_description(relative),
                "encodingFormat": _media_type(path),
                "contentSize": str(path.stat().st_size),
                "sha256": digest_file(path).removeprefix("sha256:"),
            }
        )

    contextual: list[dict[str, Any]] = []
    mentioned_ids: list[str] = []

    owner = {"@id": owner_id, "@type": "Person", "name": owner_name}
    for workspace_field, person_field in (
        ("owner_email", "email"),
        ("owner_given_name", "givenName"),
        ("owner_family_name", "familyName"),
    ):
        if workspace.get(workspace_field):
            owner[person_field] = workspace[workspace_field]
    people: dict[str, dict[str, Any]] = {owner_id: owner}

    instruments: dict[str, dict[str, Any]] = {}
    for _, record in _load_records(bench, "instruments"):
        identifier = f"#instrument-{record['id']}"
        entity: dict[str, Any] = {
            "@id": identifier,
            "@type": "IndividualProduct",
            "name": f"{record['manufacturer']} {record['model']}",
            "identifier": record["id"],
            "manufacturer": record["manufacturer"],
            "model": record["model"],
            "serialNumber": record["serial"],
            "description": record.get("notes") or f"Laboratory {record['kind']}",
        }
        if record.get("asset_tag"):
            entity["productID"] = record["asset_tag"]
        instruments[record["id"]] = entity
        contextual.append(entity)
        mentioned_ids.append(identifier)

    studies: dict[str, dict[str, Any]] = {}
    for _, record in _load_records(bench, "studies"):
        identifier = f"#study-{record['id']}"
        tags.update(str(tag) for tag in record.get("tags", []))
        entity = {
            "@id": identifier,
            "@type": "CreativeWork",
            "name": record["title"],
            "identifier": record["id"],
            "description": record["objective"],
            "abstract": record.get("hypothesis", ""),
            "text": record["protocol"],
            "keywords": ", ".join(record.get("tags", [])),
            "dateCreated": record.get("created_at", workspace["created_at"]),
        }
        studies[record["id"]] = entity
        contextual.append(entity)
        mentioned_ids.append(identifier)

    for _, record in _load_records(bench, "calibrations"):
        identifier = f"#calibration-{record['id']}"
        details = (
            f"Certificate {record['certificate']}; status {record['status']}; "
            f"standard uncertainty {record['standard_uncertainty']} {record['unit']}; "
            f"coverage factor {record['coverage_factor']}; valid from "
            f"{record['performed_at']} through {record['due_at']}."
        )
        entity = {
            "@id": identifier,
            "@type": "CreativeWork",
            "name": f"Calibration {record['id']}",
            "identifier": record["certificate"],
            "about": _reference(f"#instrument-{record['instrument_id']}"),
            "dateCreated": record["performed_at"],
            "expires": record["due_at"],
            "text": details,
        }
        contextual.append(entity)
        mentioned_ids.append(identifier)

    run_records = _load_records(bench, "runs")
    for _, record in run_records:
        operator = record["operator"]
        operator_id = _person_id(operator)
        people.setdefault(
            operator_id,
            {"@id": operator_id, "@type": "Person", "name": operator},
        )
        identifier = f"#run-{record['id']}"
        conditions = canonical_json(record.get("conditions", {}))
        description = f"Conditions: {conditions}."
        if record.get("deviations"):
            description += " Deviations: " + "; ".join(record["deviations"]) + "."
        if record.get("notes"):
            description += " " + record["notes"]
        entity: dict[str, Any] = {
            "@id": identifier,
            "@type": "CreateAction",
            "name": f"Experimental run {record['id']}",
            "agent": _reference(operator_id),
            "object": _reference(f"#study-{record['study_id']}"),
            "startTime": record["started_at"],
            "endTime": record.get("recorded_at", record["started_at"]),
            "description": description,
            "actionStatus": _reference("http://schema.org/CompletedActionStatus"),
        }
        instrument_ids = [
            f"#instrument-{instrument_id}" for instrument_id in record.get("instruments", [])
        ]
        if instrument_ids:
            entity["instrument"] = _references(instrument_ids)
        result_ids = [file_ids[path] for path in record.get("raw_files", []) if path in file_ids]
        if result_ids:
            entity["result"] = _references(result_ids)
        contextual.append(entity)
        mentioned_ids.append(identifier)

    software_id = "https://pypi.org/project/benchlineage/"
    software = {
        "@id": software_id,
        "@type": "SoftwareApplication",
        "name": "BenchLineage",
        "url": BENCHLINEAGE_URL,
        "version": BENCHLINEAGE_VERSION,
    }
    contextual.append(software)
    mentioned_ids.append(software_id)

    for path, record in _load_records(bench, "analysis"):
        run_id = record["run_id"]
        raw_ids: list[str] = []
        for file_record in record.get("files", []):
            relative = file_record.get("path")
            if relative in file_ids:
                raw_ids.append(file_ids[relative])
        analysis_relative = path.relative_to(bench.root).as_posix()
        entity: dict[str, Any] = {
            "@id": f"#analysis-{path.stem}",
            "@type": "CreateAction",
            "name": f"BenchLineage analysis for {run_id}",
            "instrument": _reference(software_id),
            "result": _reference(file_ids[analysis_relative]),
            "endTime": record.get("created_at", seal["created_at"]),
            "description": f"Derived analysis linked to run {run_id}.",
            "actionStatus": _reference("http://schema.org/CompletedActionStatus"),
        }
        if raw_ids:
            entity["object"] = _references(raw_ids)
        contextual.append(entity)
        mentioned_ids.append(entity["@id"])

    contextual.extend(people.values())
    for person_id in people:
        if person_id not in mentioned_ids:
            mentioned_ids.append(person_id)

    study_count = len(studies)
    run_count = len(run_records)
    summary = (
        f"<p>BenchLineage workspace containing {study_count} studies and {run_count} "
        "experimental runs. The archive preserves the original records, raw files, analyses, "
        "reports, and content-addressed seals.</p>"
    )
    descriptor = {
        "@id": "ro-crate-metadata.json",
        "@type": "CreativeWork",
        "about": _reference("./"),
        "conformsTo": _reference(ELN_CONFORMS_TO),
        "dateCreated": seal["created_at"],
        "sdPublisher": _reference(BENCHLINEAGE_URL),
        "version": ELN_FORMAT_VERSION,
    }
    root_dataset = {
        "@id": "./",
        "@type": "Dataset",
        "name": workspace["title"],
        "description": "An ELN Consortium exchange archive exported by BenchLineage.",
        "license": "No data license was declared; contact the workspace author before reuse.",
        "author": _reference(owner_id),
        "dateCreated": workspace["created_at"],
        "dateModified": seal["created_at"],
        "datePublished": seal["created_at"],
        "identifier": seal["root_digest"],
        "hasPart": [_reference("./workspace/")],
    }
    experiment_dataset = {
        "@id": "./workspace/",
        "@type": "Dataset",
        "genre": "experiment",
        "name": workspace["title"],
        "description": "Sealed experimental evidence exported from a BenchLineage workspace.",
        "author": _reference(owner_id),
        "dateCreated": workspace["created_at"],
        "dateModified": seal["created_at"],
        "identifier": seal["root_digest"],
        "text": summary,
        "keywords": ", ".join(sorted(tags)),
        "hasPart": [
            _reference(file_ids[path.relative_to(bench.root).as_posix()]) for path in files
        ],
        "mentions": [_reference(identifier) for identifier in mentioned_ids],
    }
    publisher = {
        "@id": BENCHLINEAGE_URL,
        "@type": "Organization",
        "name": "BenchLineage",
        "url": BENCHLINEAGE_URL,
    }
    graph = [descriptor, root_dataset, experiment_dataset, publisher]
    graph.extend(file_entities)
    graph.extend(contextual)
    return {"@context": [ELN_CONTEXT, {"sha256": ELN_SHA256_TERM}], "@graph": graph}


def build_eln(workspace: str | Path | Workspace, output: str | Path) -> Path:
    """Export a sealed workspace as a deterministic ELN Consortium archive."""
    bench = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    bench.require()
    destination = Path(output).resolve()
    if destination.suffix.lower() != ".eln":
        raise ValueError("ELN output must use the .eln extension")
    try:
        destination.relative_to(bench.root)
    except ValueError:
        pass
    else:
        raise ValueError("ELN output must be outside the workspace it packages")

    audit = audit_workspace(bench)
    if audit["status"] != "pass":
        raise ValueError("workspace audit must pass before ELN export")
    seal_path = latest_seal(bench)
    if seal_path is None:
        raise ValueError("workspace must be sealed before ELN export")
    verification = verify_seal(bench, seal_path)
    if not verification["valid"]:
        raise ValueError("latest workspace seal is not valid")
    seal = read_json(seal_path)

    files = relative_files(bench.root)
    for path in files:
        try:
            path.resolve().relative_to(bench.root)
        except ValueError as exception:
            raise ValueError(f"workspace file resolves outside root: {path}") from exception
    try:
        metadata = _metadata_document(bench, files, seal)
    except (KeyError, TypeError, ValueError) as exception:
        raise ValueError(
            f"cannot map workspace records to ELN metadata: {exception}"
        ) from exception
    metadata_bytes = (canonical_json(metadata) + "\n").encode("utf-8")

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    archive_root = destination.name
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            archive.writestr(_file_info(f"{archive_root}/ro-crate-metadata.json"), metadata_bytes)
            for path in files:
                relative = path.relative_to(bench.root).as_posix()
                _write_file(archive, f"{archive_root}/workspace/{relative}", path)
        result = verify_eln(temporary)
        if not result["valid"]:
            raise ValueError(f"generated ELN archive failed verification: {result}")
        os.replace(temporary, destination)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(temporary)
        raise
    return destination


def _entity_types(entity: dict[str, Any]) -> set[str]:
    value = entity.get("@type", [])
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {str(item) for item in value}
    return set()


def _local_member(root: str, identifier: str) -> str | None:
    parsed = urlparse(identifier)
    if parsed.scheme or identifier.startswith("#"):
        return None
    if parsed.query or parsed.fragment:
        raise ValueError(f"local file identifier has an unescaped query or fragment: {identifier}")
    relative = identifier.removeprefix("./")
    decoded = unquote(relative)
    if not _safe_member(decoded) or decoded.endswith("/"):
        raise ValueError(f"unsafe local file identifier: {identifier}")
    return f"{root}/{decoded}"


def _digest_archive_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    hasher = hashlib.sha256()
    with archive.open(info) as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def verify_eln(source: str | Path) -> dict[str, Any]:
    """Verify ELN structure and every locally listed payload without extraction."""
    path = Path(source)
    result: dict[str, Any] = {
        "valid": False,
        "root": None,
        "root_name_matches_archive": False,
        "context": None,
        "datasets": 0,
        "files": 0,
        "external_files": 0,
        "root_digest": None,
        "unsafe": [],
        "duplicates": [],
        "structure": [],
        "missing": [],
        "added": [],
        "changed": [],
        "invalid_entities": [],
    }
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exception:
        result["structure"].append(f"cannot open ZIP archive: {exception}")
        return result

    with archive:
        names = archive.namelist()
        counts = Counter(names)
        result["duplicates"] = sorted(name for name, count in counts.items() if count > 1)
        result["unsafe"] = sorted(name for name in names if not _safe_member(name))
        roots = sorted(
            {PurePosixPath(name).parts[0] for name in names if name and PurePosixPath(name).parts}
        )
        if len(roots) != 1:
            result["structure"].append(
                f"archive must contain exactly one root folder; found {len(roots)}"
            )
            return result
        root = roots[0]
        result["root"] = root
        result["root_name_matches_archive"] = root == path.name
        metadata_name = f"{root}/ro-crate-metadata.json"
        if metadata_name not in names:
            result["structure"].append("ro-crate-metadata.json is missing from the root folder")
            return result
        metadata_info = archive.getinfo(metadata_name)
        if metadata_info.file_size > 64 * 1024 * 1024:
            result["structure"].append("ro-crate-metadata.json exceeds 64 MiB")
            return result
        try:
            metadata = json.loads(archive.read(metadata_info))
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            zipfile.BadZipFile,
            RuntimeError,
            NotImplementedError,
        ) as exception:
            result["structure"].append(f"ro-crate-metadata.json is invalid: {exception}")
            return result
        if not isinstance(metadata, dict):
            result["structure"].append("ro-crate-metadata.json must contain a JSON object")
            return result

        context = metadata.get("@context")
        accepted_contexts = {
            f"https://w3id.org/ro/crate/{version}/context" for version in ("1.1", "1.2", "1.3")
        }
        context_values = (
            {context}
            if isinstance(context, str)
            else {item for item in (context or []) if isinstance(item, str)}
        )
        recognized_contexts = sorted(context_values & accepted_contexts)
        result["context"] = recognized_contexts[-1] if recognized_contexts else context
        if not context_values & accepted_contexts:
            result["structure"].append("unsupported or missing RO-Crate JSON-LD context")

        graph = metadata.get("@graph")
        if not isinstance(graph, list):
            result["structure"].append("@graph must be an array")
            return result
        entities: dict[str, dict[str, Any]] = {}
        for index, entity in enumerate(graph):
            if not isinstance(entity, dict):
                result["invalid_entities"].append(f"@graph[{index}] is not an object")
                continue
            identifier = entity.get("@id")
            if not isinstance(identifier, str) or not identifier:
                result["invalid_entities"].append(f"@graph[{index}] has no @id")
                continue
            if identifier in entities:
                result["invalid_entities"].append(f"duplicate entity id: {identifier}")
            if not _entity_types(entity):
                result["invalid_entities"].append(f"entity has no @type: {identifier}")
            entities[identifier] = entity

        descriptor = entities.get("ro-crate-metadata.json")
        root_dataset = entities.get("./")
        if descriptor is None or "CreativeWork" not in _entity_types(descriptor):
            result["structure"].append("metadata descriptor is missing or has the wrong type")
        else:
            conforms_to = descriptor.get("conformsTo", {})
            if not isinstance(conforms_to, dict) or not str(conforms_to.get("@id", "")).startswith(
                "https://w3id.org/ro/crate/"
            ):
                result["structure"].append("metadata descriptor has no RO-Crate conformsTo")
            if descriptor.get("about") != {"@id": "./"}:
                result["structure"].append("metadata descriptor must describe the root Dataset")
        if root_dataset is None or "Dataset" not in _entity_types(root_dataset):
            result["structure"].append("root Dataset ./ is missing or has the wrong type")
        elif not str(root_dataset.get("name", "")).strip():
            result["structure"].append("root Dataset has no name")

        dataset_entities = [
            entity for entity in entities.values() if "Dataset" in _entity_types(entity)
        ]
        file_entities = [entity for entity in entities.values() if "File" in _entity_types(entity)]
        result["datasets"] = len(dataset_entities)
        result["files"] = len(file_entities)

        referenced_parts: set[str] = set()
        for entity in dataset_entities:
            identifier = entity["@id"]
            parts = entity.get("hasPart", [])
            if not isinstance(parts, list):
                result["invalid_entities"].append(f"hasPart is not an array: {identifier}")
                continue
            for reference in parts:
                child_id = reference.get("@id") if isinstance(reference, dict) else None
                if not child_id or child_id not in entities:
                    result["invalid_entities"].append(
                        f"hasPart references a missing entity from {identifier}: {child_id}"
                    )
                    continue
                referenced_parts.add(child_id)
                if identifier != "./" and "Dataset" in _entity_types(entities[child_id]):
                    result["invalid_entities"].append(
                        f"ELN experiment Dataset contains another Dataset: {identifier}"
                    )

        expected: dict[str, dict[str, Any]] = {}
        for entity in file_entities:
            if entity["@id"] not in referenced_parts:
                result["invalid_entities"].append(
                    f"File entity is not reachable through Dataset hasPart: {entity['@id']}"
                )
            try:
                member = _local_member(root, entity["@id"])
            except ValueError as exception:
                result["invalid_entities"].append(str(exception))
                continue
            if member is None:
                result["external_files"] += 1
                continue
            if member in expected:
                result["invalid_entities"].append(f"multiple File entities map to {member}")
            expected[member] = entity

        available = {
            info.filename
            for info in archive.infolist()
            if not info.is_dir()
            and info.filename != metadata_name
            and not info.filename.endswith("/ro-crate-metadata.json.minisig")
        }
        result["missing"] = sorted(set(expected) - available)
        result["added"] = sorted(available - set(expected))
        for member in sorted(set(expected) & available):
            entity = expected[member]
            info = archive.getinfo(member)
            try:
                expected_size = int(entity.get("contentSize", -1))
            except (TypeError, ValueError):
                expected_size = -1
            expected_digest = str(entity.get("sha256", "")).removeprefix("sha256:").lower()
            digest_valid = len(expected_digest) == 64 and all(
                character in "0123456789abcdef" for character in expected_digest
            )
            try:
                digest_matches = _digest_archive_member(archive, info) == expected_digest
            except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError):
                digest_matches = False
            if expected_size != info.file_size or not digest_valid or not digest_matches:
                result["changed"].append(member)

        candidate_datasets = [
            entity
            for entity in dataset_entities
            if isinstance(entity.get("identifier"), str)
            and entity["identifier"].startswith("sha256:")
        ]
        if candidate_datasets:
            result["root_digest"] = candidate_datasets[-1]["identifier"]

    result["valid"] = not any(
        result[key]
        for key in (
            "unsafe",
            "duplicates",
            "structure",
            "missing",
            "added",
            "changed",
            "invalid_entities",
        )
    )
    return result
