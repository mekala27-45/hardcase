# Model card: uniform_contrastive

Portfolio retrieval training experiment on a frozen scientific benchmark.
Rankings indicate benchmark relevance, not claim truth or clinical advice.
Training, teacher supervision, held-out quality and live serving evidence
are reported separately. Results apply to the declared data, artifacts,
compute budget and environment. A candidate may fail promotion.

Status: completed.

Base model: sentence-transformers/all-MiniLM-L6-v2

Pinned revision: 1110a243fdf4706b3f48f1d95db1a4f5529b4d41

Teacher: cross-encoder/ms-marco-MiniLM-L6-v2 at 233902d25c440f23af6f7d6e94d2946bac0bee0a. Teacher scores are weak supervision, not evaluation labels.

## Design and data

The exact planned modules, optimizer, seed, temperatures, update budget, candidate rules and selection policy are in [requests/experiment.json](../requests/experiment.json). Observed grouped development membership is in [the split manifest](../evidence/preparation/split.json). The intended use is fixed-corpus scientific document retrieval. Scores are ranking similarities, not truth probabilities.

frozen_preparation | verified inventory | 5183 documents | denominator 1 | corpus | data_inventory | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

frozen_preparation | verified inventory | 638 queries | denominator 1 | fit | data_inventory | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

frozen_preparation | verified inventory | 146 queries | denominator 1 | validation | data_inventory | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

frozen_preparation | verified inventory | 25 queries | denominator 1 | leakage_audit | data_inventory | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

base_encoder | mean nDCG@10 | 0.68090309 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

bm25 | mean nDCG@10 | 0.61139123 nDCG@10 | denominator 146 | validation | retrieval_quality | 2026-11-05T21:09:38.304237+00:00 to 2026-11-05T21:19:09.579199+00:00 | source evidence/preparation/prepare.json (1af8773e8f86c7217c86d94d484f9b264eacb7b35578b07241ce60f6e39c3ecf)

cross_encoder | executed pair count | 3625 pairs | denominator 1 | fit | teacher_supervision | 2026-11-05T21:16:37.446777+00:00 to 2026-11-05T21:19:09.443826+00:00 | source evidence/preparation/teacher-receipt.json (15174e3fd45f4d36ef901e00a128e0308402582a3ef76d8408d150346b522187)

## Learning evidence

uniform_contrastive | actual completed run | 120 optimizer updates | denominator 1 | fit | actual_training | 2026-11-05T22:20:48.450220+00:00 to 2026-11-05T22:44:44.261488+00:00 | source evidence/training/uniform_contrastive/run.json (9a00621f3f205864e34cf9e5ad2a992441b2c5da107c9a90796094035ce82dad)

uniform_contrastive | actual completed run | 960 query examples | denominator 1 | fit | actual_training | 2026-11-05T22:20:48.450220+00:00 to 2026-11-05T22:44:44.261488+00:00 | source evidence/training/uniform_contrastive/run.json (9a00621f3f205864e34cf9e5ad2a992441b2c5da107c9a90796094035ce82dad)

uniform_contrastive | actual completed run | 3548928 parameters | denominator 1 | fit | actual_training | 2026-11-05T22:20:48.450220+00:00 to 2026-11-05T22:44:44.261488+00:00 | source evidence/training/uniform_contrastive/run.json (9a00621f3f205864e34cf9e5ad2a992441b2c5da107c9a90796094035ce82dad)

Selected checkpoint and parameter hashes: [evidence/training/uniform_contrastive/run.json](../evidence/training/uniform_contrastive/run.json).

## Evaluation and deployment

Final held-out quality and live serving are not established by this card. See RESULTS.md and the immutable evaluation/release artifacts when available. Test qrels may be incomplete, pretrained benchmark exposure is unknown, and one training seed does not demonstrate stability. Source notices are retained separately. Do not describe the teacher as an independent evaluator or this project as foundation-model pretraining.
