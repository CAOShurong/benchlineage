# Changelog

All notable changes to BenchLineage are documented here.

## 0.3.6 - 2026-08-23

### Changed

- `.eln` export now rejects tags that contain commas with a concise, actionable error: the ELN
  Consortium test suite requires keywords as one comma-separated string, which cannot represent
  such a tag without silently splitting it into different keywords on import. Previously the
  ambiguous value was exported without warning (see the property-type discussion in
  TheELNFileFormat/TheELNFileFormat#158).

## 0.3.5 - 2026-08-13

### Added

- Added optional workspace-level data-license URL, name, and description fields to `init`, with
  concise rejection of partial, relative, credential-bearing, or non-string declarations.
- Linked licensed `.eln` exports to a named RO-Crate `CreativeWork` entity while preserving the
  explicit contact-the-author warning for undeclared workspaces.

### Changed

- Declared the public synthetic demonstration data under the repository's existing MIT license;
  this declaration does not apply to user-created workspaces.
- Documented the difference between code licensing and an explicit workspace data-license
  declaration.

### Verified

- Covered CLI, workspace, persisted-audit, licensed-export, undeclared-export, deterministic-demo,
  and self-contained-report paths with regression tests.

## 0.3.4 - 2026-08-12

### Fixed

- Escaped CLI JSON as ASCII so Unicode values still round-trip when Windows uses a legacy console
  code page, including after commands have written durable artifacts.
- Rejected missing or blank workspace titles and owners with the existing structured
  `workspace.invalid` audit result instead of exposing a Python traceback.
- Accepted BOM-prefixed UTF-8 JSON argument files produced by Windows PowerShell 5.1 while keeping
  durable workspace records strictly BOM-free.
- Preserved non-ASCII characters in ELN File IRIs while percent-encoding ASCII delimiters, so ZIP
  member names remain resolvable by consumers that compare IRI paths literally.

### Verified

- Reproduced all four failures from fresh public 0.3.3 wheel and sdist installs, then reran the
  installed-package success and failure paths without a UTF-8 environment workaround.
- Parsed the corrected synthetic CC0 export with the current SampleDB default-branch ELN parser
  and passed the current TheELNFileFormat default-branch test suite. These are maintainer-run
  compatibility checks, not evidence of independent adoption.

## 0.3.3 - 2026-08-12

### Fixed

- Accepted parent/child Dataset relationships permitted by the current ELN Consortium
  specification, so current SampleDB exports no longer fail verification.
- Reported standard RO-Crate preview files and ELN metadata signatures as unverified ancillary
  members instead of treating them as undeclared evidence payloads.

### Verified

- Pinned public eLabFTW 5.6.9 and SampleDB producer archives by source and SHA-256, then exercised
  them in CI without redistributing their data in this repository.

## 0.3.2 - 2026-08-12

### Fixed

- Omit explicit empty directory members from `.eln` archives so strict downstream importers see
  exactly one archive root.

## 0.3.1 - 2026-08-12

### Fixed

- Declared exported ELN datasets as experiments so eLabFTW and SampleDB can select their native
  experiment/measurement record types without a product-specific override.
- Added optional explicit owner identity fields and included them in exported author metadata;
  the deterministic demo can now be imported without assigning an existing eLabFTW user.
- Rejected run records whose recorded timestamp precedes their start timestamp and corrected the
  public deterministic demonstration.

### Verified

- Imported the installed-package demo archive into the official eLabFTW 5.6.12 Docker image and
  inspected the resulting entity type, title, payload count, hashes, and source archive digest.

## 0.3.0 - 2026-08-11

### Added

- Deterministic `.eln` export for moving a sealed BenchLineage workspace into tools that implement
  the ELN Consortium exchange format.
- A dependency-free `verify-eln` command that checks archive structure, path safety, metadata,
  listed payloads, sizes, and SHA-256 digests without extracting the archive.
- A machine-readable `diff-seals` command for reviewing added, removed, and changed evidence
  between two workspace seals.
- Explicit mapping notes for studies, runs, instruments, analyses, people, files, and integrity
  claims in the exported RO-Crate graph.

### Changed

- Extended package and release smoke tests to exercise ELN export and verification.
- Added Python 3.14 to the supported CI matrix.
- Updated the generated demonstration and report provenance to identify BenchLineage 0.3.0.

## 0.2.1 — 2026-08-05

### Added

- PyPI Trusted Publishing with short-lived GitHub OIDC credentials and publish attestations.
- PyPI-safe README graphics and links, a large social preview, and a direct package-install path.
- A community discussion route alongside the existing engineering-analysis request form.

### Changed

- Split package construction, PyPI publication, and GitHub Release publication into separate
  least-privilege jobs that share one verified distribution artifact.
- Updated generated report and bundle provenance to identify BenchLineage 0.2.1.

## 0.2.0 — 2026-08-05

### Added

- Deterministic publication ZIPs with fixed archive metadata and a plain
  SHA-256 member manifest.
- `verify-bundle` checks for unsafe, duplicate, missing, added, and changed
  archive members without extraction.
- Versioned GitHub Release installation, checksums, and package smoke tests.

### Changed

- Rebuilt the README graphics, site, and generated report around a restrained
  academic visual system.
- Clarified the product gap, scientific claim boundary, and publication
  workflow.
- Updated supported GitHub Actions to their current major versions.

## 0.1.1 — 2026-08-04

### Fixed

- Quantized synthetic derived values to remove insignificant cross-platform `libm` and
  `statistics` drift from the committed deterministic demonstration.
- Updated packaging metadata for current PEP 639-compatible setuptools releases.

## 0.1.0 — 2026-08-04

### Added

- Transparent workspace, study, instrument, calibration, run, analysis, and seal records.
- Deterministic frequency-response, power-efficiency, linear-calibration, and column-summary analyses.
- GUM-inspired uncertainty budgets with explicit distributions and sensitivity coefficients.
- Cross-artifact audit covering identifiers, references, files, calibration windows, and seal state.
- SHA-256 evidence inventories, root digests, tamper verification, and seal comparison.
- Self-contained interactive HTML reports with no CDN, tracker, database, or server.
- A deterministic synthetic EE demonstration with two studies and three experimental runs.
- JSON Schema contracts, methodology, competitive landscape, CI, and GitHub Pages.
