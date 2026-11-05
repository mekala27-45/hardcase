# Hardcase

Portfolio retrieval training experiment on a frozen scientific benchmark.
Rankings indicate benchmark relevance, not claim truth or clinical advice.
Training, teacher supervision, held-out quality and live serving evidence
are reported separately. Results apply to the declared data, artifacts,
compute budget and environment. A candidate may fail promotion.

A controlled study of selective retrieval-encoder fine-tuning, mined weak negatives and teacher distillation, with an inspectable ONNX serving path.

[Open the workbench](https://mekala27-45.github.io/hardcase/) | [Completion evidence](RESULTS.md) | [Specification](docs/SPEC.md) | [Operations](OPERATIONS.md)

## Current execution state

The published interface displays retained evidence. Live learned search has not yet been verified. The production database credential transfer is awaiting explicit approval. Final test evaluation remains closed until the pretest live check passes. Training state is recorded in the linked workflow and imported terminal manifests, not inferred from this description.

[Actual training workflow](https://github.com/mekala27-45/hardcase/actions/runs/42113390181)

## Observed preparation

frozen_preparation | verified inventory | 5183 documents | denominator 1 | corpus | data_inventory | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

frozen_preparation | verified inventory | 638 queries | denominator 1 | fit | data_inventory | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

frozen_preparation | verified inventory | 146 queries | denominator 1 | validation | data_inventory | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

frozen_preparation | verified inventory | 25 queries | denominator 1 | leakage_audit | data_inventory | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

base_encoder | mean nDCG@10 | 0.68090309 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

bm25 | mean nDCG@10 | 0.61139123 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

cross_encoder | executed pair count | 3625 pairs | denominator 1 | fit | teacher_supervision | 2026-11-05T21:16:37.446777+00:00 to 2026-11-05T21:19:09.443826+00:00 | source evidence/preparation/teacher-receipt.json (15174e3fd45f4d36ef901e00a128e0308402582a3ef76d8408d150346b522187)

## Reproduction

Read OPERATIONS.md before executing a stage. Frozen inputs are retained under [input-assets-42109854166](https://github.com/mekala27-45/hardcase/releases/tag/input-assets-42109854166); verify requests/retain.json hashes before use. The test vault is excluded from training. Selected model assets and independent rankings are linked only after their runs complete.

## Limits

This is a portfolio project, not employment experience or a medical product. The teacher is weak supervision. Published qrels can be incomplete, pretrained exposure is unknown and a single seed does not establish training stability. A completed negative result is valid.

## Rights

Source code is MIT licensed. Dataset and model rights remain separate; see THIRD_PARTY_NOTICES.md.
