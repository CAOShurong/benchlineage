# ELN interoperability

BenchLineage exports the open `.eln` exchange format maintained by the
[ELN Consortium](https://the.elnconsortium.org/specification/). This is an interoperability path,
not a claim that BenchLineage is a complete electronic laboratory notebook.

## Why this format

An `.eln` file is a ZIP archive containing one root directory and an attached RO-Crate. The
Consortium lists import or export implementations in eLabFTW, Kadi4Mat, PASTA, RSpace, SampleDB,
NOMAD, LinkAhead, OpenSemanticLab, SciLog, and datalab. That makes the format a better handoff
target than a BenchLineage-only archive when a record must enter an institutional system.

The current Consortium specification accepts RO-Crate 1.1 and newer, while its published test
suite still validates the RO-Crate 1.1 profile. BenchLineage therefore emits a flattened,
compacted RO-Crate 1.1 document. This is a deliberate compatibility choice; using the newest core
RO-Crate context would not by itself prove that deployed ELN importers accept the archive.

## Archive layout

```text
thesis-bench.eln
└── thesis-bench.eln/
    ├── ro-crate-metadata.json
    └── workspace/
        ├── benchlineage.json
        ├── studies/
        ├── instruments/
        ├── calibrations/
        ├── runs/
        ├── data/raw/
        ├── analysis/
        ├── reports/
        └── seals/
```

The outer ZIP contains exactly one root directory. The original workspace hierarchy is preserved
below one ELN `Dataset`, so importers that ignore BenchLineage-specific linked data still receive
the durable source records and raw bytes.

## Metadata mapping

| BenchLineage artifact | RO-Crate / ELN representation | Important links |
|---|---|---|
| Workspace | Root `Dataset` plus one experiment `Dataset` | owner, files, studies, equipment, actions |
| Owner and operators | `Person` | dataset `author`, run `agent` |
| Study | `CreativeWork` | objective, hypothesis, protocol, tags |
| Instrument | `IndividualProduct` | manufacturer, model, serial number, asset tag |
| Calibration | `CreativeWork` | instrument, certificate, coverage window, uncertainty statement |
| Experimental run | `CreateAction` | operator, study, equipment, time, raw-file results |
| Analysis | `CreateAction` | raw-file inputs, BenchLineage software, JSON result |
| Workspace file | `File` | media type, byte length, SHA-256 digest |
| Latest seal | Dataset `identifier` | BenchLineage root digest |

The experiment Dataset declares `genre: experiment`, which lets importers such as eLabFTW and
SampleDB select an experiment/measurement record without a product-specific type override. When
the workspace includes optional owner email, given-name, and family-name fields, they are emitted
on the author `Person`; importers may otherwise require the operator to select an existing user.

The metadata document uses an inline JSON-LD mapping for the ELN Consortium's `sha256` field. No
network lookup is required to understand or verify file digests.

The Dataset `identifier` is the latest BenchLineage evidence root. Its scope is intentionally the
same as a native seal: durable evidence is covered, while generated reports and seal records are
excluded. The ELN graph separately records a size and SHA-256 digest for every included file,
including reports and seals, so the finished archive verifier still detects any changed member.

## Export and verify

```bash
benchlineage audit thesis-bench
benchlineage verify thesis-bench
benchlineage export-eln thesis-bench --output thesis-bench.eln
benchlineage verify-eln thesis-bench.eln
```

Export refuses an unsealed workspace, a failing semantic audit, an invalid latest seal, an output
inside the source workspace, or an output name without the `.eln` extension. The writer fixes ZIP
timestamps, permissions, order, and compression settings; unchanged workspace bytes and the same
archive filename produce identical archive bytes.

The built-in verifier never extracts the archive. It checks:

- one safe root directory and one root metadata document;
- duplicate, absolute, parent-traversal, backslash, and drive-like member paths;
- JSON-LD context, descriptor, root Dataset, entity identities, types, and `hasPart` references;
- parent/child Dataset relationships, including the Consortium rule that an importable child also
  appears in the root Dataset's import list;
- every local File entity against the corresponding ZIP member's size and SHA-256 digest;
- missing, unlisted, or changed payload files.

RO-Crate reserves `ro-crate-preview.html` and `ro-crate-preview_files/` for a human-readable
website and recommends that these members not appear in Dataset `hasPart`. ELN metadata signatures
also sit beside the metadata document. The verifier therefore reports unlisted members at exactly
these paths as `unverified_ancillary`: they do not make the archive fail, but their bytes and trust
are outside the declared File-digest result. Any other unlisted file remains a failure.

CI additionally runs the ELN Consortium's four published suites at commit
`19028dd2878065b34df7a7df836babaa61ad2845`: parsing with `rocrate` 0.15.1, Consortium parameter
rules, JSON Schema with `jsonschema` 4.25.1, and `roc-validator` 0.11.3 against the required RO-Crate
1.1 profile. These are development checks only; the installed BenchLineage runtime remains
dependency-free.

## Real importer acceptance

All experiments in this section were run by the BenchLineage maintainer. They are integration
tests against real upstream software, not reports from independent users and not adoption evidence.

On 2026-08-12, the demo generated by an installed BenchLineage 0.3.1 wheel was imported with the
official `elabftw/elabimg:stable` container at image digest
`sha256:db6f369e0593203ff2d3045671eaadceca60ccfefa5ef22a9b62f485d3cd4a4f`, which identified
itself as eLabFTW 5.6.12. The import used the native
`bin/console import:eln benchlineage-0.3.1-demo.eln 1` command: no entity-type or user override was
supplied.

The observed database delta was one Experiment and zero Resources. The imported Experiment kept
the title `Power-conversion and RC-filter characterization`; eLabFTW created the declared author
as `Shurong Cao`, and all 21 attachment rows created by its importer had a SHA-256 value. The
final source archive was 32,021 bytes with SHA-256
`f3775c2a9c03133541ceddfa01bd730999b3a93aede63ad16c61f5456d42f29e` and separately passed
`benchlineage verify-eln` before import.

This is a tested handoff for one deterministic fixture and one importer version. It does not imply
that eLabFTW renders every BenchLineage-specific linked-data entity, or that every `.eln` producer
and consumer agrees on all optional metadata.

In a separate negative-path experiment, `benchlineage verify-eln` returned failure after one CSV
byte sequence was changed without updating its declared digest. eLabFTW 5.6.12 logged the same
SHA-256 mismatch but still returned command success and created the record with its default
checksum-error policy. Treat a successful consumer import as a handoff result, not as proof of
archive integrity; verify the source archive independently before import.

The same day, the official SampleDB source at commit
`f135e5dc2923e1bf473f0698a34fbe4616248673` (`v0.33.1-77-gf135e5dc`) was run locally against
PostgreSQL 15.18. Its real `create_eln_import`, `parse_eln_file`, and `import_eln_file` paths parsed
and persisted the BenchLineage 0.3.2 candidate as one object and one imported user.
The title was preserved, and all 20 RO-Crate File entities matched the persisted attachments by
original filename, byte length, and SHA-256. The same test harness also imported SampleDB's
Kadi4Mat example fixture, providing an independent producer baseline for the local environment.

SampleDB rejected the original 0.3.0 and 0.3.1 archive structure before metadata parsing because
explicit empty directory ZIP members made its root-directory check observe an additional empty
parent. BenchLineage 0.3.2 omits directory members; the 21 file members still imply the same root
and workspace hierarchy without duplicating it as empty entries.

## Third-party producer fixtures

The 0.3.3 compatibility matrix exercises the installed package in the reverse direction against
two public archives that were produced outside BenchLineage. These are maintainer-run checks, not
independent adoption and not proof that BenchLineage imports their domain model.

| Producer fixture | Public source and declared identity | SHA-256 | Observed scope |
|---|---|---|---|
| eLabFTW 5.6.9 team export | Zenodo DOI `10.5281/zenodo.21413739`; the record is CC BY 4.0 and the archive root declares CC BY-NC-SA 4.0 | `39958ee74e4be13925ab003659514f93059397b824662d43597ecde2803f1c7c` | 128 declared File payloads matched; one standard HTML preview was reported as unverified ancillary material |
| SampleDB `v0.32.0-4-gebff0633` export | ELN Consortium example at commit `19028dd2878065b34df7a7df836babaa61ad2845`; repository MIT, while the archive's root Dataset says `No License` | `eab127863e36ad8849875cdbad157796fd9d6925a6f01d01fd06a15769bf3d50` | 8 declared File payloads matched; parent/child Datasets were accepted; the standard HTML preview and metadata signature were reported as unverified ancillary material |

The SampleDB crate separately passed all 65 required checks in `roc-validator` 0.11.3's RO-Crate
1.2 profile. The eLabFTW crate did not pass that independent profile because of its JSON-LD
flattening and availability details; BenchLineage's result only covers its documented structural
and payload-integrity checks. Neither third-party archive is copied into this repository because
their embedded data-license statements are more restrictive or ambiguous than their host record.

## Limits

- Export is one-way. BenchLineage does not import arbitrary `.eln` archives into
  its stricter workspace schemas.
- Passing format validation does not show that a target application's user interface preserves or
  displays every domain-specific entity.
- The archive carries hashes, not a trusted signature or timestamp. Anyone who can replace both a
  file and its metadata can create a different internally consistent archive.
- No data license is inferred. When the workspace declares none, the root Dataset explicitly says
  to contact the author before reuse.
- Format validity, integrity, and provenance do not establish that an experiment was performed
  correctly or honestly.

## Primary specifications

- [ELN Consortium specification](https://github.com/TheELNConsortium/TheELNFileFormat/blob/master/SPECIFICATION.md)
- [ELN implementations and examples](https://github.com/TheELNConsortium/TheELNFileFormat)
- [RO-Crate 1.1](https://w3id.org/ro/crate/1.1)
- [RO-Crate provenance model](https://www.researchobject.org/ro-crate/specification/1.1/provenance.html)
