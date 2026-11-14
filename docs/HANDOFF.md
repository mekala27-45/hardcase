# Continue Hardcase

PR [1](https://github.com/mekala27-45/hardcase/pull/1) is merged. The prepared Neon registry is initialized, production and preview credentials are stored as sensitive Vercel variables, and the production demo is public. Operators remain protected. The earlier approval blockers are resolved for Hardcase only. Read generated RESULTS.md and current evidence before describing completion.

## Frozen experiment

Actual training run [42113390181](https://github.com/mekala27-45/hardcase/actions/runs/42113390181) completed all three arms. Each recorded 120 optimizer updates, 960 query examples, all 638 fit queries, 32 changed trainable tensors and no changed frozen tensor. The validation-selected checkpoint is hard_contrastive/update 40. Selection identity is `bc763a19f62ca113ed8454de3851d1fb80748c1bf530379ad2205b7a2731417a`. See evidence/training/ledger-audit.json and the complete raw step ledgers.

Original model checkpoints and export artifacts remain under `training-assets-42113390181`. The original INT8 selection was rejected for portable deployment after startup failure on three independent AMD EPYC workers. All original artifacts and selection evidence remain retained. The unchanged float32 parent is frozen by compatibility run [42127068812](https://github.com/mekala27-45/hardcase/actions/runs/42127068812), release `training-assets-42127068812`, export identity `7b4d374da3bc93378f138409b2df47507c72a11e5bfa7bf4b8d833743ca9b943`. No training, corpus-vector or tolerance change occurred, and test access stayed closed.

The intended learned bundle is `43f7a256426411096133ff091bac9c2564db5c0487ea5a3c99bb5677f1c1cfda`. The unchanged base bundle is `7d1a32fef82ec596b80a04cfc7abe73a7a0388733464bd4dd60ca112492cc310`. The base remains the default until every promotion gate passes. A failed quality result is a valid conclusion.

## Current execution and authority

The original live pretest is immutable at evidence/live/pretest.json. requests/evaluate.json binds its digest and the frozen model/export selection. The first held-out attempt [43545916335](https://github.com/mekala27-45/hardcase/actions/runs/43545916335) is retained and independently audited. Product release [v0.2.0](https://github.com/mekala27-45/hardcase/releases/tag/v0.2.0) is published. Do not launch another selection or overwrite the first outcome. All promotion gates pass, but the baseline remains the default; no operator promotion was executed.

Later public verification is kept separately in evidence/live/release-20261114/. Its browser and separate-client receipts match independent Neon records on the same deployment as the sixteen-query public smoke. requests/release-check.json pins those later proof digests. The initial observer failure from comparing JSON key order is retained, and the corrected observer compares structural values.

Public workbench: https://mekala27-45.github.io/hardcase/ . Public API: https://hardcase-taupe.vercel.app . Existing Vercel protection remains enabled for generated deployment/preview URLs. Do not reinitialize the live database, rotate credentials, weaken protection, or change billing to reproduce this work.

Project IDs: Neon `wispy-haze-91153072`, database `hardcase`, owner `hardcase_owner`; Vercel `prj_xNmGw7TnbVsiquXURbedLzAAHzhA`, team `team_NNcxgB3J9dHQnUJYJJYvRMda`. Credentials are not stored in this document.

The Compare view is an unlabeled diagnostic layer over the existing base and experimental endpoints. Its bounded serial suites, rank shifts, receipt readbacks and RRF preview do not change the frozen experiment or grant operator authority. See docs/COMPARISON.md.

## Completion order

Keep the original pretest and evaluation identity unchanged. After importing the first attempt, restore the original hash-locked inputs and run `python -m evaluation.run --audit-retained evidence/evaluation`. This entry point regrades retained rankings without model execution. Keep unsupported INT8 results missing and preserve all failure records.

The original request already admitted the test vault. Do not change checkpoints, candidates, export policy, statistical settings or tolerances after seeing results. New generalization claims require a new experiment identity and untouched evaluation data.

The sixteen-request serial public smoke is retained. Combine it with the separately observed local open-loop envelope; the public smoke is not a stable p95 benchmark. Recompute the release decision with `python deploy/decide_release.py`, which checks requests/release-check.json. Refresh execution-dependent checklist rows with `python deploy/refresh_completion.py` and regenerate documentation with `python deploy/render_docs.py`. Promote only if every gate passes and publication is authorized. Verify any transition using a fresh request and independent database read.

Regenerate source-bound documentation, both theme checks, the eighteen-line checklist and final live artifact/persistence verification. Create a product release tag only after the core evidence is complete. Artifact prereleases are not product releases.
