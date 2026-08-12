import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from benchlineage.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "workspace"

    def tearDown(self):
        self.temporary.cleanup()

    def test_demo_audit_verify_and_report(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["demo", str(self.root)]), 0)
            self.assertEqual(main(["audit", str(self.root)]), 0)
            self.assertEqual(main(["verify", str(self.root)]), 0)
            self.assertEqual(
                main(
                    [
                        "report",
                        str(self.root),
                        "--output",
                        str(self.root / "reports" / "cli.html"),
                    ]
                ),
                0,
            )
            bundle = self.root.parent / "evidence.zip"
            self.assertEqual(
                main(["bundle", str(self.root), "--output", str(bundle)]),
                0,
            )
            self.assertEqual(main(["verify-bundle", str(bundle)]), 0)
        self.assertTrue((self.root / "reports" / "cli.html").is_file())

    def test_error_is_concise(self):
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            code = main(["audit", str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn('"status": "fail"', stdout.getvalue())

    def test_init_accepts_explicit_owner_identity(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                main(
                    [
                        "init",
                        str(self.root),
                        "--title",
                        "Interop bench",
                        "--owner",
                        "Ada Lovelace",
                        "--owner-email",
                        "ada@example.invalid",
                        "--owner-given-name",
                        "Ada",
                        "--owner-family-name",
                        "Lovelace",
                        "--data-license-url",
                        "https://spdx.org/licenses/CC-BY-4.0.html",
                        "--data-license-name",
                        "CC BY 4.0",
                        "--data-license-description",
                        "Reusable interop fixture.",
                    ]
                ),
                0,
            )
        metadata = json.loads((self.root / "benchlineage.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["owner_email"], "ada@example.invalid")
        self.assertEqual(metadata["owner_given_name"], "Ada")
        self.assertEqual(metadata["owner_family_name"], "Lovelace")
        self.assertEqual(
            metadata["data_license_url"],
            "https://spdx.org/licenses/CC-BY-4.0.html",
        )
        self.assertEqual(metadata["data_license_name"], "CC BY 4.0")

    def test_json_output_roundtrips_unicode_on_legacy_code_page(self):
        output_bytes = io.BytesIO()
        legacy_stdout = io.TextIOWrapper(output_bytes, encoding="cp936")
        with contextlib.redirect_stdout(legacy_stdout):
            code = main(
                [
                    "init",
                    str(self.root),
                    "--title",
                    "Unicode ß bench",
                    "--owner",
                    "Researcher",
                ]
            )
            legacy_stdout.flush()
        self.assertEqual(code, 0)
        output = output_bytes.getvalue().decode("ascii")
        self.assertEqual(json.loads(output)["title"], "Unicode ß bench")

    def test_audit_reports_missing_required_workspace_field(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                main(
                    [
                        "init",
                        str(self.root),
                        "--title",
                        "Incomplete bench",
                        "--owner",
                        "Researcher",
                    ]
                ),
                0,
            )
        metadata_path = self.root / "benchlineage.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        del metadata["title"]
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(["audit", str(self.root)])
        self.assertEqual(code, 1)
        self.assertEqual(stderr.getvalue(), "")
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["errors"][0]["code"], "workspace.invalid")
        self.assertIn("title", result["errors"][0]["message"])

    def test_run_accepts_bom_prefixed_conditions_file(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                main(
                    [
                        "init",
                        str(self.root),
                        "--title",
                        "PowerShell input",
                        "--owner",
                        "Researcher",
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "create-study",
                        str(self.root),
                        "--id",
                        "study-001",
                        "--title",
                        "BOM compatibility",
                        "--objective",
                        "Exercise a PowerShell-style JSON file.",
                        "--hypothesis",
                        "The CLI accepts a UTF-8 BOM.",
                        "--protocol",
                        "Record one synthetic run.",
                    ]
                ),
                0,
            )
        conditions = self.root.parent / "conditions.json"
        conditions.write_text('{"bus_voltage_v": 400}', encoding="utf-8-sig")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                main(
                    [
                        "add-run",
                        str(self.root),
                        "--id",
                        "run-001",
                        "--study",
                        "study-001",
                        "--operator",
                        "Researcher",
                        "--started-at",
                        "2026-08-12T14:00:00+08:00",
                        "--conditions",
                        str(conditions),
                    ]
                ),
                0,
            )
        record = json.loads((self.root / "runs" / "run-001.json").read_text(encoding="utf-8"))
        self.assertEqual(record["conditions"], {"bus_voltage_v": 400})

    def test_init_rejects_invalid_owner_email(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(
                [
                    "init",
                    str(self.root),
                    "--title",
                    "Invalid identity",
                    "--owner",
                    "Researcher",
                    "--owner-email",
                    "not-an-email",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("owner email", stderr.getvalue())

    def test_init_rejects_license_details_without_url(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(
                [
                    "init",
                    str(self.root),
                    "--title",
                    "Invalid license",
                    "--owner",
                    "Researcher",
                    "--data-license-name",
                    "MIT License",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("data license URL", stderr.getvalue())

    def test_duplicate_demo_returns_usage_error(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["demo", str(self.root)]), 0)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["demo", str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("not empty", stderr.getvalue())

    def test_eln_export_verify_and_seal_diff(self):
        destination = self.root
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["demo", str(destination)]), 0)

        export = self.root.parent / "demo.eln"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["export-eln", str(destination), "--output", str(export)]), 0)
        exported = json.loads(stdout.getvalue())
        self.assertTrue(exported["verified"])

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["verify-eln", str(export)]), 0)
        self.assertTrue(json.loads(stdout.getvalue())["valid"])

        first = next((destination / "seals").glob("seal-*.json"))
        raw = destination / "data" / "raw" / "rc-baseline.csv"
        raw.write_text(raw.read_text(encoding="utf-8") + "120000,1,0.01,-89\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["seal", str(destination), "--label", "after change"]), 0)
        second = sorted((destination / "seals").glob("seal-*.json"))[-1]

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(["diff-seals", str(first), str(second)]), 1)
        difference = json.loads(stdout.getvalue())
        self.assertFalse(difference["same_root"])
        self.assertIn("data/raw/rc-baseline.csv", difference["changed"])

    def test_malformed_eln_returns_structured_failure(self):
        malformed = self.root.parent / "malformed.eln"
        malformed.write_bytes(b"not a ZIP archive")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(main(["verify-eln", str(malformed)]), 1)
        self.assertFalse(json.loads(stdout.getvalue())["valid"])
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
