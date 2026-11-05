---
name: prepare-retrieval-training
description: Prepare or verify the frozen Hardcase corpus, development split, candidate lists and teacher supervision before actual encoder training.
---

Read AGENTS.md, docs/SPEC.md and requests/experiment.json. Require the observed setup probe, exact model lock and compatible environment. Set PYTHONPATH=src:. on Linux or src;. in PowerShell.

Run `python -m hardcase.mining.prepare` only for a new authorized preparation attempt. It captures source bytes, isolates the test vault, purges text leakage, groups fit/validation queries, encodes the unchanged full corpus, mines lists and scores teacher pairs. Do not provide data/vault to training.

Verify data/manifests/preparation.json, source.json, split.json and purge.json; data/processed/candidates.json, schedule.json and teacher-scores.json; and artifacts/preparation/prepare.json. Check all configuration and content digests, complete corpus inventory, positive exclusions, common candidate alignment and actual teacher receipts. Inspect the forty-pair automated audit without treating unjudged text as irrelevant.

Run `python -m unittest discover -s tests`. Commit the bounded training request with the verified input artifact ID and digest. Run `python -m hardcase.training.run` against these frozen inputs. Stop on a changed digest, missing labels, incomplete fit coverage, model revision mismatch or failed setup. Preserve terminal evidence; never replace missing real data with synthetic benchmark rows.
