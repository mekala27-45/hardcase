---
name: evaluate-retriever
description: Execute or rederive the frozen Hardcase held-out retrieval study from selected checkpoints, canonical rankings and independent published qrels.
---

Read AGENTS.md and the held-out contract in docs/SPEC.md. Require complete selected training manifests, export selection and verified pretest learned browser/client/DB evidence. Bind their digests in requests/evaluate.json. Inspect request identity before making the test vault available.

Set PYTHONPATH for the repository, install requirements-resolved.txt and run `python -m evaluation.run`. The evaluator preserves all planned main and export rows. It reads qrels only for independent grading and dependence grouping. Missing pairs suppress complete estimates and promotion claims.

Inspect artifacts/evaluation/<evaluation_id>/planned-inventory.json, executions.json, canonical ranking files, main-rows.json, export-rows.json, test-groups.json, export-drift.json, error-sample.json and report.json. Recompute metrics from ranked IDs and original qrels. Keep the selected checkpoint fixed and report all prespecified secondary contrasts.

Stop on a changed checkpoint, tokenizer, corpus, selection, label digest or missing pretest live evidence. Do not tune from test results. Preserve failure rows and original attempts. A transport retry needs a new attempt record and the same immutable artifacts; it cannot silently overwrite the first outcome.
