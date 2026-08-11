import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from benchlineage.demo import build_demo
from benchlineage.eln import build_eln, verify_eln
from benchlineage.io import read_json, write_json
from benchlineage.provenance import seal_workspace


class ElnTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = build_demo(self.root / "workspace")

    def tearDown(self):
        self.temporary.cleanup()

    def test_export_is_valid_and_byte_stable(self):
        first = build_eln(self.workspace, self.root / "one" / "evidence.eln")
        second = build_eln(self.workspace, self.root / "two" / "evidence.eln")
        self.assertEqual(first.read_bytes(), second.read_bytes())

        result = verify_eln(first)
        self.assertTrue(result["valid"])
        self.assertEqual(result["root"], "evidence.eln")
        self.assertEqual(result["context"], "https://w3id.org/ro/crate/1.1/context")
        self.assertGreater(result["files"], 10)
        self.assertRegex(result["root_digest"], r"^sha256:[0-9a-f]{64}$")

        with zipfile.ZipFile(first) as archive:
            names = archive.namelist()
            self.assertTrue(all(name.startswith("evidence.eln/") for name in names))
            metadata = json.loads(archive.read("evidence.eln/ro-crate-metadata.json"))
        graph = {entity["@id"]: entity for entity in metadata["@graph"]}
        self.assertEqual(graph["ro-crate-metadata.json"]["version"], "1.0")
        self.assertEqual(graph["./"]["@type"], "Dataset")
        self.assertEqual(graph["./workspace/"]["@type"], "Dataset")
        self.assertEqual(graph["#instrument-scope-01"]["@type"], "IndividualProduct")
        self.assertEqual(graph["#run-rc-baseline-001"]["@type"], "CreateAction")
        self.assertEqual(
            graph["./workspace/data/raw/rc-baseline.csv"]["encodingFormat"],
            "text/csv",
        )

    def test_tampered_member_is_detected(self):
        original = build_eln(self.workspace, self.root / "original.eln")
        tampered = self.root / "tampered.eln"
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(tampered, "w") as target:
            for item in source.infolist():
                payload = source.read(item.filename)
                if item.filename.endswith("data/raw/rc-baseline.csv"):
                    payload += b"tampered\n"
                target.writestr(item, payload)
        result = verify_eln(tampered)
        self.assertFalse(result["valid"])
        self.assertIn(
            "original.eln/workspace/data/raw/rc-baseline.csv",
            result["changed"],
        )

    def test_unicode_and_space_containing_paths_round_trip(self):
        report = self.workspace.root / "reports" / "trace Ω #1.txt"
        report.write_text("portable evidence\n", encoding="utf-8")
        archive_path = build_eln(self.workspace, self.root / "unicode.eln")

        result = verify_eln(archive_path)
        self.assertTrue(result["valid"])
        with zipfile.ZipFile(archive_path) as archive:
            self.assertIn("unicode.eln/workspace/reports/trace Ω #1.txt", archive.namelist())
            metadata = json.loads(archive.read("unicode.eln/ro-crate-metadata.json"))
        identifiers = {entity["@id"] for entity in metadata["@graph"]}
        self.assertIn("./workspace/reports/trace%20%CE%A9%20%231.txt", identifiers)

    def test_missing_added_and_duplicate_members_are_detected(self):
        original = build_eln(self.workspace, self.root / "original.eln")
        omitted_name = "original.eln/workspace/data/raw/rc-baseline.csv"

        missing = self.root / "missing.eln"
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(missing, "w") as target:
            for item in source.infolist():
                if item.filename != omitted_name:
                    target.writestr(item, source.read(item.filename))
        self.assertIn(omitted_name, verify_eln(missing)["missing"])

        added = self.root / "added.eln"
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(added, "w") as target:
            for item in source.infolist():
                target.writestr(item, source.read(item.filename))
            target.writestr("original.eln/workspace/unlisted.txt", "not in the graph")
        self.assertIn(
            "original.eln/workspace/unlisted.txt",
            verify_eln(added)["added"],
        )

        duplicate = self.root / "duplicate.eln"
        duplicate.write_bytes(original.read_bytes())
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(duplicate, "a") as archive:
                archive.writestr(omitted_name, "second entry")
        self.assertIn(omitted_name, verify_eln(duplicate)["duplicates"])

    def test_multiple_roots_are_rejected(self):
        malformed = self.root / "malformed.eln"
        with zipfile.ZipFile(malformed, "w") as archive:
            archive.writestr("one/ro-crate-metadata.json", "{}")
            archive.writestr("two/file.txt", "unexpected")
        result = verify_eln(malformed)
        self.assertFalse(result["valid"])
        self.assertTrue(result["structure"])

    def test_non_object_metadata_and_unsafe_paths_are_rejected_without_a_traceback(self):
        malformed = self.root / "malformed.eln"
        with zipfile.ZipFile(malformed, "w") as archive:
            archive.writestr("malformed.eln/ro-crate-metadata.json", "[]")
            archive.writestr("malformed.eln/../escape.txt", "unsafe")
        result = verify_eln(malformed)
        self.assertFalse(result["valid"])
        self.assertIn("malformed.eln/../escape.txt", result["unsafe"])
        self.assertIn(
            "ro-crate-metadata.json must contain a JSON object",
            result["structure"],
        )

    def test_output_inside_workspace_and_wrong_extension_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside the workspace"):
            build_eln(self.workspace, self.workspace.root / "evidence.eln")
        with self.assertRaisesRegex(ValueError, "\\.eln"):
            build_eln(self.workspace, self.root / "evidence.zip")

    def test_incomplete_workspace_record_returns_a_concise_mapping_error(self):
        instrument = self.workspace.root / "instruments" / "scope-01.json"
        record = read_json(instrument)
        del record["manufacturer"]
        write_json(instrument, record)
        seal_workspace(self.workspace, label="malformed fixture")

        with self.assertRaisesRegex(ValueError, "cannot map workspace records"):
            build_eln(self.workspace, self.root / "invalid.eln")


if __name__ == "__main__":
    unittest.main()
