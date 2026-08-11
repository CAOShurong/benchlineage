# Validation strategy

BenchLineage is tested at six layers.

## 1. Unit behavior

- identifier normalization and rejection;
- unit normalization, compatibility, and conversion;
- numerical summaries and regression;
- uncertainty conversion and root-sum-square combination;
- deterministic canonical JSON and file digests.

## 2. Artifact integration

- workspace initialization;
- instrument, calibration, study, and run creation;
- unknown-reference rejection;
- raw path containment;
- analysis auto-detection;
- calibration-window audit.

## 3. Integrity behavior

- a fresh seal verifies;
- changing one raw byte fails verification;
- removing an inventoried file fails verification;
- adding evidence fails strict verification;
- stored-inventory manipulation invalidates the declared root.
- publication bundles are byte-stable for unchanged workspaces;
- modified ZIP members fail bundle verification;
- bundle paths cannot escape during extraction.
- ELN archives are byte-stable for unchanged workspaces;
- duplicate, unsafe, missing, added, or modified ELN members fail verification;
- percent-encoded file identifiers round-trip to Unicode and space-containing member names.

## 4. End-to-end workflow

The deterministic demonstration is generated from an empty directory, analyzed, sealed, audited,
reported, and compared with the committed fixture. The generated report is inspected for:

- self-contained CSS and JavaScript;
- no external script, stylesheet, image, font, or tracker;
- escaped record text;
- embedded source payload;
- expected chart, audit, and evidence-root sections.

## 5. Interchange compatibility

The generated `.eln` archive is checked in three independent ways:

- BenchLineage verifies the ZIP layout, RO-Crate graph, listed payloads, sizes, and SHA-256 values
  without extracting it;
- the Python `rocrate` library opens the extracted graph;
- `roc-validator` evaluates the required RO-Crate 1.1 profile.

Release candidates are also exercised against the ELN Consortium's four published test suites:
the PyPI `rocrate` parser, Consortium parameter rules, JSON Schema, and `roc-validator`. These
checks establish structural compatibility with the published interchange tests. They do not prove
successful import into every ELN product, because individual importers may implement only part of
the exchange format or add product-specific constraints.

## 6. Packaging and platform

CI runs on Windows and Ubuntu with Python 3.11, 3.13, and 3.14. Release validation builds a wheel,
installs it into an isolated target, executes the CLI, generates the demonstration, and verifies
its seal. The same smoke test creates and verifies both a publication bundle and an ELN exchange
archive.

Passing tests do not validate a user's physical experiment or uncertainty model.
