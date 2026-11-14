# Hardcase results

Portfolio retrieval training experiment on a frozen scientific benchmark.
Rankings indicate benchmark relevance, not claim truth or clinical advice.
Training, teacher supervision, held-out quality and live serving evidence
are reported separately. Results apply to the declared data, artifacts,
compute budget and environment. A candidate may fail promotion.

## Completion evidence

1  not done: Scaffold, preregistration and actual gradient/export/free-host probes.
   Evidence: Actual gradient/export probe: evidence/setup/probe.json. Learned free-host startup remains unverified; protected preview creation was blocked by the Vercel daily quota in evidence/hosting/preview-limit.json.
2  done: Evidence-bound claim renderer with missing-data and mode checks.
   Evidence: src/hardcase/claims.py, tests/test_claims.py, evidence/claims/preparation.json and passing CI 42127330166; source-bound documents and missing-data states exercised by review 42127330258.
3  done: Licensed data capture, grouped splits, purge and frozen inventories.
   Evidence: evidence/preparation/source.json, split.json and purge.json: 5183 documents, 638 fit queries, 146 validation queries and 25 purged queries, with retained license notices and frozen input assets.
4  done: Full-corpus BM25 and unchanged encoder baselines with independent checks.
   Evidence: evidence/preparation/prepare.json records full-corpus BM25 and unchanged-encoder validation; independent metric/ranking checks passed in CI and the full runtime test suite.
5  done: Frozen weak-negative lists, actual teacher scores and recorded audit.
   Evidence: evidence/preparation/teacher-receipt.json records 3625 executed teacher pairs. mining-audit.json and audit-commentary.json retain 40 frozen source-span inspections, clearly separate from human expert adjudication.
6  done: Three actual training arms, parameter-change evidence and validation selection.
   Evidence: Training run 42113390181 and evidence/training/ledger-audit.json: all three arms completed 120 updates and 960 examples; every fit query appeared, all frozen tensors stayed unchanged, and validation selected hard_contrastive/update 40.
7  done: Working float32 ONNX, quantization investigation and matched resource evidence.
   Evidence: evidence/export/parity.json, evidence/compatibility/decision.json and evidence/serving/paired-timing.json. Unchanged float32 passed; INT8 portability failure retained. Runtime run 42127323550 measured matched query units without changing selection.
8  done: Compatible bundle registry with atomic aliases, promotion and rollback rules.
   Evidence: Runtime 42127323550 verified actual compatible bundles, immutable registry records, alias CAS, in-flight rollback and revocation in isolated PostgreSQL. Production initialization remains explicitly blocked in evidence/hosting/registry-approval.json.
9  not done: Live learned inference verified by browser, separate client and fresh DB read.
   Evidence: evidence/hosting/preview-limit.json and registry-approval.json. No fresh public learned browser/client pair or independent production DB receipt exists; credential configuration and deployment remain blocked.
10  not done: Complete frozen held-out rankings, independent metrics and paired analysis.
   Evidence: No requests/evaluate.json or final evaluation report has been created. Held-out execution remains 0/1500 main rows and 0/600 export rows pending the pretest live gate.
11  not done: Measured serving stages, memory, admission behavior and bounded public smoke.
   Evidence: evidence/serving/local-open-loop.json: 60/60 at 1 RPS and 120/120 at 2 RPS, p95 about 33/35 ms and peak server RSS about 430 MiB. The required sixteen-query public smoke is unexecuted.
12  not done: Evidence-bound release decision and all six independently observed fault cases.
   Evidence: All six actual-artifact fault cases passed in evidence/faults/actual-bundles.json and runtime-transactions.json. The release gate remains a refusal because held-out and public-live evidence are missing; no promotion executed.
13  not done: Five working views with genuine live search and inspectable model evidence.
   Evidence: Five implemented views and real imported training records pass review-interface checks. Published Pages is still the older main version, with no configured genuine public API search.
14  done: Both validated themes, primary fonts and responsive accessibility checks.
   Evidence: Review 42129215925 passed both themes, primary fonts, contrast, 360/768/1440 layouts, reduced motion and native Chromium 200-percent zoom. evidence/frontend/native-zoom.json records DPR 1 to 2 and CSS viewport 1440 to 720 with no page overflow in all five views.
15  done: Agent guidance, three skills, SPEC, model cards, notices and operating notes.
   Evidence: AGENTS.md, CLAUDE.md, .agents/skills/*/SKILL.md (three repository-scoped skills), docs/SPEC.md, four model cards, THIRD_PARTY_NOTICES.md, OPERATIONS.md and docs/HANDOFF.md.
16  done: Passing CI, bounded worker requests and retained artifact provenance.
   Evidence: Runtime 42127323550 passed all 78 tests without skips. CI 42129215961 passed both hash seeds, and interface review 42129215925 passed native zoom. Input/model/compatibility assets retain hashes and release provenance; bounded requests and failed attempts are preserved.
17  not done: Clean-worktree rederivation and final live artifact/persistence verification.
   Evidence: Clean isolated runners restored exact hashed model artifacts and rederived the source-bound documents and interface. Final public artifact, learned browser/client and independent production persistence verification remain blocked.
18  not done: Authorized release and tag after commits with this evidence checklist.
   Evidence: Draft PR 1 is prepared; main publication was rejected by automatic approval review. No product release tag exists. The meaningful implementation history is recorded in evidence/build/commit-inventory.json; artifact prereleases are not product releases.
