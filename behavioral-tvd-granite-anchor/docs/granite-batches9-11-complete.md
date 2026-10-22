# Granite exploratory Batches 9–11: completed and paused

All three authorized stages completed sequentially under immutable run
`03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`,
continuing base commit e96e277 and scientific protocol a8c1a66. Each predecessor
was independently verified, reconciled and restore-checked before its successor.
**No Batch 12 authorization or dispatch occurred.**

## Engineering

All eight prior batches initially matched their archived requests, evaluation
records and complete physical attempt histories. SQLite integrity, original $10
cap, frozen manifest/input/source hashes and operational identity passed. Initial
counts/spending matched the investigator's expectations exactly. The Batch 3
original failed-attempt fingerprint remains
`4b811e554e9bcb56eee750dedd4f52ea67b8dd85bc3bef9480143a24fbb65a84`.
Every subsequent pre/post audit preserved earlier evaluations and failed attempts.

Only offline analysis, validation, backup and documentation tooling changed:

- Full completion now separates scientific completeness from historical billing
  uncertainty. Settled unknown-cost failures are disclosed and retain full
  conservative charges; valid retries satisfy their logical evaluations.
  Reserved/inflight requests, missing/invalid science, missing canaries and
  under-accounted/unsettled unknown billing still block completion.
- CLI restrictions no longer stop cumulative/disjoint analysis at five/eight
  batches. Counts derive from the frozen schedule, including the final short batch.
- Verified compressed, content-addressed historical snapshots and exact-byte
  incremental checkpoints replace repeated full-size before/after backups.
  The complete restore procedure and same-volume limitation are documented in
  [backup and export engineering](granite-backup-and-export.md).
- Nine completion regressions and two backup/corruption tests join the original
  66: **77 tests pass**. Batch 1 and 8 probability/A/B/C CSVs were independently
  regenerated in scratch and all 11 per batch remain byte-identical.

No frozen scientific source, manifest hash, prompt, input, provider, parameter,
probability definition or task identity changed. The real incomplete full grid
was explicitly checked and still refuses full-completion export.

The volume is 33.77 GB. Initially 19.03 GB was available. Seventeen full-size
historical snapshot names occupied 5.897 GB; ten unique lossless objects now
occupy 0.812 GB, reclaiming **5.084 GB**. Every original snapshot was actually
restored, byte-hashed, SQLite-integrity checked and compared across all tables
before retiring its redundant full copy. Latest Batch 11 recovery also matches
all authoritative tables, states, attempts, settings and accounting exactly.
After the group, approximately **23.43 GB** was available before final Git/review
archive overhead; the authoritative database was 882,737,152 bytes. Root working
files occupied 1.707 GB, and this experiment's backup tree 1.175 GB.

The pre-inference group bound allowed 1.05 GB persistent growth, 2.90 GB temporary
peak usage and a required 2 GB margin, leaving over 20 GB free at projected peak.
It passed. All successor stages rechecked free space. The end-of-experiment
*generous conservative bound* does not fit the current volume: repeat the gate
before future groups, and compact verified redundant evidence or obtain an
approved larger/off-volume location before it fails. No new storage service was
provisioned. Local backup directories share the working volume; GitHub preserves
curated evidence, not the authoritative ledger. This remains a disaster-recovery
limitation, not an off-volume ledger backup.

## New measurements

Each batch contains 20 consecutive frozen-schedule scenarios, 1,920 primary
measurements, 80 baselines and 30 scheduled canaries. All 6,090 new physical calls
were valid on their first attempt. No failed calls, retries, new uncertain billing
or additional resume canaries occurred.

| Batch | Confirmed and conservative cost | Active seconds | Valid responses/s |
|---|---:|---:|---:|
| 9 | $0.099491040 | 539.118 | 3.765 |
| 10 | $0.099380540 | 485.708 | 4.179 |
| 11 | $0.099414540 | 613.877 | 3.307 |
| Group | $0.298286120 | 1,638.703 | 3.716 |

Batch 11 had one 110.5-second response; it succeeded without a retry. Active group
inference totaled 27.31 minutes, excluding offline audits/analysis and task setup.
Every valid response reports the pinned Granite model and Cloudflare provider,
contains both genuine ASCII answer-token logs, and matches frozen request/prompt
hashes. All 90 new canaries match their probability, log-odds and raw-logprob
references exactly. Minimum binary answer mass was 0.998491, 0.998260 and 0.998790
in Batches 9, 10 and 11 respectively.

Independent scalar reconstruction checked every probability transformation, all
four condition matrices, their average, and A/B/C normalized and summed distances.
The largest batch distance difference was 4.45e-16. Range, completeness, symmetry,
zero diagonal, nonnegativity and A≤B passed. No imputation or sampled-answer
substitution was used. Batch exports and cumulative exports remain separate.

## Cumulative preliminary analysis: 220 scenarios

There are **21,120 primary**, **880 baseline**, **330 scheduled canary** and
**12 historical resume-canary** evaluations: **22,342 valid records** from
**22,350 physical attempts**. Historical eight failed attempts and four uncertain
billing outcomes remain intact. Confirmed response charges are **$1.094968516**;
conservative spending is **$1.104767812** of the original $10 cap. The difference
$0.009799296 retains four full unknown-billing reservations. No outstanding work
or reservations remain in the authorized stages.

The 24×220 semantic probability matrix was reconstructed from individual scenario
records; metrics were recomputed over pooled scenarios, not averaged batch matrices.

| Metric | Mean normalized pair distance | Mean summed L1 | Normalized range |
|---|---:|---:|---:|
| A: distance between four-condition averages | 0.069121160 | 15.206655212 | 0.039279–0.123530 |
| B: average condition-specific distance | 0.084713945 | 18.637067809 | 0.050327–0.141745 |
| C: canonical-only distance | 0.082583371 | 18.168341576 | 0.038592–0.180345 |

From 200→220 scenarios, A pair-distance ranking Spearman correlation is 0.996458;
23/24 nearest neighbors remain unchanged. Mean absolute pair-distance change is
0.00116147 (maximum 0.00358485). The closest current A pair is Buddhism/Judaism;
the farthest is Taoism/Utilitarianism. These are descriptive preliminary rankings.

Disjoint first-110 versus next-110 scenarios give Spearman **0.799986**, mean
absolute normalized distance difference **0.00711080** (maximum **0.0409231**),
and **13/24** matching nearest neighbors. Nested prefixes share data, so their
higher apparent stability does not establish population-level stability. Random
110-of-220 subsampling (100 draws, frozen seed 20261022) gives mean Spearman
0.960994, 5th–95th percentiles 0.948328–0.972222; 55-of-220 gives 0.899845.

Mean absolute label effect remains 0.290042, action-line order effect 0.169579,
and mean four-condition probability range 0.478453. Mean absolute shift from the
counterbalanced no-constitution baseline is 0.104741; signed mean shift +0.0267034.
All 22,342 valid records retain log odds on the observed 0.125 grid (tolerance
1e-5): repeatability is not arbitrary numerical precision. Counterbalancing is
retained exactly; it does not eliminate all prompt sensitivity. Interpret these
as Granite-conditioned behavioral distances, not established philosophical distances.

## Remaining work

**56 batches / 1,116 scenarios** remain: 107,136 primary evaluations, 4,464
baselines and 1,680 scheduled canaries (113,280 tasks, plus any legitimate retries
or restart QC). Aggregate active inference is 6,110.155 seconds (101.84 minutes),
3.65654 valid responses/s. Estimated remaining active inference is **8.61 hours**,
with **$5.60** remaining cost and **$6.71** projected total. Allow roughly ±20%
variation and additional setup/approval delays; storage gates may require action.
No estimate authorizes another batch. A next group of three remains a reasonable
operational size, conditional on explicit investigator authorization and the same
integrity, budget, storage and sequential completion gates.

Machine-readable evidence: `engineering-0009-0011/`, each `batch-0009/` through
`batch-0011/`, `cumulative-through-0011/`, and `progress-after-batch-0011.json`
under `results/granite-exploratory/`. Recovery sidecars and archive checksums are
curated; authoritative SQLite and compressed ledger objects remain outside Git.
