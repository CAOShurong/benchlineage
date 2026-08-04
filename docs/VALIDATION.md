# Validation strategy

BenchLineage is tested at five layers.

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

## 4. End-to-end workflow

The deterministic demonstration is generated from an empty directory, analyzed, sealed, audited,
reported, and compared with the committed fixture. The generated report is inspected for:

- self-contained CSS and JavaScript;
- no external script, stylesheet, image, font, or tracker;
- escaped record text;
- embedded source payload;
- expected chart, audit, and evidence-root sections.

## 5. Packaging and platform

CI runs on Windows and Ubuntu with Python 3.11 and 3.13. Release validation builds a wheel, installs
it into an isolated target, executes the CLI, generates the demonstration, and verifies its seal.

Passing tests do not validate a user's physical experiment or uncertainty model.
