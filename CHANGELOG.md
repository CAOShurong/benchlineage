# Changelog

All notable changes to BenchLineage are documented here.

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
