# Hardcase

Portfolio retrieval training experiment on a frozen scientific benchmark.
Rankings indicate benchmark relevance, not claim truth or clinical advice.
Training, teacher supervision, held-out quality and live serving evidence
are reported separately. Results apply to the declared data, artifacts,
compute budget and environment. A candidate may fail promotion.

A controlled study of selective retrieval-encoder fine-tuning, mined weak negatives and teacher distillation, with an inspectable ONNX serving path.

[Open the workbench](https://mekala27-45.github.io/hardcase/) | [Completion evidence](RESULTS.md) | [Specification](docs/SPEC.md) | [Operations](OPERATIONS.md)

## Current execution state

The published interface displays retained evidence. Live learned search has not yet been verified. Production publication, registry initialization and deployment credentials await explicit approval. Vercel also rejected the prepared preview at its daily free deployment limit. Final test evaluation remains closed until the pretest live check passes. Training state is recorded in the linked workflow and imported terminal manifests, not inferred from this description.

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

## Completed training and frozen validation selection

The selected candidate is hard_contrastive. Its checkpoint identity and validation-only selection are retained in [the selection manifest](evidence/training/selection.json). The comparison below uses development validation; it is not held-out quality.

hard_contrastive | completed optimizer budget | 120 updates | denominator 1 | fit | actual_training | 2026-11-05T21:32:40.192018+00:00 to 2026-11-05T21:57:21.810318+00:00 | source evidence/training/hard_contrastive/run.json (dbbe8252d0482d1c956233700f269832148a59d896026d614ced82c8c40a6258)

hard_contrastive | completed training examples | 960 query examples | denominator 1 | fit | actual_training | 2026-11-05T21:32:40.192018+00:00 to 2026-11-05T21:57:21.810318+00:00 | source evidence/training/hard_contrastive/run.json (dbbe8252d0482d1c956233700f269832148a59d896026d614ced82c8c40a6258)

hard_contrastive | mean selected-checkpoint nDCG@10 | 0.69854383 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T21:32:40.192018+00:00 to 2026-11-05T21:57:21.810318+00:00 | source evidence/training/hard_contrastive/run.json (dbbe8252d0482d1c956233700f269832148a59d896026d614ced82c8c40a6258)

hard_distilled | completed optimizer budget | 120 updates | denominator 1 | fit | actual_training | 2026-11-05T21:57:21.840066+00:00 to 2026-11-05T22:20:48.427520+00:00 | source evidence/training/hard_distilled/run.json (5453d226e14d12f1b1113297fe97e690e76ad14d461af9bae8beac79d5148778)

hard_distilled | completed training examples | 960 query examples | denominator 1 | fit | actual_training | 2026-11-05T21:57:21.840066+00:00 to 2026-11-05T22:20:48.427520+00:00 | source evidence/training/hard_distilled/run.json (5453d226e14d12f1b1113297fe97e690e76ad14d461af9bae8beac79d5148778)

hard_distilled | mean selected-checkpoint nDCG@10 | 0.69799398 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T21:57:21.840066+00:00 to 2026-11-05T22:20:48.427520+00:00 | source evidence/training/hard_distilled/run.json (5453d226e14d12f1b1113297fe97e690e76ad14d461af9bae8beac79d5148778)

uniform_contrastive | completed optimizer budget | 120 updates | denominator 1 | fit | actual_training | 2026-11-05T22:20:48.450220+00:00 to 2026-11-05T22:44:44.261488+00:00 | source evidence/training/uniform_contrastive/run.json (9a00621f3f205864e34cf9e5ad2a992441b2c5da107c9a90796094035ce82dad)

uniform_contrastive | completed training examples | 960 query examples | denominator 1 | fit | actual_training | 2026-11-05T22:20:48.450220+00:00 to 2026-11-05T22:44:44.261488+00:00 | source evidence/training/uniform_contrastive/run.json (9a00621f3f205864e34cf9e5ad2a992441b2c5da107c9a90796094035ce82dad)

uniform_contrastive | mean selected-checkpoint nDCG@10 | 0.6894497 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T22:20:48.450220+00:00 to 2026-11-05T22:44:44.261488+00:00 | source evidence/training/uniform_contrastive/run.json (9a00621f3f205864e34cf9e5ad2a992441b2c5da107c9a90796094035ce82dad)

The serving variant is candidate_float32. Selection is frozen before test access. Float32 parity and measured INT8 drift are separate records in [parity.json](evidence/export/parity.json); quantization is not an exact-equivalence claim.

base_float32 | mean symmetric-export nDCG@10 | 0.68090309 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T22:44:46.538795+00:00 to 2026-11-05T22:54:38.417064+00:00 | source evidence/export/selection.json (d80c018f2e4c50d010258acd8069e94385118a5eeedc827cd20edd5268b7128f)

candidate_float32 | mean symmetric-export nDCG@10 | 0.69854383 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T22:44:46.538795+00:00 to 2026-11-05T22:54:38.417064+00:00 | source evidence/export/selection.json (d80c018f2e4c50d010258acd8069e94385118a5eeedc827cd20edd5268b7128f)

candidate_int8 | mean symmetric-export nDCG@10 | 0.69949976 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T22:44:46.538795+00:00 to 2026-11-05T22:54:38.417064+00:00 | source evidence/export/selection.json (d80c018f2e4c50d010258acd8069e94385118a5eeedc827cd20edd5268b7128f)

