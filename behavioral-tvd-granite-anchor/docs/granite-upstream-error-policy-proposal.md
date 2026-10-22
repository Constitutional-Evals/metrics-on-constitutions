# Proposed upstream-error handling — NOT ACTIVE

This is an operational proposal for investigator review. This recovery does not
change `api.py`, the exploratory dispatcher, scientific inputs, request templates,
provider pinning, probability extraction, caps, retry limits or frozen manifest.

## Distinguish the response types before accepting a model result

An HTTP 200 status alone does not establish successful inference. Preserve the
exact response and actual HTTP status before classification. An explicit error
envelope with internal code 429, 500, 502, 503 or 504, no model-output choices,
and no conflicting model/provider identity should be classified as a transient
upstream failure. Missing identity in such an error envelope does not establish
that another provider served a model. Recognize a bounded, documented schema;
do not infer retryability from arbitrary error-message substrings.

A response that identifies an unexpected model or provider must still stop,
including an error envelope containing conflicting identity. Mixed error and
model-output envelopes, unknown error shapes/codes, invalid usage, or ambiguous
partial output require review. Do not reinterpret them automatically.

For a purported successful model response, keep the exact frozen model/provider
checks, genuine answer-token logprob validation, parameter/prompt hashes and
canary thresholds. Missing required logs, malformed distributions and genuine
identity mismatches are not successful measurements. The established bounded
`logprobs:null` policy remains distinct from upstream errors. Never derive a
probability from a sampled answer or silently fill missing values.

## Bound, account and audit retries

For recognized transient error-only envelopes, record a separate paid attempt
with the original HTTP200 status, embedded status, complete original response,
request/prompt hashes, observed identity and usage, timing and classification.
Use actual valid reported cost when available; otherwise retain the entire
conservative reservation as charged. Retry only the identical logical task and
request after the existing bounded backoff, within three lifetime attempts,
2,000 physical primary attempts per batch, concurrency three, the persistent
$1 stage cap and shared $10 experiment cap. All concurrent reservations count.
If the attempt limit is exhausted, preserve explicit missing status and stop
for review. Do not fall back to another model/provider or refund unknown costs.

Before activation, add meaningful fixtures for an error-only HTTP200/504 response,
an actual identity mismatch, mixed error/output, an unrecognized error, exhausted
attempts, uncertain billing, resume, duplicate prevention and canary drift.
Use fixtures and existing saved envelopes without live API spending; a separately
authorized small live validation can follow review.

## Version boundary

The current frozen manifest hashes the dispatcher and API client source. Patching
them in place would fail its integrity checks and silently changing those hashes
would change the run ID. Neither is permitted by this task. The current run
continues to use its existing frozen implementation with individually authorized,
audited recoveries such as this one.

Automatic handling should be proposed as a separate reviewed execution version
with the new source hashes, a new immutable manifest/run identity and explicit
links to the original protocol and incident evidence. If the investigator wants
to continue the same scientific collection across that boundary, first design
and approve an explicit provenance/checkpoint migration or version-aware runner:
preserve all original rows and task identities, link rather than overwrite earlier
records, demonstrate unchanged scientific requests and probability definitions,
and retain the original shared experiment-wide spending history and cap across
versions. Do not create a budget-resetting replacement ledger or silently pool
different configurations. Such engineering and any migration need review and
validation; they are not implemented or activated here.

The simpler immediate route is the unchanged runner with bounded, explicit
recoveries. Successful completion of this recovery can make the next stages
technically ready, but does not reactivate Batches 4 or 5.
