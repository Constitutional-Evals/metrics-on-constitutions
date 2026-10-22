# Publishing Granite scientific snapshots

The private repository remains authoritative for the **currently frozen Granite
experiment**: measurement collection, original Git history, ledger, backups, and
recovery state. The shared repository is the collaborative home for published
measurements, reproducible analyses, and future research. Publication is not
permission to resume inference. Batch 12 remains incomplete and paused.

The initial source snapshot is `vstumuluri/test-metric-constitution`, branch `work`,
commit `b7726db93c756d76df80307351f998617e340914`. The source and destination do not
share commit histories. Publication provenance uses source commit IDs and per-file
hashes, not Git merges between unrelated repositories.

## Policy and baseline

- [.publication/granite-policy.json](.publication/granite-policy.json) contains an
  **exact file allowlist**, the reviewed 96-file exclusion list, and frozen hashes.
  New files under `results/` are not automatically approved. Known operational
  paths, Git metadata, credentials, SQLite/database files, backup chains, model
  weights, and authorization files are hard-excluded.
- [.publication/granite-baseline.json](.publication/granite-baseline.json) records
  the last published private-source commit and each file's source blob/SHA-256
  and public destination SHA-256. Documentation overlays have different source
  and destination hashes by design. The initial baseline accompanies this PR;
  normally begin future synchronization from the approved, merged public baseline.
- [tools/sync_granite_snapshot.py](tools/sync_granite_snapshot.py) is a standard-library,
  local-only utility. It performs no inference, network requests, Git commits,
  pushes, or automatic merges. A local apply is not publication.

## Example: publish several newly completed batches

1. Separately authorize and complete measurement collection in the **private**
   repository. Validate its completed batches, preserve private checkpoints, and
   commit the scientific outputs there. This document grants no such authorization.
2. Fetch/review the shared repository and create a publication branch. Select an
   explicit private source ref (prefer the immutable commit SHA). Do not use an
   unreviewed moving `work` head accidentally.
3. Run a dry run from anywhere, using explicit top-level checkout paths:

   ```bash
   python /path/to/shared/tools/sync_granite_snapshot.py \
     --source /path/to/private --source-ref REVIEWED_SOURCE_SHA \
     --destination /path/to/shared --destination-ref HEAD \
     --manifest /tmp/granite-publication-plan.json
   ```

   The JSON reports additions/updates/removals, hashes, excluded paths, public
   conflicts, and unapproved new files. No files are copied. The last source
   snapshot comes from the committed public baseline, never an uncommitted edit.
4. For example, new Batch 13–15 archives and matrix files will be **unapproved**
   additions. Review each file and its dependencies, inspect raw archives for
   privacy/credentials, and add only approved exact filenames to the policy in a
   reviewed public-branch commit. Batch authorization and ledger material must
   remain private. Reject incidental newly generated files. Rerun the dry run.
5. Reproduce the new analyses offline in the subproject directory. Confirm the
   unchanged frozen run/inputs and all dependencies needed by the new reports.
   Review the JSON manifest and, only when approved, apply that exact plan locally:

   ```bash
   python /path/to/shared/tools/sync_granite_snapshot.py \
     --source /path/to/private --source-ref REVIEWED_SOURCE_SHA \
     --destination /path/to/shared --destination-ref HEAD \
     --manifest /tmp/granite-applied-plan.json \
     --apply --approved-manifest /tmp/granite-publication-plan.json
   ```

6. Inspect the local diff, rerun relevant offline checks, and review the changed
   baseline plus `.publication/granite-sync-history/<manifest-hash>.json`. Commit,
   push, and open a PR **only under explicit publication authorization**. Do not
   treat a locally prepared baseline as successfully published until its commit
   is actually shared/reviewed. The utility never performs those Git mutations.

The private checkout must contain the recorded baseline source commit (fetch it
first when using a shallow clone). The destination checkout must be clean and at
the requested ref. A different
source/destination commit, policy, baseline, file hash, or approval makes the old
manifest stale. Approved content is read from the selected private Git commit,
not dirty/untracked source files. The tool rechecks the entire plan before writing
and verifies copied hashes. Deletions are disabled; allowing any requires both
`--allow-deletions` in plan/apply and explicit review of the delete actions.

## Collaborative changes and conflicts

Any public change to a baseline-controlled file blocks synchronization, even if
the private copy has not changed. Changes on both sides are conflicts. Existing
public documentation overlays also block a differing private update. No
collaborator's work is silently overwritten, and public-only files outside the
allowlist are left alone.

Resolve conflicts in a separate reviewed commit: compare both contents and
scientific intent, preserve the approved public change, and, where appropriate,
port nonfrozen analysis/documentation improvements to a new private development
commit. **Never automatically merge public changes into frozen experimental
source.** Incompatible scientific changes require a separate experimental version.

For an intentional retained public overlay, maintain its public destination hash
and the actual old private source hash in the baseline; future private changes
remain conflicts. If both repositories deliberately converge to the same content,
after a reviewed baseline reconciliation the utility can record convergence
without overwriting bytes. Changing a baseline to acknowledge a conflict is a
manual review decision, not a way to bypass it. Rerun the plan after reconciliation.

Each apply prepares all changed bytes first, uses atomic replacement per file,
and writes the baseline last. It is not a multi-file filesystem transaction. If a
local apply fails/interruption leaves a partial diff, restore or reconcile that
unpublished Git working tree before retrying; never publish a partial apply.

## Validation and licensing

Run root publication tests with `python -m unittest discover -s tests -v`.
They use temporary repositories, including public edits, dual divergence, stale
approvals, exact allowlisting, exclusions, disguised database/credential archives,
source freezes, explicit deletion approval, overlays, and symlinks.

Scientific tests/reconstruction run separately **from the subproject directory**;
see [its README](behavioral-tvd-granite-anchor/README.md) and
[migration notes](behavioral-tvd-granite-anchor/MIGRATION.md). Older private runtime
replay helpers are preserved history, not portable public reconstruction commands.

No project code license is selected by this import. Maintainers should discuss
that decision in the migration PR. The empty destination supplied no license or
repository policy requiring a choice before an owner-authorized publication;
no accessible organization-wide `.github` policy repository was found. Existing
CC BY 4.0 anchor/dataset attribution is retained in
[third-party notices](behavioral-tvd-granite-anchor/THIRD_PARTY_NOTICES.md), alongside
archived model metadata/notices. No weights are distributed and no known
redistribution prohibition was identified for the approved artifacts. This is not
a claim to have inspected private organization policies or a blanket license for
model outputs. Exact applicable notices remain authoritative.
