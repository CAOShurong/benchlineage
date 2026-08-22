import hashlib
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
            self.assertFalse(any(info.is_dir() for info in archive.infolist()))
            metadata = json.loads(archive.read("evidence.eln/ro-crate-metadata.json"))
        graph = {entity["@id"]: entity for entity in metadata["@graph"]}
        self.assertEqual(graph["ro-crate-metadata.json"]["version"], "1.0")
        self.assertEqual(graph["./"]["@type"], "Dataset")
        license_id = graph["./"]["license"]["@id"]
        self.assertEqual(license_id, "https://spdx.org/licenses/MIT.html")
        self.assertEqual(graph[license_id]["name"], "MIT License")
        self.assertIn("synthetic demonstration", graph[license_id]["description"])
        self.assertEqual(graph["./workspace/"]["@type"], "Dataset")
        self.assertEqual(graph["./workspace/"]["genre"], "experiment")
        owner = graph["./workspace/"]["author"]["@id"]
        self.assertEqual(graph[owner]["email"], "benchlineage-demo@example.invalid")
        self.assertEqual(graph[owner]["givenName"], "Shurong")
        self.assertEqual(graph[owner]["familyName"], "Cao")
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

    def test_workspace_without_optional_owner_identity_still_exports(self):
        metadata_path = self.workspace.root / "benchlineage.json"
        metadata = read_json(metadata_path)
        for field in ("owner_email", "owner_given_name", "owner_family_name"):
            metadata.pop(field)
        write_json(metadata_path, metadata)
        seal_workspace(self.workspace, label="legacy owner metadata")

        archive_path = build_eln(self.workspace, self.root / "legacy-owner.eln")
        self.assertTrue(verify_eln(archive_path)["valid"])
        with zipfile.ZipFile(archive_path) as archive:
            crate = json.loads(archive.read("legacy-owner.eln/ro-crate-metadata.json"))
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        owner_id = graph["./workspace/"]["author"]["@id"]
        self.assertNotIn("email", graph[owner_id])

    def test_workspace_without_data_license_keeps_explicit_reuse_warning(self):
        metadata_path = self.workspace.root / "benchlineage.json"
        metadata = read_json(metadata_path)
        for field in (
            "data_license_url",
            "data_license_name",
            "data_license_description",
        ):
            metadata.pop(field)
        write_json(metadata_path, metadata)
        seal_workspace(self.workspace, label="undeclared data license")

        archive_path = build_eln(self.workspace, self.root / "unlicensed.eln")
        with zipfile.ZipFile(archive_path) as archive:
            crate = json.loads(archive.read("unlicensed.eln/ro-crate-metadata.json"))
        graph = {entity["@id"]: entity for entity in crate["@graph"]}
        self.assertEqual(
            graph["./"]["license"],
            "No data license was declared; contact the workspace author before reuse.",
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
        self.assertIn("./workspace/reports/trace%20Ω%20%231.txt", identifiers)

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

    def test_parent_child_datasets_and_standard_preview_are_supported(self):
        payload = b"third-party producer payload\n"
        digest = hashlib.sha256(payload).hexdigest()
        metadata = {
            "@context": "https://w3id.org/ro/crate/1.2/context",
            "@graph": [
                {
                    "@id": "ro-crate-metadata.json",
                    "@type": "CreativeWork",
                    "about": {"@id": "./"},
                    "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"},
                },
                {
                    "@id": "./",
                    "@type": "Dataset",
                    "name": "Third-party export",
                    "hasPart": [{"@id": "./parent/"}, {"@id": "./child/"}],
                },
                {
                    "@id": "./parent/",
                    "@type": "Dataset",
                    "name": "Parent experiment",
                    "hasPart": [{"@id": "./child/"}],
                },
                {
                    "@id": "./child/",
                    "@type": "Dataset",
                    "name": "Child experiment",
                    "hasPart": [{"@id": "./child/result.txt"}],
                },
                {
                    "@id": "./child/result.txt",
                    "@type": "File",
                    "name": "result.txt",
                    "contentSize": str(len(payload)),
                    "sha256": digest,
                },
            ],
        }
        archive_path = self.root / "third-party.eln"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("third-party/ro-crate-metadata.json", json.dumps(metadata))
            archive.writestr("third-party/child/result.txt", payload)
            archive.writestr(
                "third-party/ro-crate-preview.html", "<!doctype html><title>Preview</title>"
            )
            archive.writestr("third-party/ro-crate-preview_files/style.css", "body {}")
            archive.writestr("third-party/ro-crate-metadata.json.minisig", "untrusted fixture")

        result = verify_eln(archive_path)

        self.assertTrue(result["valid"])
        self.assertEqual(result["added"], [])
        self.assertEqual(
            result["unverified_ancillary"],
            [
                "third-party/ro-crate-metadata.json.minisig",
                "third-party/ro-crate-preview.html",
                "third-party/ro-crate-preview_files/style.css",
            ],
        )

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

    def test_tags_containing_commas_round_trip_as_distinct_keywords(self):
        study_path = sorted((self.workspace.root / "studies").glob("*.json"))[0]
        record = read_json(study_path)
        record["tags"] = ["gain, phase", "stability"]
        write_json(study_path, record)
        seal_workspace(self.workspace, label="comma tags fixture")

        export = build_eln(self.workspace, self.root / "comma.eln")
        with zipfile.ZipFile(export) as archive:
            metadata = json.loads(archive.read("comma.eln/ro-crate-metadata.json"))
        graph = metadata["@graph"]
        study = next(
            entity
            for entity in graph
            if entity.get("@type") == "CreativeWork" and entity.get("name") == record["title"]
        )
        self.assertEqual(study["keywords"], ["gain, phase", "stability"])
        root = next(entity for entity in graph if entity.get("genre") == "experiment")
        self.assertIn("gain, phase", root["keywords"])
        self.assertIn("stability", root["keywords"])
        self.assertIsInstance(root["keywords"], list)

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
