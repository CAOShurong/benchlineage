import json
import tempfile
import unittest
from pathlib import Path

from benchlineage.io import canonical_json, digest_bytes, read_json, safe_identifier
from benchlineage.workspace import Workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "bench"
        self.bench = Workspace(self.root)
        self.bench.initialize(title="Test bench", owner="Researcher")

    def tearDown(self):
        self.temporary.cleanup()

    def test_layout_created(self):
        self.assertTrue((self.root / "data" / "raw").is_dir())
        self.assertEqual(self.bench.require()["title"], "Test bench")

    def test_refuses_reinitialize(self):
        with self.assertRaises(FileExistsError):
            self.bench.initialize(title="Again", owner="Researcher")

    def test_identifier_normalization(self):
        self.assertEqual(safe_identifier("Scope 01"), "scope-01")
        with self.assertRaises(ValueError):
            safe_identifier("../outside")

    def test_instrument_roundtrip(self):
        result = self.bench.add_instrument(
            instrument_id="scope-01",
            kind="oscilloscope",
            manufacturer="Maker",
            model="Model",
            serial="123",
        )
        self.assertEqual(result["id"], "scope-01")
        self.assertEqual(self.bench.records("instruments")[0]["serial"], "123")

    def test_calibration_requires_instrument(self):
        with self.assertRaisesRegex(ValueError, "unknown instrument"):
            self.bench.add_calibration(
                calibration_id="cal-1",
                instrument_id="missing",
                performed_at="2026-01-01T00:00:00+00:00",
                due_at="2027-01-01T00:00:00+00:00",
                certificate="CERT",
                standard_uncertainty=1,
                unit="V",
            )

    def test_study_requires_protocol(self):
        with self.assertRaisesRegex(ValueError, "required"):
            self.bench.create_study(
                study_id="s1", title="Study", objective="Objective", hypothesis="", protocol=""
            )

    def test_run_rejects_unknown_study(self):
        with self.assertRaisesRegex(ValueError, "unknown study"):
            self.bench.add_run(
                run_id="r1",
                study_id="missing",
                operator="Researcher",
                started_at="2026-01-01T00:00:00+00:00",
                instruments=[],
                raw_files=[],
                conditions={},
            )

    def test_copy_csv_normalizes_and_protects_destination(self):
        source = Path(self.temporary.name) / "source.csv"
        source.write_text("time_s,value_v\r\n0,1\r\n1,2\r\n", encoding="utf-8")
        destination = self.bench.copy_csv(
            source, destination_name="trace-one", required_columns=["time_s", "value_v"]
        )
        self.assertEqual(destination.read_text(encoding="utf-8"), "time_s,value_v\n0,1\n1,2\n")
        with self.assertRaises(FileExistsError):
            self.bench.copy_csv(source, destination_name="trace-one")

    def test_copy_csv_rejects_missing_column(self):
        source = Path(self.temporary.name) / "source.csv"
        source.write_text("x,y\n1,2\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing columns"):
            self.bench.copy_csv(source, destination_name="trace", required_columns=["z"])

    def test_canonical_json_and_digest(self):
        payload = canonical_json({"b": 2, "a": 1})
        self.assertEqual(payload, '{"a":1,"b":2}')
        self.assertRegex(digest_bytes(payload.encode()), r"^sha256:[0-9a-f]{64}$")

    def test_json_writer_is_readable(self):
        metadata = read_json(self.root / "benchlineage.json")
        self.assertEqual(metadata["format_version"], "1.0")
        json.loads((self.root / "benchlineage.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
