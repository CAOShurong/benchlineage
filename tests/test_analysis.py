import csv
import math
import tempfile
import unittest
from pathlib import Path

from benchlineage.analysis import analyze_run, detect_kind
from benchlineage.workspace import Workspace


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bench = Workspace(self.root)
        self.bench.initialize(title="Analysis", owner="Researcher")
        self.bench.create_study(
            study_id="study",
            title="Study",
            objective="Analyze data",
            hypothesis="",
            protocol="Collect rows.",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def _run_for_rows(self, run_id, fields, rows):
        path = self.root / "data" / "raw" / f"{run_id}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        self.bench.add_run(
            run_id=run_id,
            study_id="study",
            operator="Researcher",
            started_at="2026-08-04T00:00:00+00:00",
            instruments=[],
            raw_files=[f"data/raw/{run_id}.csv"],
            conditions={},
        )

    def test_detect_kinds(self):
        self.assertEqual(detect_kind(["frequency_hz", "vin_v", "vout_v"]), "frequency_response")
        self.assertEqual(detect_kind(["vin_v", "iin_a", "vout_v", "iout_a"]), "power_efficiency")
        self.assertEqual(detect_kind(["reference", "observed"]), "linear_calibration")
        self.assertEqual(detect_kind(["x", "y"]), "column_summary")

    def test_frequency_response(self):
        rows = []
        for frequency in (10, 100, 1000, 10000):
            gain = 1 / math.sqrt(1 + (frequency / 1000) ** 2)
            rows.append({"frequency_hz": frequency, "vin_v": 1, "vout_v": gain})
        self._run_for_rows("frequency", ["frequency_hz", "vin_v", "vout_v"], rows)
        result = analyze_run(self.bench, "frequency")
        analysis = result["files"][0]["result"]
        self.assertEqual(analysis["kind"], "frequency_response")
        self.assertIsNotNone(analysis["cutoff_frequency_hz"])
        self.assertGreater(analysis["cutoff_frequency_hz"], 700)
        self.assertLess(analysis["cutoff_frequency_hz"], 1500)

    def test_efficiency(self):
        self._run_for_rows(
            "efficiency",
            ["vin_v", "iin_a", "vout_v", "iout_a"],
            [
                {"vin_v": 10, "iin_a": 1, "vout_v": 5, "iout_a": 1.6},
                {"vin_v": 10, "iin_a": 0.5, "vout_v": 5, "iout_a": 0.7},
            ],
        )
        result = analyze_run(self.bench, "efficiency")["files"][0]["result"]
        self.assertEqual(result["peak_efficiency_percent"], 80)
        self.assertEqual(result["kind"], "power_efficiency")

    def test_linear_calibration(self):
        self._run_for_rows(
            "calibration",
            ["reference", "observed"],
            [{"reference": 0, "observed": 1}, {"reference": 1, "observed": 3}],
        )
        result = analyze_run(self.bench, "calibration")["files"][0]["result"]
        self.assertAlmostEqual(result["slope"], 2)
        self.assertAlmostEqual(result["intercept"], 1)

    def test_summary(self):
        self._run_for_rows(
            "summary",
            ["time_s", "value_v"],
            [{"time_s": 0, "value_v": 1}, {"time_s": 1, "value_v": 3}],
        )
        result = analyze_run(self.bench, "summary")["files"][0]["result"]
        self.assertEqual(result["columns"]["value_v"]["mean"], 2)

    def test_uncertainty_attached(self):
        self._run_for_rows("budget", ["x"], [{"x": 1}, {"x": 2}])
        result = analyze_run(
            self.bench,
            "budget",
            uncertainty_components=[
                {"name": "resolution", "limit": 1, "distribution": "rectangular"}
            ],
        )
        self.assertIn("uncertainty_budget", result)

    def test_zero_input_rejected(self):
        self._run_for_rows(
            "zero-input",
            ["frequency_hz", "vin_v", "vout_v"],
            [
                {"frequency_hz": 1, "vin_v": 0, "vout_v": 1},
                {"frequency_hz": 2, "vin_v": 1, "vout_v": 1},
            ],
        )
        with self.assertRaisesRegex(ValueError, "may not be zero"):
            analyze_run(self.bench, "zero-input")

    def test_non_numeric_rejected(self):
        path = self.root / "data" / "raw" / "bad.csv"
        path.write_text("x\nnot-a-number\n", encoding="utf-8")
        self.bench.add_run(
            run_id="bad",
            study_id="study",
            operator="Researcher",
            started_at="2026-08-04T00:00:00+00:00",
            instruments=[],
            raw_files=["data/raw/bad.csv"],
            conditions={},
        )
        with self.assertRaisesRegex(ValueError, "non-numeric"):
            analyze_run(self.bench, "bad")


if __name__ == "__main__":
    unittest.main()
