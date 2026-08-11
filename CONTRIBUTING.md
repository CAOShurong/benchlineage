# Contributing

BenchLineage welcomes focused contributions that preserve transparent evidence and dependency-free
core operation.

## Before opening a pull request

1. Open an issue describing the research workflow or failure mode.
2. State whether the change affects durable artifact schemas.
3. Add tests for normal, malformed, and tampered inputs.
4. Update methodology and schema documentation when semantics change.
5. Keep synthetic fixtures clearly labelled and free of proprietary laboratory data.

## Local checks

```bash
python -m unittest discover -s tests -v
ruff check src tests scripts
ruff format --check src tests scripts
python -m compileall -q src tests scripts
python scripts/build_demo.py --check
python scripts/check_repository.py
```

Changes to ELN export should also be exercised with an installed wheel and the external RO-Crate
validators documented in [ELN interoperability](docs/ELN_INTEROPERABILITY.md). Keep those tools as
development-only dependencies so the offline runtime remains dependency-free.

## Design rules

- Raw evidence is never silently modified.
- Derived artifacts name their source run and raw files.
- Audit rules return stable machine-readable codes.
- Cryptographic claims are limited to byte identity.
- Core runtime dependencies remain at zero unless a strong, documented reason changes that policy.
- Public demonstrations never imply that synthetic instruments or measurements are real.

By contributing, you agree that your work is released under the MIT License.
