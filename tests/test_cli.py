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
