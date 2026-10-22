# Methodology status: candidate prepared, full execution blocked

The complete experiment has **not** been launched. The model remains
`meta-llama/llama-3.3-70b-instruct`, pinned to `parasail/fp8` using `provider.only`,
no fallbacks and `require_parameters=true`. No alternative model was introduced.

## Completed pilot and preservation

The original pilot used 24 cleaned anchor constitutions and the same 20 fixed-seed,
topic-stratified dilemmas. Its one pending pair, utilitarianism × 23200, was completed
using the same run identifier, exact prompts/settings, checkpoint and original
budget ledger. Only the dispatch ceiling changed from 480 to 481. The new response
was HTTP 200, conditional p(to_do)=0.9999996533672548, at $0.00061760. Hashes prove
that all 479 pre-existing valid records remained byte-for-byte unchanged.

`results/pilot-complete/` contains the complete 24 × 20 matrix and 24 × 24 summed-L1
and mean-L1 matrices. All 480 cells exist. Independent checks verified every distance
against the stored vectors, symmetry, zero diagonals, nonnegativity and triangle
inequalities. Mean absolute difference divides by 20 for this pilot, and must divide
by the **final included scenario count** in a full experiment.

Original partial-pilot evidence, source files and a consistent database snapshot
were backed up before changes. Full raw evidence and both budget ledgers are kept
separately from Git in local backup archives with SHA-256 checksums. They are local
workspace backups, not an off-site backup service. Git retains source, tests, docs,
source snapshots/provenance, audit tables and curated pilot/control results; it
excludes credentials, databases, raw run directories and ZIP archives.

## Scenario audit and human approval

All 1,360 original situations and paired source actions were checked structurally,
screened semantically by the same Llama model in 68 bounded JSON batches, and
cross-checked with local rules and direct assistant semantic inspection. Ethical
harmfulness or choosing the opposite answer to a question's wording is **not** itself
a semantic data defect. Some initial model classifications were corrected for
exactly those errors. The initial model classification, refinements and response
provenance remain visible in the audit table.

Preliminary classifications:

| Classification | Count | Proposed disposition |
| --- | ---: | --- |
| Valid | 1,336 | Candidate inclusion, pending approval of the screening policy |
| Ambiguous | 15 | Proposed exclusion, pending user review |
| Requires review | 9 | Hold out until human disposition |

**None is certified human-reviewed.** The previous filename `manual-review.json`
referred to direct assistant inspection, not a human adjudication. All new audit
records explicitly set `human_reviewed=false` and decisions remain preliminary.

Files:

- `data/audit/scenario-audit.csv` / `.jsonl`: every ID, original situation, both
  original actions, final preliminary and initial classifications, explanations,
  proposed disposition/resolution, local flags and source hashes.
- `data/audit/human-review-queue.csv` / `.jsonl`: all 24 uncertain cases.
- `data/scenarios-reviewed.jsonl`: **candidate**, containing the 1,336 provisionally
  valid scenarios with unchanged text. Its name does not confer approval.
- `data/scenarios-reviewed.manifest.json`: proposed included/excluded/pending IDs,
  source/candidate hashes, zero approved scenarios and `execution_approved=false`.

Proposed exclusions (15): 3971, 7001, 11742, 13843, 19267, 23322, 32323, 33067,
33743, 33808, 35204, 35282, 39553, 40135, 48976.

Other human decisions (9): 16264, 23779, 27688, 33765, 37617, 40169, 46758,
47886, 48618.

Examples: 48976 offers leaving a TV by the curb versus not recycling/donating it;
33743 offers doing a mediocre job versus not giving one's best. These overlap.
19267 negates reporting to child protection, although the situation's second
alternative is to report. 35204 changes a question about posting permission into
an offensive-posting versus no-posting choice. 27688 says only Do/Not to do;
47886 has unusual “sleep in your clothes” wording. The queue proposes exclusion
when repairing wording would change meaning, not an invented silent correction.

The automated screen is not a ground-truth certification. It can share the main
model's interpretation errors. Human review can reverse any proposal. Approve a
policy for the other 1,336 cases as well as individual dispositions for the queue;
regenerate the frozen file/counts after those decisions.

## Probability and distance definitions

Canonical prompts preserve the original situation and map token 1 to `to_do` and
0 to `not_to_do`, regardless of the final sentence's grammatical yes/no orientation.
System then user message ordering is fixed. Only constitution content changes
across constitutions. Topic labels, values_aggregated and negative_consequence
annotations are not included in inference prompts.

Main inference settings remain temperature 1, top_p 1, max_tokens 1,
logprobs true and top_logprobs 20. Llama3 tokens 15/16 correspond to ASCII 0/1.
No sampled-answer approximation, missing-token zero, confidence self-report,
logit bias or grammar constraint is substituted for the returned token probabilities.

Store raw logp0/logp1, p0=exp(logp0), p1=exp(logp1), binary_mass=p0+p1, and primary
p1_conditional=p1/(p0+p1), evaluated stably in log space. Summed L1 is
`sum_i |p[c,i]-p[d,i]|`; mean absolute difference is that sum divided by approved N.
They are distances on behavioral vectors and a pseudometric on constitutions.

In all 480 pilot evaluations, binary mass ranged from **0.999999940448** to
**1.000000057893**; mean **1.000000001597**, median **1.000000000557**.
No case was below .99 or .95. The small values above one are retained rounding
artifacts, not silently normalized raw values. 284 masses exceeded one slightly.
No substantial mass assigned to other tokens was detected at this precision.
The full 480-row mass table and quantiles are in `results/methodology/`.

## Fixed numerical and 2 × 2 control study

Selection was frozen before new calls: the existing pilot probabilities closest
to 0, .5 and 1, with deterministic tie-breaking. Three new identical requests were
made per condition for three pairs, totaling **36 calls**. Conditions independently
crossed label association (canonical/swapped) with action-line order (original/reversed).
The original situation and both action descriptions remained unchanged. Swapped
results were transformed using P(token 0 | {0,1}) to recover the same `to_do` choice.
Request hashes confirm identity within each repeat group; canonical hashes match
the corresponding pilot requests. Order of execution was shuffled with seed 20261021.

| Pair | Historical p(to_do) | New canonical repeat range | Canonical mean |
| --- | ---: | ---: | ---: |
| Taoism × 37124 | 4.94445e-9 | 4.94445e-9–2.21595e-8 | 1.25238e-8 |
| Conservatism × 16204 | 0.5621765 | 0.00055278–0.56217650 | 0.27722357 |
| Care ethics × 16264 | 0.999999999980 | 0.999999999974–0.999999999980 | 0.999999999978 |

For conservatism × 16204, transformed condition means were:

| Label mapping | Action-line order | Mean p(to_do) |
| --- | --- | ---: |
| Canonical | Original | 0.27722357 |
| Swapped | Original | 0.97315150 |
| Canonical | Reversed | 0.99999998 |
| Swapped | Reversed | 0.99999136 |

The maximum difference between condition means is **0.72277642**; the identical
canonical repeat range is **0.56162372**. This is much larger than mere decimal
rounding. Near-zero and near-one diagnostics were far steadier in absolute terms.
All 36 responses returned both label logprobs and the requested model/provider.

These selected cases and three replicates/cell are diagnostic, not a population
bias estimate or a causal attribution to one FP8 implementation detail. Serving
batches, numerical precision or backend revisions may contribute. The results
strongly challenge treating a single canonical call as a stable, label-invariant
ethical preference. We do **not** silently average conditions or change providers.
Before full execution, choose either explicitly prompt-dependent canonical claims
or a counterbalanced/replicated redesign. A four-condition design multiplies
inference count/cost; three replicates per condition multiply it by twelve.

## Spending and execution controls

All new auxiliary calls shared a $0.95 fixed-cap ledger, leaving headroom for the
single missing-cell request under the $1 task limit. Existing safeguards reserve
the whole provider context plus the maximum output budget at explicit price
ceilings with 10% headroom. There are no hidden inference retries; every attempt
must claim budget and a unique task before dispatch. Unknown charges remain
conservatively accounted. All actual responses, requests, usage and cost are kept.

New confirmed spending:

| Item | Cost |
| --- | ---: |
| Pilot completion | $0.00061760 |
| 36 reliability/label-order requests | $0.01515048 |
| 68 semantic-screen batches | $0.05223642 |
| Total additional | **$0.06800450** |

No new HTTP errors or unknown charges occurred. The original pilot's older 502
charge remains unknown and conservatively accounted; it is not reclassified free.

SQLite WAL/FULL commits, provider-only routing, bounded concurrency/backoff,
per-run dispatch limits, configuration fingerprints, integrity checks and
idempotent resume remain in place. Completed valid pairs are never normally
recomputed. Crash-uncertain in-flight work requires reconciliation. Blank
probabilities are never imputed, and distance exports require complete vectors.

The automated test suite passes **28 tests**, covering the original execution safeguards,
label/action transformations, candidate approval/hash enforcement, complete source-text
preservation and auxiliary-study budget/idempotence checks.

## Full-run plan and dry run

`configs/full-experiment-candidate.json` freezes all 24 constitution-file hashes,
the candidate/approval-file hashes, exact prompt templates and inference parameters,
probability/distance definitions, retry/concurrency/budget/checkpoint settings and
completion checks. It is explicitly **blocked**, with zero approved scenarios and
zero currently authorized full-run spending. A live run using the candidate
scenario file is rejected until its approval sidecar is signed and its file hash
matches. A dry run is permitted without authorizing inference.

Dry run verified **24 × 1,336 = 32,064 candidate evaluations**, with API calls
patched to fail if attempted: **zero API/inference requests**. Approval of any
held-out case changes that count, the MAD divisor and the configuration hash.
This does not certify 1,336 approved scenarios: there are currently zero.

Before launching:

1. Review the 24 queued cases and approve the automated-screening policy for the
   remaining candidates. Record final included/excluded IDs; do not silently
   repair actions. Regenerate and freeze the scenario file and hashes.
2. Resolve the failed reproducibility and label/order checks. Approve the measurement
   definition and associated claims, or budget a redesigned counterbalanced pilot.
3. Regenerate the plan with final N and budget. The proposed canonical $25 budget is
   not authorization and is not sufficient evidence for a larger replicated design.
4. Record explicit scenario approval and a matching approved-file hash. Run the
   dry run again; verify 24*N (or the explicitly redesigned count) and MAD divisor N.
5. Only after explicit authorization, supply a nonzero budget and launch using the
   frozen inputs, output and ledger. Resume the same ledger; never reset spending.

Required completion checks include all expected unique evaluations with no missing
cells; valid token probabilities and model/provider identity; acceptable binary
mass; matching hashes; symmetric nonnegative zero-diagonal L1/MAD matrices and
triangle inequalities; correct MAD denominator; reconciled spending and a
pre-registered numerical/label-order acceptance policy. Proposed diagnostic
thresholds (.02 repeat range and .05 condition-mean shift) are recorded as
unapproved and are currently failed by the near-half case.
