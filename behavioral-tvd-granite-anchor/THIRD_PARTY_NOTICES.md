# Third-party data and attribution

## Constitutional anchors

The 24 aligned anchors derive from Constitutional-Evals/constitutions, revision
`c34525f09629efe79d236837f89c022e64281363`, licensed CC BY 4.0:
https://github.com/Constitutional-Evals/constitutions/tree/c34525f09629efe79d236837f89c022e64281363/anchors

Preserved original provenance and upstream notices: [data/constitutions/SOURCE.md](data/constitutions/SOURCE.md).
Some anchors derive from EigenBench (Chang et al., arXiv:2509.01938), as indicated
in their original provenance. Upstream attribution:
https://github.com/Constitutional-Evals/constitutions/blob/c34525f09629efe79d236837f89c022e64281363/NOTICE.md

Modification: recursive removal of embedded `scenario`/`scenarios` fields;
remaining contents and provenance retained. Exact frozen experiment files remain
in [data/granite-exploratory/constitutions/](data/granite-exploratory/constitutions/).

## DailyDilemmas

Yu Ying Chiu, Liwei Jiang, and Yejin Choi. 2024.
*DailyDilemmas: Revealing Value Preferences of LLMs with Quandaries of Daily Life.*
https://arxiv.org/abs/2410.02683

Dataset: https://huggingface.co/datasets/kellycyy/daily_dilemmas
Configuration: `Dilemmas_with_values_aggregated`; split: `test`.
The dataset card declares **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).
Metadata checked at dataset revision `372352c4143ec4923c50b4472bd3148a474f7ab8`;
this licensing check does not establish that revision as the original download
revision. Original input provenance/hashes are retained in
[data/scenarios-v2.source.json](data/scenarios-v2.source.json).

Processing: pair 2,720 action-level rows into 1,360 dilemmas; retain original
situation, paired actions, and topic metadata; exclude annotations from prompts;
apply the documented automated-screening policy to select 1,336 scenarios.
Neither original situation nor action wording is rewritten. The 239-scenario
supplement additionally excludes scenario 29912 solely for common-grid
completeness; it does not revise the approved experiment.

## Model metadata and outputs

No model weights are included. Historical metadata names models with different
licenses; the Granite model card identifies Apache 2.0 for its weights. This does
not automatically license this project's code or API outputs. Public model-card
contact details in archived metadata are upstream attribution, not account
credentials. Publication should retain source credit and consider applicable
provider/model output terms; this notice does not independently establish all
redistribution rights.

## Project code license remains undecided

The private source snapshot contains no top-level license for the original code.
No new code license is inferred or applied here. The owner/organization should
select and approve one before treating this snapshot as reusable open-source
software. Third-party CC BY 4.0 attribution remains applicable independently.
