# Competitive landscape

This document explains the project boundary. It is not a claim that BenchLineage invented
electronic laboratory records or scientific provenance.

## Adjacent systems

### eLabFTW

[eLabFTW](https://www.elabftw.net/) is a mature open-source ELN with experiment and protocol
records, inventory, equipment scheduling, collaboration, permissions, export, and institutional
deployment. It is a much broader laboratory-management product than BenchLineage.

### openBIS

[openBIS ELN-LIMS](https://openbis.ch/) combines research-data management, electronic laboratory
notebooks, inventories, and data workflows for institutional environments. It is appropriate when
central infrastructure and multi-user governance are requirements.

### datalab

[datalab](https://docs.datalab-org.io/) captures experimental data and metadata as connected
research objects, with particular strength in materials-characterization workflows and instrument
integration.

### PASTA-ELN

[PASTA-ELN](https://github.com/PASTA-ELN/desktop) is a local-first and materials-science-oriented
electronic lab notebook with structured metadata and heterogeneous experimental data.

### PyTestLab

[PyTestLab](https://pytestlab.org/) focuses on modern laboratory test-and-measurement automation,
instrument abstractions, declarative benches, and reproducible execution. BenchLineage deliberately
does not compete as an instrument-driver framework.

### MLflow and DVC

[MLflow](https://mlflow.org/) tracks machine-learning experiments, models, and metrics.
[DVC](https://dvc.org/) versions data pipelines and large artifacts. Both can complement
BenchLineage, but neither makes EE instrument calibration and measurement uncertainty the center of
its core record.

## The chosen gap

BenchLineage targets an individual EE researcher who currently has:

- raw CSV files from several instruments;
- plots produced by scripts or proprietary applications;
- calibration certificates stored elsewhere;
- conditions and deviations written in a notebook or filename;
- no desire to administer a laboratory server;
- a need to publish a reviewable evidence bundle.

Its differentiators are the combination of:

- zero-dependency, offline operation;
- instrument identity and calibration-window audit;
- explicit uncertainty components;
- plain JSON/CSV artifacts suited to Git review;
- byte-level sealing with a narrow, honest integrity claim;
- a single-file public report;
- a deterministic publication ZIP with a verifier and plain SHA-256 manifest;
- a deterministic ELN Consortium exchange archive for handing the same sealed evidence to an
  existing electronic lab notebook;
- no attempt to own acquisition or analysis.

No individual feature is novel. The contribution is a small interoperable
workflow whose failure modes are easier to inspect than a general ELN
deployment. It should be compared on setup cost, evidence completeness,
long-term readability, and independent verification—not on feature count.

## When not to use BenchLineage

Choose a mature ELN or LIMS when you need access control, electronic signatures, sample inventory,
equipment booking, regulatory validation, institutional backups, or rich collaborative editing.

Choose an automation framework when you need instrument drivers, experiment scheduling, real-time
feedback, or hardware-in-the-loop execution.

Choose a data-versioning platform when large binary artifacts and distributed storage are the
primary problem.

BenchLineage can provide a portable evidence layer around those systems, but should not pretend to
replace them.

The `.eln` exporter is therefore a bridge, not a claim that BenchLineage has become an ELN. It
preserves the original workspace files and maps their relationships into RO-Crate so another tool
can inspect or import them. Product-specific round-trip fidelity still needs testing with each
target importer.
