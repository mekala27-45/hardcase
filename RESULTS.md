# Hardcase results

Portfolio retrieval training experiment on a frozen scientific benchmark.
Rankings indicate benchmark relevance, not claim truth or clinical advice.
Training, teacher supervision, held-out quality and live serving evidence
are reported separately. Results apply to the declared data, artifacts,
compute budget and environment. A candidate may fail promotion.

## Completion evidence

1  done: Scaffold, preregistration and actual gradient/export/free-host probes.
   Evidence: evidence/setup/probe.json and evidence/live/pretest.json retain actual gradient/export and public learned-runtime observations; configuration is recorded in evidence/live/configuration.json.
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
   Evidence: Actual-bundle registry and transactional rollback/revocation tests: evidence/faults/runtime-transactions.json. The initialized production registry and matching receipts are independently observed in evidence/live/.
9  done: Live learned inference verified by browser, separate client and fresh DB read.
   Evidence: Unchanged deploy/verify_live.py revalidates separate public browser/client responses against independently queried production database receipts and packaged artifact identities in evidence/live/.
10  done: Complete frozen held-out rankings, independent metrics and paired analysis.
   Evidence: evidence/evaluation/report.json and independent-audit.json bind the first frozen attempt, retained rankings, original judgments, all planned rows and independent regrading.
11  done: Measured serving stages, memory, admission behavior and bounded public smoke.
   Evidence: Local staged timing and open-loop observations remain in evidence/serving/. The bounded public smoke binds sixteen serial requests and persisted readbacks in public-smoke.json and evidence/live/client-observations.json; first observer failure is retained under evidence/serving/attempts/.
12  done: Evidence-bound release decision and all six independently observed fault cases.
   Evidence: evidence/release/decision.json derives eligibility or refusal from frozen study, public verification and local resource evidence. All six actual-artifact fault cases are retained. A refusal is a valid completed decision and does not promote a model.
13  done: Five working views with genuine live search and inspectable model evidence.
   Evidence: The public workbench serves genuine learned searches with artifact receipts. Existing training/evaluation/release/data views and the added Compare view retain explicit missing states. See evidence/live/observations.json and frontend checks.
14  done: Both validated themes, primary fonts and responsive accessibility checks.
   Evidence: Review 42129215925 passed both themes, primary fonts, contrast, 360/768/1440 layouts, reduced motion and native Chromium 200-percent zoom. evidence/frontend/native-zoom.json records DPR 1 to 2 and CSS viewport 1440 to 720 with no page overflow in all five views.
15  done: Agent guidance, three skills, SPEC, model cards, notices and operating notes.
   Evidence: AGENTS.md, CLAUDE.md, .agents/skills/*/SKILL.md (three repository-scoped skills), docs/SPEC.md, four model cards, THIRD_PARTY_NOTICES.md, OPERATIONS.md and docs/HANDOFF.md.
16  done: Passing CI, bounded worker requests and retained artifact provenance.
   Evidence: Runtime 42127323550 passed all 78 tests without skips. CI 42129215961 passed both hash seeds, and interface review 42129215925 passed native zoom. Input/model/compatibility assets retain hashes and release provenance; bounded requests and failed attempts are preserved.
17  done: Clean-worktree rederivation and final live artifact/persistence verification.
   Evidence: Hash-locked original inputs were restored into a fresh checkout for independent regrading. Public browser/client/DB proof is separate in evidence/live/release-20261114/; the original pretest is unchanged.
18  not done: Authorized release and tag after commits with this evidence checklist.
   Evidence: Main contains the merged implementation and live proof. A product release tag remains pending final verified core evidence; asset prereleases do not satisfy this line.
