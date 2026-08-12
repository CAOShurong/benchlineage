# Data model

BenchLineage uses one directional lineage:

```text
workspace
├── study ───────────────┐
├── instrument ─┐        │
│   └── calibration      │
│                ├── run ┘
│                │    └── raw file(s)
│                └────────── analysis
└─────────────────────────── seal inventory
```

## Identity

Artifact identifiers are lowercase slugs containing ASCII letters, digits, and single hyphens.
They are durable human-readable identifiers, not globally unique identifiers. A repository or
archive location supplies the wider namespace.

## Workspace

`benchlineage.json` identifies the format, version, title, owner, creation time, and governing
principles. Optional owner email, given-name, and family-name fields allow an ELN importer to map
the archive author to a local account without guessing how to split a display name. These fields
are copied into exported archives, so omit them when the author's email should not be disclosed.

## Study

Required semantics:

- `id`: local durable identity;
- `title`: human-readable subject;
- `objective`: intended answer;
- `protocol`: planned procedure.

`hypothesis` and `tags` improve interpretation but are not required to claim that a protocol
exists.

## Instrument

An instrument record includes role, manufacturer, model, serial, asset tag, and notes. Two
instruments of the same model remain distinct because their serials and calibration histories may
differ.

## Calibration

A calibration has its own identity and points to exactly one instrument. BenchLineage stores a
certificate reference rather than asserting that a certificate file has been independently
validated.

## Run

A run is the junction of intent and evidence:

- one study;
- zero or more registered instruments;
- one or more raw files;
- operator and timestamp;
- structured environmental or configuration conditions;
- deliberate deviations from protocol;
- notes.

Raw paths are workspace-relative and may not escape the workspace root.

## Analysis

An analysis identifies one run and contains one result per raw file. Built-in result kinds are
versioned under the parent `benchlineage/analysis/v1` contract.

## Seal

A seal contains:

- an ordered file inventory;
- byte length and SHA-256 digest per path;
- explicit included and excluded scope;
- one root digest;
- creation timestamp and optional label.

The schemas in [`../schemas`](../schemas/) are intended for interoperability and editor tooling.
Runtime checks additionally validate cross-file relationships that JSON Schema cannot express.

## Forward compatibility

Readers should:

- reject an unknown major schema version;
- preserve unknown fields when round-tripping records;
- treat an absent optional field differently from a field with an empty value;
- never silently reinterpret units;
- never mutate raw evidence to satisfy a newer schema.
