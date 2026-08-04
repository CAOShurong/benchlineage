import tempfile
import unittest
import zipfile
from pathlib import Path

from benchlineage.bundle import build_bundle, verify_bundle
from benchlineage.demo import build_demo


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = build_demo(self.root / "workspace")

    def tearDown(self):
        self.temporary.cleanup()

    def test_bundle_is_valid_and_byte_stable(self):
        first = build_bundle(self.workspace, self.root / "first.zip")
        second = build_bundle(self.workspace, self.root / "second.zip")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        result = verify_bundle(first)
        self.assertTrue(result["valid"])
        self.assertGreater(result["files"], 10)
        self.assertTrue(result["workspace"]["root_digest"].startswith("sha256:"))

    def test_tampered_member_is_detected(self):
        original = build_bundle(self.workspace, self.root / "original.zip")
        tampered = self.root / "tampered.zip"
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(tampered, "w") as target:
            for item in source.infolist():
                payload = source.read(item.filename)
                if item.filename.endswith("data/raw/rc-baseline.csv"):
                    payload += b"tampered\n"
                target.writestr(item, payload)
        result = verify_bundle(tampered)
        self.assertFalse(result["valid"])
        self.assertIn("workspace/data/raw/rc-baseline.csv", result["changed"])

    def test_output_inside_workspace_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside the workspace"):
            build_bundle(self.workspace, self.workspace.root / "bundle.zip")


if __name__ == "__main__":
    unittest.main()
