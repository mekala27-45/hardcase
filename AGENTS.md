# Hardcase project rules

Read docs/SPEC.md and requests/experiment.json before changing training or evaluation. The experiment is frozen. Do not alter candidates, optimizer budget, checkpoint selection or export policy after a run starts. Retain failed runs. Fixes after viewing test results require a new experiment identity and new untouched evaluation data for a fresh generalization claim.

Use Python 3.12.13 and requirements-resolved.txt for training. Use requirements-serve.txt for the inference-only process. Set PYTHONPATH to src:. on Linux or src;. on PowerShell. Run `python -m unittest discover -s tests`. Run `npm ci` and `npm run build` inside site. The local PowerShell helper deploy/test-local.ps1 selects a writable temporary directory.

Training reads only the frozen fit labels, candidates, teacher scores and schedule. Validation selects checkpoints. Only evaluation/run.py reads the test vault, after immutable training/export selection and verified pretest learned API evidence. The teacher never supplies evaluation labels.

Never put credentials, capabilities, private visitor text or model weights into source history. Public source text retains its notices. Large assets use hashed bounded release assets. The API only loads packaged allowlisted bundles. Operator authority stays outside public inference.

Edit result generators and source artifacts rather than hand-writing measured claims. Run `python -m hardcase.claims` to regenerate RESULTS.md. Missing evidence is not done and has no numeric substitute. A setup gradient probe is not benchmark training; a health deployment is not learned inference; a scripted fault is not production reliability.

Project procedures are in .agents/skills/prepare-retrieval-training, .agents/skills/evaluate-retriever and .agents/skills/promote-model-bundle. These are repository procedures, not globally installed personal skills. They grant no external permissions. Follow the current user authorization and preserve any explicit approval blocker.
