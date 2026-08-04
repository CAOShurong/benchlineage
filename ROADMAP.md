# Roadmap

BenchLineage follows evidence needs rather than feature count. Items move only when a concrete
research workflow and validation case exist.

## 0.2 — Interoperability

- CSV dialect profiles for common oscilloscopes, source-measure units, VNAs, and power analyzers.
- A stable plug-in protocol for external analysis tools without adding them as core dependencies.
- RO-Crate export and mapping notes for DataCite and institutional repositories.
- Optional detached Ed25519 signatures in addition to content digests.
- A machine-readable comparison between two evidence seals.

## 0.3 — Engineering depth

- Waveform feature extraction with explicit sampling and window assumptions.
- Bode-fit uncertainty propagation and repeated-sweep aggregation.
- Power-loss decomposition and thermal stabilization checks.
- Monte Carlo uncertainty propagation as an optional extension.
- Binary-file sidecars for waveform and image formats that should not be converted to CSV.

## 0.4 — Collaboration without a central service

- Merge-aware record identifiers and conflict reports.
- Reviewer annotations stored as separate immutable records.
- Optional trusted timestamp and institutional-signature adapters.
- Redaction manifests that preserve evidence-chain structure for public releases.

## Explicit non-goals

- Becoming a general note-taking editor.
- Replacing institutional identity, permissions, retention, or backup systems.
- Claiming regulatory compliance from a local file format.
- Building a proprietary cloud or mandatory account.
- Pretending a hash can establish measurement truth.
