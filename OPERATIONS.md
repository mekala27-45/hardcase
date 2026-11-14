# Operating Hardcase

Use an isolated checkout and the exact dependency files. Python is pinned by .python-version. Node is pinned by the Pages workflow. Do not upgrade dependencies during a frozen experiment.

On Linux set `export PYTHONPATH=src:.`. On PowerShell use `$env:PYTHONPATH='src;.'`. Install training dependencies with `python -m pip install -r requirements-resolved.txt --extra-index-url https://download.pytorch.org/whl/cpu`. Install the inference-only set with `python -m pip install -r requirements-serve.txt`. Run `python -m pip check`.

Run `python -m unittest discover -s tests`. On the restricted Windows workspace, run `./deploy/test-local.ps1`. These instrument checks do not prove model quality. PostgreSQL fault checks run only against the explicitly ephemeral CI service in .github/workflows/faults.yml. Never point that fixture initializer at the live project.

For a new experiment, capture and prepare with `python -m hardcase.mining.prepare`. Review the complete source, split, purge, schedule and teacher receipts before freezing requests/train.json. Keep data/vault out of the training worker. Run `python -m hardcase.training.run` for all registered arms. To resume an interrupted arm, use `python -m hardcase.training.run --arm ARM --resume artifacts/training/ARM/checkpoint-UPDATE`; preserve the original attempt and require the same identity.

Run `python -m hardcase.export.build` after the full selection manifest exists. Freeze the resulting export selection before final evaluation. Package assets with `python deploy/preserve_training.py` from the bounded worker environment. Its output hash inventory is retained with the release assets. A prerelease artifact tag is not a product release.

Retain exact input archives using .github/workflows/retain.yml. Verify archive SHA256 against requests/retain.json before extraction. Train and test archives are distinct. Retained notices identify their source and retrieval date.

To assemble the API, create requests/runtime.json only from observed export and release assets. It must contain release_tag, asset_sha256, export_id and variant. Run `python deploy/package_runtime.py` in a clean build. It verifies the fixed repository asset, safe archive members, bundle hashes and startup probes. Use only the base and chosen candidate under the measured memory envelope. Activate the reviewed FastAPI entry only after the package is verified. The health scaffold remains explicitly not ready until then.

Provide DATABASE_URL with TLS through protected deployment settings and OPERATOR_TOKEN through a protected operator workflow. Never place either in a command argument, source file, artifact or chat. The current Vercel credential transfer requires explicit user approval because automatic approval review rejected that secret disclosure. Do not work around the rejection through another transport.

After deployment, verify /readyz, submit distinct fresh experimental queries from browser and separate HTTP client, and independently read matching database receipts. Capture current deployment/bundle identity. Only then bind the pretest receipt digest in requests/evaluate.json and run `python -m evaluation.run`. Do not execute test evaluation to fill a live-serving gap.

Serve the site with `npm ci`, `npm run build` and `npm run preview` inside site. The workflow generates site/public/evidence.json from retained source artifacts. An absent PUBLIC_API_URL must remain visibly unavailable. The site stores only the theme preference; session capabilities stay in memory.

For promotion, follow .agents/skills/promote-model-bundle/SKILL.md. Prepare a concrete immutable report and proposal. A failed gate keeps the base default. For rollback, activate a retained verified bundle with a new generation and verify a new request plus separate DB observation. Never delete release history to simulate rollback.

Regenerate RESULTS.md with `python -m hardcase.claims`. Include the observed run IDs, model/asset digests, completion state and any approval blocker. Keep prepared, running, failed and completed states distinct.

Before cleanup, resolve absolute paths and confirm they are inside this checkout or an explicitly named disposable directory. Never remove another daily project or a shared schema. Preserve frozen input assets, selected model assets, raw rankings, notices, source commits and terminal manifests before removing reproducible caches.
