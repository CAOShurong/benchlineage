"""Deterministic, self-verifying publication bundles."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from contextlib import suppress
from pathlib import Path, PurePosixPath
from typing import Any

from ._version import __version__
from .audit import audit_workspace
from .io import canonical_json, digest_bytes, digest_file, read_json, relative_files
from .provenance import latest_seal, verify_seal
from .workspace import Workspace

BUNDLE_SCHEMA = "benchlineage/bundle/v1"
_CREATED_WITH = f"BenchLineage {__version__}"
_README = """BenchLineage evidence bundle
============================

This ZIP is a portable research-evidence package.

- BUNDLE-MANIFEST.json lists every file, byte length, and SHA-256 digest.
- workspace/ preserves the original relative paths.
- The recorded evidence root comes from the latest BenchLineage seal.
- Integrity is not authenticity, and authenticity is not scientific validity.

Verify with:

    benchlineage verify-bundle <bundle.zip>

The manifest is ordinary JSON, so the listed SHA-256 digests can also be
checked without BenchLineage.
"""


def _member_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and not name.startswith("/")
    )


def build_bundle(
    workspace: str | Path | Workspace,
    output: str | Path,
) -> Path:
    """Build a byte-stable publication ZIP from a sealed workspace."""
    bench = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    bench.require()
    destination = Path(output).resolve()
    try:
        destination.relative_to(bench.root)
    except ValueError:
        pass
    else:
        raise ValueError("bundle output must be outside the workspace it packages")

    audit = audit_workspace(bench)
    if audit["status"] != "pass":
        raise ValueError("workspace audit must pass before bundling")
    seal_path = latest_seal(bench)
    if seal_path is None:
        raise ValueError("workspace must be sealed before bundling")
    verification = verify_seal(bench, seal_path)
    if not verification["valid"]:
        raise ValueError("latest workspace seal is not valid")
    seal = read_json(seal_path)

    files = relative_files(bench.root)
    entries: list[dict[str, Any]] = []
    for path in files:
        try:
            path.resolve().relative_to(bench.root)
        except ValueError as exception:
            raise ValueError(f"workspace file resolves outside root: {path}") from exception
        relative = path.relative_to(bench.root).as_posix()
        entries.append(
            {
                "path": f"workspace/{relative}",
                "bytes": path.stat().st_size,
                "digest": digest_file(path),
            }
        )
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "created_at": seal["created_at"],
        "created_with": _CREATED_WITH,
        "workspace": {
            "title": audit["workspace"],
            "root_digest": seal["root_digest"],
            "seal": f"workspace/{seal_path.relative_to(bench.root).as_posix()}",
        },
        "audit": {
            "status": audit["status"],
            "counts": audit["counts"],
            "warnings": audit["warnings"],
        },
        "files": entries,
    }
    manifest_bytes = (canonical_json(manifest) + "\n").encode("utf-8")
    readme_bytes = _README.encode("utf-8")

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            archive.writestr(_member_info("README.txt"), readme_bytes)
            archive.writestr(_member_info("BUNDLE-MANIFEST.json"), manifest_bytes)
            for path, entry in zip(files, entries, strict=True):
                archive.writestr(_member_info(entry["path"]), path.read_bytes())
        os.replace(temporary, destination)
    except BaseException:
        with suppress(FileNotFoundError):
            os.unlink(temporary)
        raise
    return destination


def verify_bundle(bundle: str | Path) -> dict[str, Any]:
    """Verify paths, file inventory, byte lengths, and digests in a bundle."""
    path = Path(bundle)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        unsafe = sorted(name for name in names if not _safe_member(name))
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if "BUNDLE-MANIFEST.json" not in names:
            raise ValueError("bundle manifest is missing")
        try:
            manifest = json.loads(archive.read("BUNDLE-MANIFEST.json"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exception:
            raise ValueError(f"bundle manifest is invalid: {exception}") from exception
        if manifest.get("schema") != BUNDLE_SCHEMA:
            raise ValueError(f"unsupported bundle schema: {manifest.get('schema')}")

        expected: dict[str, dict[str, Any]] = {}
        for entry in manifest.get("files", []):
            name = str(entry.get("path", ""))
            if name in expected:
                duplicates.append(name)
            expected[name] = entry
        available = set(names) - {"README.txt", "BUNDLE-MANIFEST.json"}
        missing = sorted(set(expected) - available)
        added = sorted(available - set(expected))
        changed: list[str] = []
        for name in sorted(set(expected) & available):
            payload = archive.read(name)
            entry = expected[name]
            if len(payload) != entry.get("bytes") or digest_bytes(payload) != entry.get("digest"):
                changed.append(name)

    valid = not unsafe and not duplicates and not missing and not added and not changed
    return {
        "valid": valid,
        "schema": manifest["schema"],
        "workspace": manifest.get("workspace", {}),
        "files": len(expected),
        "unsafe": unsafe,
        "duplicates": sorted(set(duplicates)),
        "missing": missing,
        "added": added,
        "changed": changed,
    }
