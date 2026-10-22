# Research snapshot: migration and portability

This directory is a proposed public, self-contained research snapshot from
`vstumuluri/test-metric-constitution`, branch `work`, source commit
`b7726db93c756d76df80307351f998617e340914`. The private Git history is not imported,
and this is not a submodule. The investigator approved this snapshot for a public migration pull request;
merging remains subject to maintainer review.

The immutable scientific run ID remains
`03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`.
All 41 scientific input/source hashes in the frozen manifest are unchanged.
No original probability, distance matrix, figure, scientific script, or manifest
is rewritten. Official results cover 220 scenarios; the 239-scenario complete-case
supplement excludes scenario 29912. Batch 12 stays stopped and incomplete.

The repeatable private-to-public synchronization workflow is documented in
[Publishing scientific snapshots](../PUBLISHING.md).

## Installation and working directory

The original `pyproject.toml` and `src/constitution_distance/` are retained.
Editable installation is supported from the monorepo root:

```bash
pip install -e ./behavioral-tvd-granite-anchor
```

Or from this directory:

```bash
pip install -e .
```

The base package has no mandatory third-party dependencies. Offline analysis
additionally needs NumPy 2.2.5, SciPy 1.15.3, and Matplotlib 3.10.3. These can be
installed in an ordinary Python environment without model weights or GPU packages:

```bash
pip install numpy==2.2.5 scipy==1.15.3 matplotlib==3.10.3
```

Run the README's offline reconstruction and test commands **from this subproject
directory**. Their existing project-relative paths then remain valid. If your
virtual environment is elsewhere, substitute its Python for `.venv/bin/python`.
Reproduction should write outside the snapshot (the README uses `/tmp`), preserving
published results. The new monorepo root is not the scientific project root.

## Offline verification

Migration checks passed all 86 local fixture/mock tests in the existing scientific
environment. A fresh editable installation with only the analysis dependencies
passed 81 tests, skipping five optional Torch tests; no model weights or GPU
packages were installed. Both environments reconstructed the official
220- and supplementary 239-scenario calculations from archived request/response
logs. All five official probability CSVs and six distance CSVs matched exactly.
All 33 supplementary/reconstructed CSVs and six figure files reproduced byte for
byte. No API inference, model download, or ledger access was used.

The retained analysis requires the frozen task-plan archive, scientific manifest,
constitution/scenario files, and `batch-0001` through `batch-0012` response archives.
These dependencies are included unchanged. No missing probability was imputed.

## Historical scripts and internal path strings

Only the documented offline reconstruction and tests were exercised. This is not
a claim that every historical execution/recovery script is portable. Many older
helpers embed `/workspace/work/` or `/workspace/backups/` paths, and data-analysis
scripts commonly assume this directory is their working directory. Those original
strings are retained as historical evidence, not silently rewritten. In particular,
older pilot-analysis, provider-study, backup, preservation, resumption, and timeout
recovery helpers require their original working artifacts and must not be used as
public-snapshot reproduction commands. The source snapshot's `/workspace` paths
are descriptive; they are not available operational state in a public checkout.

Archived documentation is not a promise that its old working directories are
included. Specifically:

- `docs/granite-final-pilot.md` replay helpers (including
  `analyze_final_granite_pilot.py` and `check_final_granite_numerics.py`) expect
  original `/workspace/work/granite-final-pilot/` artifacts; the raw published
  pilot evidence is preserved, but these helpers are not relocated or rerun.
- Historical Llama/provider-analysis helpers expect their original controlled
  pilot and diagnostic working directories. Their published evidence remains
  included; the new snapshot does not reproduce those private runtime directories.
- `docs/granite-exploratory-resumption.md` and backup/recovery instructions require
  the authoritative private ledger and approvals. Those dependencies are
  deliberately unavailable in this research snapshot.
- `docs/local-reference.md` describes an abandoned local-model path that requires
  separately downloaded weights and optional dependencies; it is not needed for
  current Granite result reproduction and was not executed.

For the supported portable path, use the current subproject README's archived-log
reconstruction and mock tests. This explicitly replaces reliance on those older
working-directory replay commands for the current 220/239 results.

Do not run dispatcher, recovery, or authorization scripts to reconstruct figures.
The original authoritative SQLite ledger, backups, recovery state, and applicable
approvals remain solely in the original protected environment. This snapshot is
not an operational replacement or permission to resume inference.

## Deliberate exclusions and public review

The [provenance manifest](MIGRATION-PROVENANCE.json) inventories retained files and deliberate
exclusions. Excluded material consists of historical batch/spending authorizations,
storage/backup engineering records, and most ledger-recovery transactions or
full-checkpoint preflight dumps. Scientific request/response archives, failure
attempt histories, partial numerical exports, official/supplementary results,
relevant reports, and all code/tests remain retained. Two small Batch 12 recovery
summaries remain included to preserve existing progress-report links; they are
not databases. Private original files are neither deleted nor changed.

Historical reports and some immutable records contain generic internal absolute
paths, response/request IDs, usage/cost metadata, and references to private source
commits. Those are proposed for explicit investigator approval; identifiers and
paths are not asserted to be confidential credentials. Public upstream model-card
contact addresses are retained attribution. An automated pattern scan is not a
guarantee that no sensitive content could remain.

See [third-party notices](THIRD_PARTY_NOTICES.md) for dataset/anchor attribution and
the unresolved project-code license. No license for original code or provider
outputs is invented by this migration. The project owner should resolve intended
code licensing and review applicable output redistribution terms before publication.
