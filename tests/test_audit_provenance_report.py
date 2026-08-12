import json
import tempfile
import unittest
from pathlib import Path

from benchlineage.audit import audit_workspace
from benchlineage.demo import build_demo
from benchlineage.io import read_json, write_json
from benchlineage.provenance import compare_seals, latest_seal, seal_workspace, verify_seal
from benchlineage.report import build_report


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "demo"
        self.bench = build_demo(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def test_demo_counts(self):
        audit = audit_workspace(self.bench)
        self.assertEqual(audit["counts"]["studies"], 2)
        self.assertEqual(audit["counts"]["runs"], 3)
        self.assertEqual(audit["counts"]["instruments"], 3)
        self.assertEqual(audit["counts"]["raw_files"], 3)

    def test_demo_audit_passes(self):
        audit = audit_workspace(self.bench)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["errors"], [])
        self.assertEqual(audit["warnings"], [])

    def test_recorded_before_started_is_rejected(self):
        run_path = self.root / "runs" / "rc-baseline-001.json"
        record = read_json(run_path)
        record["recorded_at"] = "2026-08-04T05:59:59+00:00"
        write_json(run_path, record)
        audit = audit_workspace(self.bench)
        self.assertEqual(audit["status"], "fail")
        self.assertIn("run.time.order", {entry["code"] for entry in audit["errors"]})

    def test_invalid_persisted_owner_email_is_rejected(self):
        metadata_path = self.root / "benchlineage.json"
        metadata = read_json(metadata_path)
        metadata["owner_email"] = "not-an-email"
        write_json(metadata_path, metadata)
        audit = audit_workspace(self.bench)
        self.assertIn("workspace.owner.email", {entry["code"] for entry in audit["errors"]})

    def test_invalid_persisted_data_license_is_rejected(self):
        metadata_path = self.root / "benchlineage.json"
        metadata = read_json(metadata_path)
        metadata["data_license_url"] = "licenses/MIT.html"
        write_json(metadata_path, metadata)
        audit = audit_workspace(self.bench)
        errors = {entry["code"]: entry["message"] for entry in audit["errors"]}
        self.assertIn("workspace.data_license", errors)
        self.assertIn("absolute HTTP(S)", errors["workspace.data_license"])

    def test_analysis_before_recorded_run_is_rejected(self):
        analysis_path = self.root / "analysis" / "rc-baseline-001.json"
        analysis = read_json(analysis_path)
        analysis["created_at"] = "2026-08-04T05:59:59+00:00"
        write_json(analysis_path, analysis)
        audit = audit_workspace(self.bench)
        self.assertIn("analysis.time.order", {entry["code"] for entry in audit["errors"]})

    def test_latest_seal_verifies(self):
        seal = latest_seal(self.bench)
        self.assertIsNotNone(seal)
        self.assertTrue(verify_seal(self.bench, seal)["valid"])

    def test_raw_tampering_is_detected(self):
        seal = latest_seal(self.bench)
        raw = self.root / "data" / "raw" / "rc-baseline.csv"
        raw.write_text(raw.read_text(encoding="utf-8") + "999,1,1,0\n", encoding="utf-8")
        result = verify_seal(self.bench, seal)
        self.assertFalse(result["valid"])
        self.assertIn("data/raw/rc-baseline.csv", result["changed"])

    def test_missing_file_is_detected(self):
        seal = latest_seal(self.bench)
        (self.root / "data" / "raw" / "rc-baseline.csv").unlink()
        result = verify_seal(self.bench, seal)
        self.assertFalse(result["valid"])
        self.assertIn("data/raw/rc-baseline.csv", result["missing"])

    def test_added_file_is_strictly_detected(self):
        seal = latest_seal(self.bench)
        (self.root / "data" / "raw" / "extra.csv").write_text("x\n1\n", encoding="utf-8")
        strict = verify_seal(self.bench, seal)
        relaxed = verify_seal(self.bench, seal, reject_untracked=False)
        self.assertFalse(strict["valid"])
        self.assertTrue(relaxed["valid"])

    def test_declared_root_manipulation_is_detected(self):
        seal = json.loads(latest_seal(self.bench).read_text(encoding="utf-8"))
        seal["files"][0]["digest"] = "sha256:" + "0" * 64
        result = verify_seal(self.bench, seal)
        self.assertFalse(result["declared_root_valid"])
        self.assertFalse(result["valid"])

    def test_compare_seals(self):
        first = json.loads(latest_seal(self.bench).read_text(encoding="utf-8"))
        (self.root / "reports" / "ignored.txt").write_text("presentation", encoding="utf-8")
        second = seal_workspace(self.bench, label="second")
        comparison = compare_seals(first, second)
        self.assertTrue(comparison["same_root"])
        self.assertEqual(comparison["changed"], [])

    def test_report_is_self_contained(self):
        report = build_report(self.bench, self.root / "reports" / "check.html")
        text = report.read_text(encoding="utf-8")
        self.assertIn("Power-conversion and RC-filter characterization", text)
        self.assertIn("window.__BENCHLINEAGE__", text)
        self.assertNotIn("<script src=", text)
        self.assertNotIn('<link rel="stylesheet"', text)
        self.assertNotRegex(text, r'(?:src|href)=["\']https?://')
        self.assertIn(
            '"data_license_url":"https://spdx.org/licenses/MIT.html"',
            text,
        )

    def test_report_escapes_labels(self):
        metadata_path = self.root / "benchlineage.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["title"] = "<script>alert(1)</script>"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        report = build_report(self.bench, self.root / "reports" / "escaped.html")
        text = report.read_text(encoding="utf-8")
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", text)
        self.assertNotIn("<h1><script>", text)


if __name__ == "__main__":
    unittest.main()
