# Methodology

## 1. Claim boundary

BenchLineage records a chain of artifacts around an engineering experiment. It can establish that:

- a study record existed in the inspected workspace;
- a run names particular instruments, conditions, and raw files;
- an analysis record names a run and contains deterministic outputs;
- an evidence inventory matches a declared SHA-256 root.

It cannot establish that:

- a stated instrument was physically connected;
- a calibration certificate is authentic;
- a measurement method was scientifically appropriate;
- uncertainty components are complete;
- an operator did not fabricate an internally consistent workspace.

The distinction matters. Integrity is not authenticity, and authenticity is not scientific
validity.

## 2. Artifact lifecycle

### 2.1 Research intent

A study states the objective, hypothesis, and protocol before or alongside data collection.
BenchLineage does not enforce preregistration timing because a local clock is not a trusted
timestamp. Version control or an external registry can provide stronger temporal evidence.

### 2.2 Instrument identity

An instrument record separates the human-readable role from manufacturer, model, serial, and asset
tag. Serial numbers should refer to physical equipment; public demonstrations must use obviously
synthetic values.

### 2.3 Calibration coverage

A calibration record names one instrument, performance date, due date, certificate reference,
standard uncertainty, unit, coverage factor, and status. Audit checks whether a valid calibration
record covers each run timestamp. This is a documented-traceability check, not certificate
validation.

### 2.4 Raw evidence

Raw data lives under `data/raw/` and is referenced by a run. BenchLineage does not rewrite raw
evidence during analysis. The optional CSV-copy operation normalizes a source into a new evidence
file and refuses to overwrite an existing destination.

### 2.5 Derived analysis

An analysis is replaceable. It references a run, whose raw-file paths remain authoritative.
Built-in analyses are deterministic for the same input bytes and package version.

### 2.6 Uncertainty budget

Each component records a standard uncertainty directly or a stated limit plus distribution.
Sensitivity coefficients translate an input component into the output quantity. Independent
contributions are combined by root-sum-square. Correlation is not currently modeled.

### 2.7 Audit

Audit traverses references instead of validating files in isolation. Stable finding codes make
results suitable for CI:

| Code | Meaning |
|---|---|
| `workspace.invalid` | Missing or unsupported root record |
| `json.invalid` | A durable JSON artifact cannot be parsed |
| `id.duplicate` | Two artifacts claim the same identity |
| `calibration.instrument` | Calibration points to an unknown instrument |
| `calibration.dates` | Calibration timestamps are malformed or reversed |
| `run.study` | Run points to an unknown study |
| `run.instrument` | Run points to an unknown instrument |
| `run.raw.escape` | Raw-data reference resolves outside the workspace |
| `run.raw.missing` | Referenced raw file does not exist |
| `run.calibration` | No in-date valid calibration covers an instrument |
| `raw.orphan` | Raw file is not referenced by a run |
| `analysis.run` | Analysis points to an unknown run |
| `seal.invalid` | Latest seal no longer matches evidence |
| `seal.missing` | No evidence seal exists |

Errors fail audit. Warnings expose incomplete traceability without making early-stage work
impossible.

## 3. Content sealing

The sealing algorithm is:

1. Enumerate all workspace files except `reports/**` and `seals/**`.
2. Sort paths using their forward-slash relative representation.
3. Record each file's byte length and SHA-256 digest.
4. Canonically encode an ordered list containing only `path` and `digest`.
5. Compute the SHA-256 digest of that canonical JSON.
6. Write the inventory and root digest to a new seal record.

Reports are excluded because presentation should be regenerable from evidence. Previous seals are
excluded to avoid recursive hashing.

Verification checks:

- the stored inventory hashes to the declared root;
- every declared path still exists;
- every current file digest matches;
- no additional evidence file exists when strict mode is enabled.

This resembles a flat content-addressed manifest, not a blockchain and not a digital signature.

## 4. Built-in analysis assumptions

### Frequency response

Gain is `abs(vout / vin)`. Gain in decibels is `20 log10(gain)`. The passband estimate is the mean
of the first one to five points, depending on sweep length. The cutoff target is 3.0103 dB below
that estimate. Crossing is linearly interpolated in log-frequency space.

This method assumes the sweep begins in the passband and contains a single relevant crossing.

### Power efficiency

Input and output power are the products of recorded voltage and current. Efficiency is
`100 × Pout / Pin`; input power must be positive. No phase, harmonics, or timing correction is
inferred.

### Linear calibration

Ordinary least squares fits `observed = intercept + slope × reference`. The implementation reports
R² and root-mean-square residual. It does not account for uncertainty in both axes.

### Column summary

Each CSV cell must be finite and numeric. Standard deviation uses the sample definition when two or
more rows exist. A one-row column has zero reported standard deviation.

## 5. Reproducibility controls

- JSON outputs use sorted keys and stable indentation.
- Demo pseudo-randomness is seeded.
- Durable record identifiers are path-safe lowercase slugs.
- Reports embed their complete source payload.
- CI runs on Windows and Ubuntu across supported Python versions.
- The wheel is installed and exercised in isolation during release validation.

## 6. Recommended publication statement

A paper or dataset using BenchLineage should report:

- BenchLineage version and repository commit;
- workspace root digest;
- whether seal verification passed;
- which findings remained in audit;
- acquisition software and raw binary formats outside BenchLineage;
- analysis code or extension version;
- any redaction performed before public release.

## 7. Publication bundles

`benchlineage bundle` packages every workspace file, including reports and
seals, under a fixed `workspace/` prefix. `BUNDLE-MANIFEST.json` records the
byte length and SHA-256 digest of every included member, the latest sealed
evidence root, and the audit summary. Fixed member order, timestamps,
permissions, and compression settings make a bundle byte-stable when the
workspace bytes and BenchLineage version are unchanged.

`verify-bundle` reads without extracting, rejects unsafe or duplicate member
paths, and reports missing, added, or changed members. The ZIP is not encrypted
or digitally signed. A valid bundle proves internal byte consistency, not
authorship, trusted time, certificate authenticity, or scientific validity.
