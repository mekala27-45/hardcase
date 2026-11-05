# Decisions and unresolved questions

The experiment remains the preregistered SciFact comparison. These decisions do not add a new model family, seed or test-driven selection.

## Scientific claims

- Unjudged documents remain weak negatives. The frozen audit shows teacher preferences and source text; it does not establish that these documents are irrelevant.
- Teacher agreement measures agreement with weak supervision. Only published qrels evaluate retrieval quality.
- One seed does not establish run stability. Query-group intervals quantify a different source of uncertainty.
- Benchmark relevance is not claim truth or clinical advice. Search returns sources and similarity scores.
- Adaptation to this fixed corpus is not evidence of unseen-document generalization.
- The pretrained model's benchmark exposure is unknown. The pinned revision establishes identity, not absence of pretraining contamination.

## Engineering choices

- Matched optimizer updates and example counts do not equal identical compute. Teacher preparation, mining and each arm's token and timing ledger remain separate.
- Distillation may not repay teacher execution. The teacher receipt records its actual pair count, tokens and elapsed seconds; final retrieval evidence must determine usefulness.
- Shorter inputs can remove relevant evidence. Every document preserves its original text and encoded span, and evaluation includes truncation slices.
- INT8 may be slower or less accurate on the selected CPU. Variant selection is frozen before test results and uses its actual symmetric corpus encoding.
- Exact search is appropriate for the declared corpus size and makes full-corpus membership inspectable. No approximate-index speed claim is made.
- An alias transaction does not prove that a subsequent request served the intended bundle. Fresh client and independent database observations are required.

## Observed constraints

Local package execution initially depended on network access that the local workspace could not provide. The bounded public standard-runner jobs therefore execute the real model work with frozen inputs, retained source commits and hashes. The preparation run completed against the full corpus.

The first responsive-navigation check found inconsistent button accessible names between desktop and narrow layouts. Explicit accessible labels fixed that failure, and the subsequent Pages checks passed. Failure and success run links are in BUILD-JOURNAL.md.

A later workspace configuration update introduced Linux-only writable paths into the Windows environment. Local command execution and native browser control are currently blocked by the environment's path validation. Review-branch CI remains available. No local check after that change is claimed.

Production database configuration and publication of further commits to main await explicit approval after automatic approval review rejected those actions. The draft pull request keeps subsequent changes reviewable. The test vault remains closed until independently verified learned serving exists.

## Observed export portability failure

The original export worker selected INT8 using its registered development and resource policy. Independent startup probes then produced inconsistent admission outcomes. Three additional standard CPU workers retained the exact same base and candidate float32 vectors, while INT8 differed from its frozen probe by up to 0.029012 at a required 0.00001 tolerance. The observed bundle bytes passed integrity checks. The probes do not by themselves establish the low-level cause.

The [ONNX Runtime quantization guide](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html) documents CPU-dependent quantization behavior and saturation as possible mechanisms. This is a hypothesis, not a proven diagnosis for this run. The project therefore retains the rejected INT8 artifact and selects the already-verified float32 parent for compatibility before any held-out access. No model weights, corpus vectors, labels or startup tolerances are edited. The original export selection and the compatibility decision have separate content identities. No reduced-range retuning or test-driven rescue is performed.
