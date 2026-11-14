# Paired retrieval diagnostics

Open the Compare view and enter one to eight queries, one per line. Choose ten or twenty results per retriever. Run comparison, select a query, inspect rank changes, and download the diagnostic report. Reloading clears the workspace.

The runner snapshots the `base` and `experimental` bundle IDs and generations before creating a new public session. Every pair uses the same query and depth. It sends requests serially, with one-second spacing, and independently reads each persisted receipt. No operator credential is available to this interface.

A pair is complete only when both fresh responses match their query digest, alias snapshot, artifact identity, depth and persisted receipt. The pair must use the same corpus and deployment. Alias changes, incomplete lists, duplicate IDs, invalid scores and changed receipts fail closed. After a refusal the runner sends no more requests on that session, since an uncertain server-side request might still be active. Missing rows remain in the planned denominator.

Stop after current request drains the in-flight request and its receipt readback, then prevents additional searches. Completed pairs remain inspectable. Stopping cannot undo an already admitted server request. Navigating to another workbench view does not cancel the run; returning shows its current state.

Shared documents counts the intersection of the two returned lists. Jaccard divides that intersection by their union. Mean shared rank shift averages absolute rank differences only over shared documents; it is null when none are shared. Signed rank change is baseline rank minus learned rank. A document outside a returned list has no observed rank in that list.

The reciprocal-rank fusion preview sums `1 / (60 + rank)` across the two truncated lists and breaks ties by document ID. This calculation runs in the browser. It does not query the full corpus again, deploy a hybrid model or measure relevance. Similarity scores from different encoders are not subtracted or treated as calibrated probabilities.

Reports include query fingerprints, both verified receipts, observed request latencies, bundle snapshots and every failed/cancelled row. Raw query strings and session capabilities are excluded. Queries stay in browser memory and are sent only to the existing search endpoint; the service stores query digests, not raw visitor text. A digest is an identifier, not encryption, and can reveal a guessable query through comparison. Download reports only when you intend to keep these diagnostic records.

The frozen study retains its original checkpoints, candidates, export choice, labels and statistical policy. This unlabeled interface is not a new held-out experiment and supplies no training or promotion authority. To make a fresh generalization claim after inspecting results, register a new experiment and use untouched evaluation data.

## Independent regrading

After restoring the hash-locked inputs and admitting the frozen pretest proof, run `python -m evaluation.run --audit-retained evidence/evaluation`. Only the existing evaluation entry point opens the test vault. The auditor independently recalculates relevance metrics, checks every planned method-query row and summary, verifies ranking/report/label identities and checks the primary mean. It does not rerun models, refill failed exports or select checkpoints.

For a later public deployment, keep the original `evidence/live/pretest.json` unchanged. Capture new browser/client/database evidence separately, then run `python deploy/decide_release.py --live-evidence evidence/live/release-20261114/verified.json`. The release decision still requires the public smoke and live proof to name the same deployment and bundle. The command emits a proposal or refusal; it never changes an alias.
