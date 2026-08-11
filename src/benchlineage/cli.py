"""BenchLineage command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .analysis import analyze_run
from .audit import audit_workspace
from .bundle import build_bundle, verify_bundle
from .demo import build_demo
from .eln import build_eln, verify_eln
from .io import read_json, write_json
from .provenance import compare_seals, latest_seal, seal_workspace, verify_seal
from .report import build_report
from .workspace import Workspace


def _json_argument(value: str) -> Any:
    path = Path(value)
    if path.is_file():
        return read_json(path)
    return json.loads(value)


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="benchlineage",
        description="Local-first provenance and uncertainty trails for EE experiments.",
    )
    parser.add_argument("--version", action="version", version="BenchLineage 0.3.0")
    subcommands = parser.add_subparsers(dest="command", required=True)

    initialize = subcommands.add_parser("init", help="initialize a transparent workspace")
    initialize.add_argument("workspace")
    initialize.add_argument("--title", required=True)
    initialize.add_argument("--owner", required=True)

    instrument = subcommands.add_parser("add-instrument", help="register instrument identity")
    instrument.add_argument("workspace")
    instrument.add_argument("--id", required=True)
    instrument.add_argument("--kind", required=True)
    instrument.add_argument("--manufacturer", required=True)
    instrument.add_argument("--model", required=True)
    instrument.add_argument("--serial", required=True)
    instrument.add_argument("--asset-tag", default="")
    instrument.add_argument("--notes", default="")

    calibration = subcommands.add_parser("add-calibration", help="register calibration coverage")
    calibration.add_argument("workspace")
    calibration.add_argument("--id", required=True)
    calibration.add_argument("--instrument", required=True)
    calibration.add_argument("--performed-at", required=True)
    calibration.add_argument("--due-at", required=True)
    calibration.add_argument("--certificate", required=True)
    calibration.add_argument("--standard-uncertainty", required=True, type=float)
    calibration.add_argument("--unit", required=True)
    calibration.add_argument("--coverage-factor", type=float, default=2.0)

    study = subcommands.add_parser("create-study", help="record study intent and protocol")
    study.add_argument("workspace")
    study.add_argument("--id", required=True)
    study.add_argument("--title", required=True)
    study.add_argument("--objective", required=True)
    study.add_argument("--hypothesis", default="")
    study.add_argument("--protocol", required=True)
    study.add_argument("--tag", action="append", default=[])

    run = subcommands.add_parser("add-run", help="link a run to raw evidence")
    run.add_argument("workspace")
    run.add_argument("--id", required=True)
    run.add_argument("--study", required=True)
    run.add_argument("--operator", required=True)
    run.add_argument("--started-at", required=True)
    run.add_argument("--instrument", action="append", default=[])
    run.add_argument("--raw-file", action="append", default=[])
    run.add_argument("--conditions", default="{}")
    run.add_argument("--deviation", action="append", default=[])
    run.add_argument("--notes", default="")

    analyze = subcommands.add_parser("analyze", help="derive an analysis from a recorded run")
    analyze.add_argument("workspace")
    analyze.add_argument("--run", required=True)
    analyze.add_argument(
        "--kind",
        choices=[
            "auto",
            "frequency_response",
            "power_efficiency",
            "linear_calibration",
            "column_summary",
        ],
        default="auto",
    )
    analyze.add_argument("--uncertainty", help="JSON file or inline JSON component array")
    analyze.add_argument("--coverage-factor", type=float, default=2.0)

    audit = subcommands.add_parser("audit", help="check references, calibrations, files, and seals")
    audit.add_argument("workspace")
    audit.add_argument("--output")

    seal = subcommands.add_parser("seal", help="content-address the current evidence")
    seal.add_argument("workspace")
    seal.add_argument("--label", default="")

    verify = subcommands.add_parser("verify", help="verify the latest or selected seal")
    verify.add_argument("workspace")
    verify.add_argument("--seal")
    verify.add_argument("--allow-untracked", action="store_true")

    report = subcommands.add_parser("report", help="build a self-contained HTML report")
    report.add_argument("workspace")
    report.add_argument("--output", required=True)
    report.add_argument("--title")
    report.add_argument("--note", default="")

    bundle = subcommands.add_parser(
        "bundle", help="build a deterministic, self-verifying publication ZIP"
    )
    bundle.add_argument("workspace")
    bundle.add_argument("--output", required=True)

    verify_bundle_parser = subcommands.add_parser(
        "verify-bundle", help="verify a publication ZIP without extracting it"
    )
    verify_bundle_parser.add_argument("bundle")

    export_eln = subcommands.add_parser(
        "export-eln", help="export a sealed workspace in the ELN Consortium format"
    )
    export_eln.add_argument("workspace")
    export_eln.add_argument("--output", required=True)

    verify_eln_parser = subcommands.add_parser(
        "verify-eln", help="verify an ELN archive without extracting it"
    )
    verify_eln_parser.add_argument("archive")

    diff_seals = subcommands.add_parser(
        "diff-seals", help="show added, removed, and changed evidence between two seals"
    )
    diff_seals.add_argument("left")
    diff_seals.add_argument("right")
    diff_seals.add_argument("--output")

    demo = subcommands.add_parser("demo", help="generate the public synthetic demonstration")
    demo.add_argument("destination")
    demo.add_argument("--seed", type=int, default=20260804)
    demo.add_argument("--replace", action="store_true")
    return parser


def execute(arguments: argparse.Namespace) -> int:
    command = arguments.command
    if command == "init":
        _print(
            Workspace(arguments.workspace).initialize(title=arguments.title, owner=arguments.owner)
        )
    elif command == "add-instrument":
        _print(
            Workspace(arguments.workspace).add_instrument(
                instrument_id=arguments.id,
                kind=arguments.kind,
                manufacturer=arguments.manufacturer,
                model=arguments.model,
                serial=arguments.serial,
                asset_tag=arguments.asset_tag,
                notes=arguments.notes,
            )
        )
    elif command == "add-calibration":
        _print(
            Workspace(arguments.workspace).add_calibration(
                calibration_id=arguments.id,
                instrument_id=arguments.instrument,
                performed_at=arguments.performed_at,
                due_at=arguments.due_at,
                certificate=arguments.certificate,
                standard_uncertainty=arguments.standard_uncertainty,
                unit=arguments.unit,
                coverage_factor=arguments.coverage_factor,
            )
        )
    elif command == "create-study":
        _print(
            Workspace(arguments.workspace).create_study(
                study_id=arguments.id,
                title=arguments.title,
                objective=arguments.objective,
                hypothesis=arguments.hypothesis,
                protocol=arguments.protocol,
                tags=arguments.tag,
            )
        )
    elif command == "add-run":
        _print(
            Workspace(arguments.workspace).add_run(
                run_id=arguments.id,
                study_id=arguments.study,
                operator=arguments.operator,
                started_at=arguments.started_at,
                instruments=arguments.instrument,
                raw_files=arguments.raw_file,
                conditions=_json_argument(arguments.conditions),
                deviations=arguments.deviation,
                notes=arguments.notes,
            )
        )
    elif command == "analyze":
        components = _json_argument(arguments.uncertainty) if arguments.uncertainty else None
        _print(
            analyze_run(
                arguments.workspace,
                arguments.run,
                kind=arguments.kind,
                uncertainty_components=components,
                coverage_factor=arguments.coverage_factor,
            )
        )
    elif command == "audit":
        result = audit_workspace(arguments.workspace)
        if arguments.output:
            write_json(Path(arguments.output), result)
        _print(result)
        return 0 if result["status"] == "pass" else 1
    elif command == "seal":
        _print(seal_workspace(arguments.workspace, label=arguments.label))
    elif command == "verify":
        seal_path = Path(arguments.seal) if arguments.seal else latest_seal(arguments.workspace)
        if seal_path is None:
            raise FileNotFoundError("no seal found")
        result = verify_seal(
            arguments.workspace, seal_path, reject_untracked=not arguments.allow_untracked
        )
        _print(result)
        return 0 if result["valid"] else 1
    elif command == "report":
        output = build_report(
            arguments.workspace,
            arguments.output,
            title=arguments.title,
            note=arguments.note,
        )
        _print({"report": str(output.resolve())})
    elif command == "bundle":
        output = build_bundle(arguments.workspace, arguments.output)
        verification = verify_bundle(output)
        _print(
            {
                "bundle": str(output.resolve()),
                "bytes": output.stat().st_size,
                "root_digest": verification["workspace"].get("root_digest"),
                "verified": verification["valid"],
            }
        )
    elif command == "verify-bundle":
        result = verify_bundle(arguments.bundle)
        _print(result)
        return 0 if result["valid"] else 1
    elif command == "export-eln":
        output = build_eln(arguments.workspace, arguments.output)
        verification = verify_eln(output)
        _print(
            {
                "archive": str(output.resolve()),
                "bytes": output.stat().st_size,
                "root_digest": verification["root_digest"],
                "verified": verification["valid"],
            }
        )
    elif command == "verify-eln":
        result = verify_eln(arguments.archive)
        _print(result)
        return 0 if result["valid"] else 1
    elif command == "diff-seals":
        result = compare_seals(arguments.left, arguments.right)
        if arguments.output:
            write_json(Path(arguments.output), result)
        _print(result)
        return 0 if result["same_root"] else 1
    elif command == "demo":
        bench = build_demo(arguments.destination, seed=arguments.seed, replace=arguments.replace)
        _print({"workspace": str(bench.root), "report": "reports/demo-report.html"})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        return execute(parser.parse_args(argv))
    except (
        FileNotFoundError,
        FileExistsError,
        ValueError,
        json.JSONDecodeError,
        OSError,
    ) as exception:
        print(f"error: {exception}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
