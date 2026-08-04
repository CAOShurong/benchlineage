"""Repository-level checks that do not require third-party packages."""

from __future__ import annotations

import json
import re
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


def text_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in TEXT_SUFFIXES
        and not any(part in IGNORED_PARTS for part in path.parts)
    ]


def check_json(errors: list[str]) -> None:
    for path in ROOT.rglob("*.json"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exception:
            errors.append(f"invalid JSON: {path.relative_to(ROOT)}: {exception}")


def check_toml(errors: list[str]) -> None:
    try:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exception:
        errors.append(f"invalid pyproject.toml: {exception}")


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
        if any(part in IGNORED_PARTS for part in path.parts):
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


def main() -> int:
    errors: list[str] = []
    check_json(errors)
    check_toml(errors)
    check_english(errors)
    check_markdown_links(errors)
    check_secret_shapes(errors)
    check_site(errors)
    result = {
        "status": "pass" if not errors else "fail",
        "files_checked": len(text_files()),
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
