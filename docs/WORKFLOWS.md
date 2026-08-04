# Workflows

## Workflow A: quick personal bench record

Use this when one researcher needs stronger evidence than a spreadsheet folder but does not need a
multi-user ELN.

1. Initialize one workspace per coherent project.
2. Register instruments when they first appear.
3. Record calibration references before the first run.
4. Create a study for the research question, not for every acquisition.
5. Copy or export raw files under `data/raw/`.
6. Add one run per materially distinct acquisition condition.
7. Generate derived analyses.
8. Audit after every acquisition session.
9. Seal at a milestone such as a group meeting, manuscript figure, or dataset release.

## Workflow B: Git-backed collaboration

BenchLineage files are mergeable, but it is not a concurrency server.

1. Agree on identifier prefixes by researcher or work package.
2. Keep raw binary data in an appropriate large-file store when needed.
3. Review study, run, calibration, and analysis JSON alongside code changes.
4. Run audit in CI.
5. Seal only after merging the evidence intended for a milestone.
6. Protect tags or release branches using repository rules.

Do not treat Git commit authorship as laboratory operator identity unless your process explicitly
binds them.

## Workflow C: manuscript evidence bundle

1. Create a clean export containing only publishable evidence.
2. Replace private paths or notes through an explicit redaction process.
3. Audit the export.
4. Seal the export.
5. Generate the report after sealing.
6. Run `benchlineage bundle <workspace> --output <evidence.zip>`.
7. Verify the finished archive with `benchlineage verify-bundle <evidence.zip>`.
8. Archive the bundle and analysis environment together.
9. Publish the root digest in the README, data repository, or supplementary methods.

Removing sensitive content necessarily produces a different evidence root. Keep the private
original and public redacted root distinct.

## Workflow D: external analysis

BenchLineage does not require built-in analysis:

1. Use MATLAB, Python, Julia, R, SPICE, or another validated tool.
2. Write a JSON artifact under `analysis/`.
3. Include `schema`, `run_id`, `study_id`, tool identity, source paths, parameters, and outputs.
4. Add an extension schema when the structure is intended for reuse.
5. Audit references and seal the workspace.

The report generator displays built-in analysis kinds. External tools can generate their own
self-contained report or contribute a renderer.

## Backup guidance

A single local workspace is not a backup. Follow the 3-2-1 principle when evidence matters:
maintain at least three copies, on two media types, with one copy off-site. Verify restoration, not
only synchronization.
