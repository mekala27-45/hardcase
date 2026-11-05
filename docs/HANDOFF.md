# Continue Hardcase

The repository review branch is `build/day27-evidence-completion`, with draft PR [1](https://github.com/mekala27-45/hardcase/pull/1). Main remains `ab8c8c2be8aa7854828b3fa10b07b48df6bc71cb`; it has not received the later review work. Read RESULTS.md and the latest runtime terminal before describing completion.

## Frozen experiment

Actual training run [42113390181](https://github.com/mekala27-45/hardcase/actions/runs/42113390181) completed all three arms. Each recorded 120 optimizer updates, 960 query examples, all 638 fit queries, 32 changed trainable tensors and no changed frozen tensor. The validation-selected checkpoint is hard_contrastive/update 40. Selection identity is `bc763a19f62ca113ed8454de3851d1fb80748c1bf530379ad2205b7a2731417a`. See evidence/training/ledger-audit.json and the complete raw step ledgers.

Original model checkpoints and export artifacts remain under `training-assets-42113390181`. The original INT8 selection was rejected for portable deployment after startup failure on three independent AMD EPYC workers. All original artifacts and selection evidence remain retained. The unchanged float32 parent is frozen by compatibility run [42127068812](https://github.com/mekala27-45/hardcase/actions/runs/42127068812), release `training-assets-42127068812`, export identity `7b4d374da3bc93378f138409b2df47507c72a11e5bfa7bf4b8d833743ca9b943`. No training, corpus-vector or tolerance change occurred, and test access stayed closed.

The intended learned bundle is `43f7a256426411096133ff091bac9c2564db5c0487ea5a3c99bb5677f1c1cfda`. The unchanged base bundle is `7d1a32fef82ec596b80a04cfc7abe73a7a0388733464bd4dd60ca112492cc310`. The base remains the default until every promotion gate passes. A failed quality result is a valid conclusion.

## Pending external actions

Automatic approval review rejected further publication to main, transfer of the Hardcase database credential to Vercel, and initialization of persistent model/bundle/alias records in Neon. The read-only SQL manifest hashes matched, but the database initialization transaction did not execute. The exact prepared transaction is deploy/registry-initialization.sql. Do not retry through another transport. Obtain explicit approval to publish PR 1, execute the prepared registry initialization, and store the Hardcase database and protected operator credentials in the Hardcase Vercel production/preview environments. Public production access also needs the project-specific protection setting reviewed; the operator endpoints must remain protected.

The protected preview request received HTTP 402 `api-deployments-free-per-day`, with a reported 86400-second retry interval. Do not alter billing, create another account or work around the quota. The existing public workbench at https://mekala27-45.github.io/hardcase/ reflects older main evidence and has no configured live API. The Vercel scaffold must not be described as learned inference.

Local Windows commands and native browser control are blocked by Linux-only paths in the workspace permission configuration. Reopen a correctly configured Windows workspace before fresh native browser verification. Later review edits are on GitHub; the earlier local checkout is stale. Do not overwrite the review branch with that checkout.

Project IDs: Neon `wispy-haze-91153072`, database `hardcase`, owner `hardcase_owner`; Vercel `prj_xNmGw7TnbVsiquXURbedLzAAHzhA`, team `team_NNcxgB3J9dHQnUJYJJYvRMda`. Credentials are not stored in this document.

## Completion order

After approval and quota availability, deploy the exact reviewed runtime request with its fixed archive hash. Confirm packaged bundle identities and actual startup probes on the host, then database-backed readiness. Use distinct fresh experimental queries from a browser and a separate HTTP client. Independently read their committed receipts from Neon and require matching deployment, bundle, model, tokenizer, corpus and index identities. Derive evidence/live/pretest.json using deploy/verify_live.py.

Only after that verification may requests/evaluate.json bind the existing selection, compatibility export and pretest digest. The restore helper obtains original trained checkpoints and the compatibility serving archive separately. It must not restore the rejected original serving selection by accident. Execute all planned held-out rows; keep unsupported INT8 observations null with their failure reasons. Do not choose another checkpoint or tune against test results.

Perform the sixteen-request serial public smoke with at least one-second spacing. Combine it with the separately observed local open-loop envelope; the public smoke is not a stable p95 benchmark. Recompute the release decision from actual artifacts. Promote only if every gate passes and publication is authorized. Verify any transition using a fresh request and independent database read.

Regenerate source-bound documentation, both theme checks, the eighteen-line checklist and final live artifact/persistence verification. Create a product release tag only after the core evidence is complete. Artifact prereleases are not product releases.
