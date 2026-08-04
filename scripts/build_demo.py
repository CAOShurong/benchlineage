"""Build or verify the committed deterministic demonstration."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from benchlineage.audit import audit_workspace  # noqa: E402
from benchlineage.demo import build_demo  # noqa: E402
from benchlineage.provenance import latest_seal, verify_seal  # noqa: E402


def summary(path: Path) -> dict:
    audit = audit_workspace(path)
    seal_path = latest_seal(path)
    if seal_path is None:
        raise RuntimeError("demo did not produce a seal")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    verification = verify_seal(path, seal_path)
    return {
        "audit_status": audit["status"],
        "counts": audit["counts"],
        "errors": audit["errors"],
        "warnings": audit["warnings"],
        "root_digest": seal["root_digest"],
        "seal_valid": verification["valid"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--seed", type=int, default=20260804)
    arguments = parser.parse_args()

    committed = ROOT / "demo" / "workspace"
    if arguments.check:
        with tempfile.TemporaryDirectory() as temporary:
            generated = Path(temporary) / "workspace"
            build_demo(generated, seed=arguments.seed)
            generated_summary = summary(generated)
            if not committed.is_dir():
                raise SystemExit("committed demo is missing; run scripts/build_demo.py")
            committed_summary = summary(committed)
            if generated_summary != committed_summary:
                print("generated demo differs from committed fixture", file=sys.stderr)
                print(
                    json.dumps(
                        {"generated": generated_summary, "committed": committed_summary}, indent=2
                    )
                )
                return 1
            if generated_summary["audit_status"] != "pass" or not generated_summary["seal_valid"]:
                print(json.dumps(generated_summary, indent=2))
                return 1
            print(json.dumps(generated_summary, indent=2))
            return 0

    build_demo(committed, seed=arguments.seed, replace=True)
    site_demo = ROOT / "site" / "demo"
    site_demo.mkdir(parents=True, exist_ok=True)
    shutil.copy2(committed / "reports" / "demo-report.html", site_demo / "demo-report.html")
    print(json.dumps(summary(committed), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
