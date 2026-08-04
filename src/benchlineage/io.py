"""Deterministic file and JSON helpers."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> str:
    """Serialize JSON deterministically for hashing and durable diffs."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return f"sha256:{hasher.hexdigest()}"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    """Atomically write stable, readable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


def safe_identifier(value: str, *, field: str = "identifier") -> str:
    normalized = value.strip().lower().replace("_", "-").replace(" ", "-")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    if not normalized or normalized[0] == "-" or normalized[-1] == "-":
        raise ValueError(f"{field} must start and end with a letter or digit")
    if any(character not in allowed for character in normalized):
        raise ValueError(f"{field} may contain only lowercase letters, digits, and hyphens")
    if "--" in normalized:
        raise ValueError(f"{field} may not contain consecutive hyphens")
    return normalized


def relative_files(root: Path, *, exclude: set[str] | None = None) -> list[Path]:
    excluded = exclude or set()
    result: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if any(relative == item or relative.startswith(f"{item}/") for item in excluded):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(root).as_posix())
