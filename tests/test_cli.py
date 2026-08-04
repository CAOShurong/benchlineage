import contextlib
import io
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


if __name__ == "__main__":
    unittest.main()
