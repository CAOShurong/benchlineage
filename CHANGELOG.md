# Changelog

All notable changes to BenchLineage are documented here.

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
