"""Content-addressed evidence sealing and tamper verification."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from .io import canonical_json, digest_bytes, digest_file, read_json, relative_files, write_json
from .workspace import Workspace


def _inventory(bench: Workspace) -> list[dict[str, Any]]:
    entries = []
    for path in relative_files(bench.root, exclude={"reports", "seals"}):
        relative = path.relative_to(bench.root).as_posix()
        entries.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "digest": digest_file(path),
            }
        )
    return entries


def _root_digest(entries: list[dict[str, Any]]) -> str:
    payload = [{"path": item["path"], "digest": item["digest"]} for item in entries]
    return digest_bytes(canonical_json(payload).encode("utf-8"))


def seal_workspace(
    workspace: str | Path | Workspace,
    *,
    label: str = "",
    created_at: str | None = None,
) -> dict[str, Any]:
    bench = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    bench.require()
    timestamp = created_at or dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    entries = _inventory(bench)
    seal = {
        "schema": "benchlineage/seal/v1",
        "created_at": timestamp,
        "label": label.strip(),
        "algorithm": "sha256",
        "scope": {
            "included": "all workspace files",
            "excluded": ["reports/**", "seals/**"],
        },
        "files": entries,
        "root_digest": _root_digest(entries),
    }
    safe_time = timestamp.replace(":", "").replace("+", "-")
    write_json(bench.root / "seals" / f"seal-{safe_time}.json", seal)
    return seal


def verify_seal(
    workspace: str | Path | Workspace,
    seal: str | Path | dict,
    *,
    reject_untracked: bool = True,
) -> dict[str, Any]:
    bench = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    bench.require()
    record = seal if isinstance(seal, dict) else read_json(Path(seal))
    expected = {item["path"]: item for item in record["files"]}
    current = {item["path"]: item for item in _inventory(bench)}
    missing = sorted(set(expected) - set(current))
    added = sorted(set(current) - set(expected))
    changed = sorted(
        path
        for path in set(expected) & set(current)
        if expected[path]["digest"] != current[path]["digest"]
    )
    declared_root_valid = record.get("root_digest") == _root_digest(record["files"])
    valid = not missing and not changed and declared_root_valid
    if reject_untracked:
        valid = valid and not added
    return {
        "valid": valid,
        "root_digest": record.get("root_digest"),
        "declared_root_valid": declared_root_valid,
        "missing": missing,
        "changed": changed,
        "added": added,
        "reject_untracked": reject_untracked,
    }


def latest_seal(workspace: str | Path | Workspace) -> Path | None:
    bench = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    candidates = sorted((bench.root / "seals").glob("seal-*.json"))
    return candidates[-1] if candidates else None


def compare_seals(left: str | Path | dict, right: str | Path | dict) -> dict[str, Any]:
    left_record = left if isinstance(left, dict) else read_json(Path(left))
    right_record = right if isinstance(right, dict) else read_json(Path(right))
    left_files = {item["path"]: item["digest"] for item in left_record["files"]}
    right_files = {item["path"]: item["digest"] for item in right_record["files"]}
    return {
        "same_root": left_record.get("root_digest") == right_record.get("root_digest"),
        "added": sorted(set(right_files) - set(left_files)),
        "removed": sorted(set(left_files) - set(right_files)),
        "changed": sorted(
            path
            for path in set(left_files) & set(right_files)
            if left_files[path] != right_files[path]
        ),
    }
