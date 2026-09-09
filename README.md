<p align="center">
  <img src="https://raw.githubusercontent.com/CAOShurong/benchlineage/main/docs/assets/hero.svg" alt="BenchLineage worked example: measure a cutoff frequency, link its equipment and files, then verify the record later" width="100%">
</p>

BenchLineage turns an ordinary project directory into a verifiable chain from **research
intent** to **instrument identity**, **calibration coverage**, **raw measurement**, **derived
analysis**, **uncertainty budget**, and **published report**.

It does not replace a full electronic laboratory notebook, instrument-control framework, or
institutional data repository. It focuses on a smaller failure mode that is especially common in
electrical-engineering research: six months after a measurement, the plot survives but the exact
instrument, calibration window, run conditions, raw file, and analysis lineage do not.

The default workflow is offline. There is no account, server, database, API key, telemetry, or
runtime dependency.

When the record needs to leave the project directory, BenchLineage can produce either its strict
byte-verifiable evidence bundle or an interoperable `.eln` archive for electronic laboratory
notebook exchange.

<p align="center">
  <a href="https://github.com/CAOShurong/benchlineage/actions/workflows/ci.yml"><img src="https://github.com/CAOShurong/benchlineage/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/benchlineage/"><img src="https://img.shields.io/pypi/v/benchlineage?color=2b6f6b" alt="PyPI"></a>
  <a href="https://pypi.org/project/benchlineage/"><img src="https://img.shields.io/pypi/dm/benchlineage?color=2b6f6b&logo=pypi&logoColor=white" alt="Downloads"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11%2B-20384a" alt="Python 3.11+"></a>
  <a href="https://caoshurong.github.io/benchlineage/"><img src="https://img.shields.io/badge/docs-live%20demo-28766d" alt="Live Demo"></a>
  <a href="https://github.com/CAOShurong/benchlineage/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-a47a36" alt="License: MIT"></a>
</p>

[Live demonstration](https://caoshurong.github.io/benchlineage/)
· [Synthetic report](https://caoshurong.github.io/benchlineage/demo/demo-report.html)
· [PyPI package](https://pypi.org/project/benchlineage/)
· [Methodology](https://github.com/CAOShurong/benchlineage/blob/main/docs/METHODOLOGY.md)
· [CI](https://github.com/CAOShurong/benchlineage/actions/workflows/ci.yml)
· Python 3.11+ · MIT · zero runtime dependencies

> [!IMPORTANT]
> BenchLineage is a research recordkeeping tool, not a calibration authority, regulatory
> compliance system, or safety certification. A cryptographic digest shows whether recorded bytes
> changed; it cannot prove that a physical measurement was performed correctly or honestly.

## See it before installing

- [Project site](https://caoshurong.github.io/benchlineage/)
- [Synthetic interactive report](https://caoshurong.github.io/benchlineage/demo/demo-report.html)
- [Example workspace](https://github.com/CAOShurong/benchlineage/tree/main/demo/workspace)
- [Methodology](https://github.com/CAOShurong/benchlineage/blob/main/docs/METHODOLOGY.md)
- [Competitive landscape](https://github.com/CAOShurong/benchlineage/blob/main/docs/COMPETITIVE_LANDSCAPE.md)

Every instrument name, serial number, certificate, and measurement in the public demonstration is
synthetic. The demo illustrates the evidence model; it makes no claim about physical hardware.

## The evidence chain

<p align="center">
  <img src="https://raw.githubusercontent.com/CAOShurong/benchlineage/main/docs/assets/workflow.svg" alt="Six plain-language stages: plan the experiment, identify equipment, save raw data, compute the result, check links, and share one bundle" width="100%">
</p>

<p align="center"><sub>Every stage writes an inspectable file; the final bundle keeps those files together.</sub></p>

| Layer | Durable artifact | Question it answers |
|---|---|---|
| Workspace | `benchlineage.json` | Who owns this record and which format does it use? |
| Study | `studies/*.json` | Why was the experiment run and what was planned? |
| Instrument | `instruments/*.json` | Which physical device produced the observation? |
| Calibration | `calibrations/*.json` | Was traceability recorded for the run date? |
| Run | `runs/*.json` | Who did what, when, under which conditions? |
| Raw data | `data/raw/*` | What was actually observed? |
| Analysis | `analysis/*.json` | Which deterministic derivation produced the result? |
| Seal | `seals/*.json` | Do the current bytes match the published evidence root? |
| Report | `reports/*.html` | Can another person inspect the chain without this package? |

### A result is more than a number

The figure below uses one fictional RC-filter result to show the five kinds of context that travel
with it. This is the smallest useful mental model for BenchLineage: the reported value sits in the
middle, and every surrounding statement has a recorded source.

<p align="center">
  <img src="https://raw.githubusercontent.com/CAOShurong/benchlineage/main/docs/assets/result-record.svg" alt="A fictional cutoff-frequency result linked to its objective, raw observations, equipment, analysis method, uncertainty budget, and integrity record" width="100%">
</p>

<p align="center"><sub>Integrity checks answer whether recorded files changed; they do not certify whether the experiment was scientifically correct.</sub></p>

## Try it without installing

Any command runs straight off PyPI through [uv](https://docs.astral.sh/uv/) or pipx — no
environment to create, nothing added to your Python installation:

```bash
uvx benchlineage demo my-bench --seed 20260804
uvx benchlineage verify my-bench
```

The first command builds a complete synthetic workspace — instruments, calibrations, an RC
low-pass sweep followed by a deliberate resistor substitution, derived analyses and uncertainty
budgets — seals it, and writes `my-bench/reports/demo-report.html`. The second re-hashes every
evidence file and checks the inventory against the recorded root digest; the expected result is
`"valid": true`. Swap `demo` for `init` whenever you want to start recording real work.

## Install

Install from PyPI:

```bash
python -m pip install benchlineage
benchlineage --version
```

Or don't install at all: `uvx benchlineage <command>` (and `pipx run benchlineage <command>`)
runs each command from a cached, isolated environment — see
[the one-minute demonstration](#try-it-without-installing).

For an isolated one-off demonstration with [pipx](https://pipx.pypa.io/):

```bash
pipx run benchlineage demo my-bench --seed 20260804
```

PyPI distributions are published from the tagged GitHub workflow with a short-lived OIDC
credential and a public provenance attestation. Each GitHub Release also carries the same wheel,
source archive, and a SHA-256 checksum file.

For development:

```bash
git clone https://github.com/CAOShurong/benchlineage.git
cd benchlineage
python -m pip install -e .
```

## Try the complete demonstration

```bash

benchlineage demo my-bench --seed 20260804
benchlineage audit my-bench
benchlineage verify my-bench
```

Open `my-bench/reports/demo-report.html`. It is a single HTML file with embedded CSS, JavaScript,
charts, audit evidence, and source records. It uses no CDN and sends no network requests.

The generated demonstration includes:

- a 41-point RC low-pass sweep with a baseline component value;
- a second sweep after a deliberate resistor substitution;
- a ten-point buck-converter load and efficiency sweep;
- three synthetic instruments and three synthetic calibration records;
- three derived analyses and three uncertainty budgets;
- a SHA-256 evidence inventory and root digest.

## Start a real workspace

The command blocks in this section use the POSIX-shell `\` line continuation. In PowerShell,
replace each trailing `\` with a backtick (`` ` ``), or put the command on one line. Use a JSON
file for structured arguments as shown below; this avoids shell-dependent quote handling.

```bash
benchlineage init thesis-bench \
  --title "Wide-bandgap converter characterization" \
  --owner "Your Name" \
  --owner-email "you@example.org" \
  --owner-given-name "Your" \
  --owner-family-name "Name" \
  --data-license-url "https://spdx.org/licenses/CC-BY-4.0.html" \
  --data-license-name "CC BY 4.0" \
  --data-license-description "Experimental data released under CC BY 4.0."

benchlineage add-instrument thesis-bench \
  --id scope-01 \
  --kind oscilloscope \
  --manufacturer Tektronix \
  --model MSO58 \
  --serial C012345

benchlineage add-calibration thesis-bench \
  --id scope-01-2026 \
  --instrument scope-01 \
  --performed-at 2026-01-18T09:00:00+08:00 \
  --due-at 2027-01-18T09:00:00+08:00 \
  --certificate CAL-2026-001 \
  --standard-uncertainty 0.0025 \
  --unit V

benchlineage create-study thesis-bench \
  --id gate-loop \
  --title "Gate-loop ringing characterization" \
  --objective "Measure overshoot across three gate resistances." \
  --hypothesis "Higher gate resistance reduces overshoot at the cost of switching loss." \
  --protocol "Record 200 switching events per resistor at fixed bus voltage and load." \
  --tag power-electronics \
  --tag switching
```

Raw evidence is intentionally added as an ordinary file. This keeps acquisition independent from
BenchLineage and avoids locking a lab into one driver ecosystem:

```text
thesis-bench/data/raw/gate-loop-rg2p2.csv
```

Save the run conditions as `conditions.json`:

```json
{
  "bus_voltage_v": 400,
  "load_current_a": 20,
  "gate_resistance_ohm": 2.2
}
```

Record the run. The `--conditions` option accepts either a JSON file path or inline JSON; the file
form works unchanged in POSIX shells and PowerShell:

```bash
benchlineage add-run thesis-bench \
  --id gate-loop-rg2p2-001 \
  --study gate-loop \
  --operator "Your Name" \
  --started-at 2026-08-04T14:00:00+08:00 \
  --instrument scope-01 \
  --raw-file data/raw/gate-loop-rg2p2.csv \
  --conditions conditions.json
```

Then analyze, audit, seal, and report:

```bash
benchlineage analyze thesis-bench \
  --run gate-loop-rg2p2-001 \
  --kind column_summary

benchlineage audit thesis-bench --output audit.json
benchlineage seal thesis-bench --label "Preprint figure 4 evidence"
benchlineage verify thesis-bench

benchlineage report thesis-bench \
  --title "Gate-loop characterization evidence" \
  --note "Dataset frozen before manuscript submission." \
  --output gate-loop-report.html
```

## Publish a reviewable evidence bundle

After audit and sealing, create one deterministic ZIP for a collaborator,
reviewer, or data repository:

```bash
benchlineage bundle thesis-bench --output thesis-bench-evidence.zip
benchlineage verify-bundle thesis-bench-evidence.zip
```

The bundle includes the workspace records, raw files, reports, latest seal, a
human-readable README, and `BUNDLE-MANIFEST.json`. The manifest lists every
included path, byte length, and SHA-256 digest. Rebuilding from unchanged bytes
produces the same ZIP bytes.

The verifier refuses unsafe archive paths and reports duplicate, missing,
added, or changed members without extracting the bundle. This is an integrity
check, not a digital signature or a claim that the experiment was valid.

## Move the record into an electronic lab notebook

The [ELN Consortium format](https://the.elnconsortium.org/specification/) is a ZIP-packaged
RO-Crate exchange format implemented by products including eLabFTW, Kadi4Mat, PASTA, RSpace, and
SampleDB. Export the same sealed workspace without copying records into a vendor-specific form by
hand:

```bash
benchlineage export-eln thesis-bench --output thesis-bench.eln
benchlineage verify-eln thesis-bench.eln
```

The exporter preserves every original workspace file and adds flattened JSON-LD that describes
the workspace owner, studies, instruments, calibrations, experimental runs, raw files, and
analyses. Instruments become RO-Crate `IndividualProduct` entities; runs and analyses become
`CreateAction` provenance. Each local file carries its byte length and SHA-256 digest.

When `init` receives a data-license URL, `export-eln` links the root Dataset to a RO-Crate
`CreativeWork` license entity with its declared name and description. The URL must be an absolute
HTTP(S) URL without embedded credentials. BenchLineage does not infer a license: existing or new
workspaces that omit the declaration retain an explicit contact-the-author warning. The public
synthetic demo declares the repository's MIT license; that declaration does not license user data.

The Dataset identifier carries the latest BenchLineage evidence root. As with a native seal, that
root excludes generated reports and seal records; the ELN's per-file SHA-256 entries still cover
every member of the finished archive.

`verify-eln` reads the archive without extracting it. It rejects unsafe or duplicate paths,
multiple archive roots, malformed graph references, missing or unlisted payloads, and byte or
digest mismatches. Standard `ro-crate-preview.html`, `ro-crate-preview_files/`, and ELN metadata
signature members are reported as `unverified_ancillary` instead of evidence: their presence is
allowed, but BenchLineage does not claim their bytes or signature trust were verified unless the
metadata separately declares them as hashed File entities. Exports are deterministic for the same
sealed bytes and output filename.

BenchLineage targets the ELN Consortium's currently exercised RO-Crate 1.1 compatibility surface,
which maximizes compatibility with existing importers. It does not claim that every target ELN
will preserve every BenchLineage-specific field in its own interface; the original JSON, CSV,
reports, and seals remain in the archive even when an importer ignores richer metadata. The exact
mapping and independent validation evidence are documented in
[ELN interoperability](https://github.com/CAOShurong/benchlineage/blob/main/docs/ELN_INTEROPERABILITY.md).
BenchLineage does not convert a third-party `.eln` archive into its stricter workspace schema;
`verify-eln` is a read-only archive check, not an import command.

## Built-in analyses

BenchLineage deliberately implements a small, inspectable analysis core:

| Analysis | Detected columns | Main outputs |
|---|---|---|
| Frequency response | `frequency_hz`, `vin_v`, `vout_v`, optional `phase_deg` | gain, dB curve, passband estimate, interpolated −3 dB cutoff |
| Power efficiency | `vin_v`, `iin_a`, `vout_v`, `iout_a`, optional `load_ohm` | input/output power, loss, efficiency, peak operating point |
| Linear calibration | `reference`, `observed` | slope, intercept, R², RMSE, error summary |
| Column summary | any all-numeric CSV | count, mean, median, extrema, standard deviation, standard error |

These are reference implementations, not an attempt to replace NumPy, SciPy, SPICE, MATLAB, or
domain-specific analysis. The JSON analysis artifacts are designed so more specialized tools can
write compatible results.

## Uncertainty budgets

An analysis can include Type A or Type B components:

```json
[
  {
    "name": "vertical accuracy",
    "limit": 0.005,
    "distribution": "rectangular",
    "source": "certificate CAL-2026-001"
  },
  {
    "name": "repeatability",
    "standard_uncertainty": 0.0016,
    "distribution": "normal",
    "source": "twenty repeated acquisitions"
  }
]
```

```bash
benchlineage analyze thesis-bench \
  --run gate-loop-rg2p2-001 \
  --uncertainty uncertainty.json \
  --coverage-factor 2
```

The engine converts stated limits for normal, rectangular, and triangular distributions into
standard uncertainties, applies sensitivity coefficients, combines independent contributions by
root-sum-square, and reports component variance shares. See
[Uncertainty model](https://github.com/CAOShurong/benchlineage/blob/main/docs/UNCERTAINTY.md) for assumptions and limitations.

## Auditing and sealing are different

`benchlineage audit` checks semantic relationships:

- referenced study, instrument, raw-data, and analysis records exist;
- calibration dates cover each run date when possible;
- raw paths remain inside the workspace;
- unreferenced raw files are reported;
- the latest seal still matches the evidence.

`benchlineage seal` checks byte identity. It records the SHA-256 digest and byte length of each
evidence file, then hashes the ordered inventory into one root digest. Reports and previous seals
are excluded so presentation can be regenerated without changing the recorded evidence.

Compare two recorded states without manually reading their inventories:

```bash
benchlineage diff-seals \
  thesis-bench/seals/seal-before.json \
  thesis-bench/seals/seal-after.json
```

The command returns machine-readable `added`, `removed`, and `changed` path lists plus both labels,
timestamps, and root digests. It exits with status 0 only when the roots match, so it can gate a
handoff or publication script.

A passing seal does **not** prove scientific truth. It proves only that the inventoried bytes match
the declared root.

## Why plain files?

Large ELN and LIMS platforms solve collaboration, permissions, inventory, scheduling, and
institutional deployment. BenchLineage instead optimizes for:

- one researcher or a small team;
- offline operation on Windows, macOS, or Linux;
- Git-friendly review and long-term readability;
- instrument-agnostic ingestion;
- explicit, deterministic audit rules;
- a migration path rather than another data silo.

All core records are readable JSON and CSV. If BenchLineage disappears, the evidence remains
usable.

## Repository map

```text
src/benchlineage/       CLI, analysis, audit, report, sealing, and bundle engine
schemas/                JSON Schema contracts for durable artifacts
demo/workspace/         committed synthetic example
site/                   public project site and generated report
docs/                   methodology, workflows, comparison, and design notes
tests/                  unit, integration, CLI, tamper, and report tests
scripts/                reproducible demo and repository checks
```

## Project boundaries

BenchLineage does not currently:

- control instruments or promise SCPI-driver compatibility;
- sign records with a trusted timestamping authority;
- provide multi-user permissions or electronic signatures;
- store secrets safely;
- validate laboratory safety or regulatory compliance;
- infer uncertainty models automatically;
- replace raw binary formats with CSV;
- guarantee FAIR compliance merely because metadata fields exist.

Those boundaries are intentional and documented in the
[roadmap](https://github.com/CAOShurong/benchlineage/blob/main/ROADMAP.md).

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
ruff check src tests scripts
ruff format --check src tests scripts
python -m compileall -q src tests scripts
python scripts/build_demo.py --check
python scripts/check_repository.py
```

The package targets Python 3.11 and newer and has zero runtime dependencies.

## Responsible citation

If BenchLineage contributes to a published evidence workflow, cite the software version and the
root digest of the sealed workspace. A software citation file is provided in
[`CITATION.cff`](https://github.com/CAOShurong/benchlineage/blob/main/CITATION.cff).

## License

[MIT](https://github.com/CAOShurong/benchlineage/blob/main/LICENSE). Contributions are welcome
under the same license. Questions and concrete laboratory workflows belong in
[Discussions](https://github.com/CAOShurong/benchlineage/discussions); reproducible defects and
inspectable analysis proposals belong in
[Issues](https://github.com/CAOShurong/benchlineage/issues).
