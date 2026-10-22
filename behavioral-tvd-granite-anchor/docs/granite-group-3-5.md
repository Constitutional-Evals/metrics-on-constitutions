# Authorized Granite group 3–5: stopped during Batch 3

The investigator authorized exactly Batches 3, 4 and 5 sequentially, conditional
on complete, validated, backed-up predecessors and no review-requiring errors.
The code base began at 6348860. Run ID:
`03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`.

The initial zero-request audit checked the authoritative ledger, operational
manifest, all frozen hashes, all previously valid rows, curated raw evidence and
attempt history, including six adaptive resume canaries. It confirmed 3,840
primary +160 baseline +66 canary valid records and $0.206581896 conservative
spending under the original $10 cap. A consistent before-stage backup was made.
All 63 automated tests passed. Authorizations and zero-request schedule checks
were recorded for the three stages; each retains $1 stage cap, 2,000 physical
primary attempts including retries, concurrency three and the frozen settings.

Batch 3 stopped on one HTTP200 error envelope whose internal code was 504. The
frozen identity validator classified absent model/provider metadata as an identity
failure. No actual model change is established. It recorded the failed attempt
and full conservative charge, left its evaluation invalid/missing, and refused
automatic continuation. No retry, manual settlement/reclassification, Batch 4,
Batch 5 or later inference was performed after the stop. All other Batch 3
responses were valid with both answer logs; all 18 canaries matched exactly.

## Offline verification and analysis

`audit_granite_group.py` extends the existing read-only audit to cover separately
identified adaptive canaries. Its postcheck found all 4,070 pre-existing attempts,
all previous checkpoint rows and 458 tracked files unchanged. The scientific
sources and manifest are unchanged; only new offline tooling and reports were
added, and the current progress page was updated after the postcheck.

`report_granite_stopped_group.py` independently recomputes exp(logp), binary mass,
conditional probabilities and swapped semantic orientation directly from actual
ASCII 0/1 token logs for all 1,517 valid Batch 3 responses. It checks actual
request/prompt hashes against the frozen schedule. Missing probabilities remain
blank in the 24×20 partial matrices. The full Batch 3 distances are unavailable.
A separately labeled 14-scenario complete-case subset has scalar-verified A/B/C
normalized and summed matrices, with no claim that it replaces the scheduled
20-scenario batch. No probability or distance is imputed.

`analyze_granite_cumulative.py` reconstructs the first 40 completed scenarios from
individual records, recomputes A/B/C over the pooled vectors, and independently
checks each result with scalar summation. A is distance between four-condition
mean vectors; B averages condition-specific distances; C uses canonical prompts;
normalized distances divide by the actual included N. Prefix evolution and fixed-
seed subsampling are descriptive and preliminary. No first-100 result is claimed.

From 20 to 40 scenarios, mean normalized A/B/C changed from
0.06955/0.08935/0.10390 to 0.07591/0.09383/0.10340. Pair-distance rank correlations
between prefixes are 0.851/0.896/0.893. Only 6/24 nearest neighbors for A, 11/24 for
B and 9/24 for C remain the same (ID tie-breaks apply). These provisional rankings
are sensitive to scenario inclusion and must not be interpreted as final.
The mean A-distance rank correlation for 20-of-40 subsamples is 0.868, with
5th–95th percentile 0.799–0.911 over 100 seeded draws. The retained 0.125 log-odds
quantization remains a scientific limitation.

## Recovery and dispatch boundary

Do not directly launch Batch 4 or 5 merely because their conditional authorization
files exist: the group-stop condition blocks them. Review the preserved timeout
response and authorize a narrowly audited recovery of Utilitarianism × 2599 ×
labels_swapped before resuming Batch 3 missing tasks. Preserve its original failed
attempt and conservative charge, all 1,517 valid rows and every earlier record.
Ordinary frozen resume rejects the invalid checkpoint. A future recovery must
explicitly address this status; changing frozen dispatcher error handling would
require reviewed version handling. Six fresh resume canaries are required by
the existing protocol. Complete and independently verify/back up Batch 3 before
any further stage. No larger new group is recommended until this path is reviewed.

The authoritative SQLite and raw evidence have separate backups outside Git;
backup hashes are in the Batch 3 preservation manifest. Git contains curated
raw responses/attempt records, not the authoritative spending database or secrets.
The group-stop accounting exists in both operational and curated storage.
See `results/granite-exploratory/PROGRESS.md` for costs, counts and performance.
