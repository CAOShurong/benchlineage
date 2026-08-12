"""Repository-level checks that do not require third-party packages."""

from __future__ import annotations

import json
import re
import struct
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".cff",
    ".css",
    ".html",
    ".json",
    ".md",
    ".py",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
IGNORED_PARTS = {".git", ".venv", "__pycache__", "build", "dist"}
EXPECTED_VERSION = "0.3.3"
EXPECTED_RELEASE_DATE = "2026-08-12"


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS or part.startswith("dist-") for part in path.parts)


def text_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and not is_ignored(path)
    ]


def check_json(errors: list[str]) -> None:
    for path in ROOT.rglob("*.json"):
        if is_ignored(path):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exception:
            errors.append(f"invalid JSON: {path.relative_to(ROOT)}: {exception}")


def check_toml(errors: list[str]) -> None:
    try:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            pyproject = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exception:
        errors.append(f"invalid pyproject.toml: {exception}")
        return
    if pyproject["project"]["version"] != EXPECTED_VERSION:
        errors.append("pyproject version does not match the release")
    if pyproject["project"]["authors"] != [{"name": "Shurong Cao"}]:
        errors.append("package authorship must name Shurong Cao only")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if f"version: {EXPECTED_VERSION}" not in citation:
        errors.append("citation version does not match the release")
    if f"date-released: {EXPECTED_RELEASE_DATE}" not in citation:
        errors.append("citation date does not match the release")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {EXPECTED_VERSION} - {EXPECTED_RELEASE_DATE}" not in changelog:
        errors.append("changelog version or date does not match the release")


def check_english(errors: list[str]) -> None:
    cjk = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
    for path in text_files():
        text = path.read_text(encoding="utf-8")
        match = cjk.search(text)
        if match:
            errors.append(
                f"non-English script found: {path.relative_to(ROOT)}:{text[: match.start()].count(chr(10)) + 1}"
            )


def check_markdown_links(errors: list[str]) -> None:
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        if is_ignored(path):
            continue
        text = path.read_text(encoding="utf-8")
        for target in pattern.findall(text):
            target = target.strip().strip("<>")
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            resolved = (path.parent / relative).resolve()
            if not resolved.exists():
                errors.append(f"broken Markdown link: {path.relative_to(ROOT)} -> {target}")


def check_secret_shapes(errors: list[str]) -> None:
    patterns = {
        "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{30,}\b"),
        "OpenAI key": re.compile(r"\bsk-[A-Za-z0-9_-]{30,}\b"),
        "Anthropic key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
        "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    }
    for path in text_files():
        text = path.read_text(encoding="utf-8")
        for label, pattern in patterns.items():
            if pattern.search(text):
                errors.append(f"possible {label}: {path.relative_to(ROOT)}")


def check_site(errors: list[str]) -> None:
    index = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    if "https://github.com/CAOShurong/benchlineage" not in index:
        errors.append("site does not link to the canonical repository")
    report = ROOT / "site" / "demo" / "demo-report.html"
    if not report.is_file():
        errors.append("site demonstration report is missing")
    else:
        report_text = report.read_text(encoding="utf-8")
        if "<script src=" in report_text or '<link rel="stylesheet"' in report_text:
            errors.append("demonstration report is not self-contained")
    if "python -m pip install benchlineage" not in index:
        errors.append("site lacks the PyPI install path")
    if "benchlineage export-eln" not in index:
        errors.append("site lacks the ELN exchange path")
    preview = ROOT / "site" / "social-preview.png"
    if not preview.is_file():
        errors.append("social preview is missing")
    else:
        payload = preview.read_bytes()
        if payload[:8] != b"\x89PNG\r\n\x1a\n" or len(payload) < 24:
            errors.append("social preview is not a valid PNG")
        elif struct.unpack(">II", payload[16:24]) != (1280, 640):
            errors.append("social preview must be 1280x640")


def check_release_metadata(errors: list[str]) -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    package = (ROOT / "src" / "benchlineage" / "__init__.py").read_text(encoding="utf-8")
    for label, text, marker in (
        ("citation", citation, f"version: {EXPECTED_VERSION}"),
        ("changelog", changelog, f"## {EXPECTED_VERSION}"),
        ("package", package, f'__version__ = "{EXPECTED_VERSION}"'),
        ("README", readme, "python -m pip install benchlineage"),
        ("README", readme, "benchlineage export-eln"),
        ("README", readme, "benchlineage diff-seals"),
    ):
        if marker not in text:
            errors.append(f"{label} release metadata is inconsistent")
    for relative in (
        "docs/assets/hero.svg",
        "docs/assets/workflow.svg",
        "docs/assets/result-record.svg",
    ):
        if not (ROOT / relative).is_file():
            errors.append(f"README figure is missing: {relative}")


def main() -> int:
    errors: list[str] = []
    check_json(errors)
    check_toml(errors)
    check_english(errors)
    check_markdown_links(errors)
    check_secret_shapes(errors)
    check_site(errors)
    check_release_metadata(errors)
    result = {
        "status": "pass" if not errors else "fail",
        "files_checked": len(text_files()),
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
