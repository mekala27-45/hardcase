"""Publish the requested product tag only after retained evidence and exact-commit CI."""
import json
import os
import re
import subprocess
import time
from pathlib import Path
from hardcase.contracts import digest, load_json, require
from deploy.refresh_completion import run as refresh


def gh(*args):
    return json.loads(subprocess.check_output(['gh',*args],text=True))


def run():
    request=load_json('requests/publish.json')
    require(request['tag']=='v0.2.0','UNREGISTERED_PRODUCT_TAG')
    sha=os.environ['GITHUB_SHA']
    repository=os.environ['GITHUB_REPOSITORY']
    require(repository=='mekala27-45/hardcase' and re.fullmatch('[0-9a-f]{40}',sha),'UNEXPECTED_RELEASE_SOURCE')
    study=load_json('evidence/evaluation/report.json')
    audit=load_json('evidence/evaluation/independent-audit.json')
    decision=load_json('evidence/release/decision.json')
    require(study['report_digest']==request['report_digest'] and digest(audit)==request['audit_digest'] and decision['decision_digest']==request['decision_digest'],'RELEASE_INPUT_CHANGED')
    refresh()
    checklist=load_json('evidence/completion.json')
    require(all(checklist[str(i)]['verified'] is True for i in range(1,18)),'CORE_EVIDENCE_INCOMPLETE')
    required={'.github/workflows/ci.yml','.github/workflows/site.yml'}
    ready=False
    for _ in range(90):
        runs=gh('api',f'repos/{repository}/actions/runs?head_sha={sha}&event=push&per_page=100')['workflow_runs']
        observed={}
        for workflow in runs:
            if workflow['path'] in required:
                observed.setdefault(workflow['path'],workflow)
        if required<=observed.keys() and all(row['status']=='completed' for row in observed.values()):
            require(all(row['conclusion']=='success' for row in observed.values()),'EXACT_COMMIT_CHECK_FAILED')
            ready=True
            break
        time.sleep(10)
    require(ready,'EXACT_COMMIT_CHECK_TIMEOUT')
    # No retagging, replacement or publication of an existing name.
    existing=subprocess.run(['gh','release','view',request['tag'],'--json','tagName'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    require(existing.returncode!=0,'PRODUCT_RELEASE_ALREADY_EXISTS')
    notes=Path('artifacts/product-release-notes.md')
    notes.parent.mkdir(parents=True,exist_ok=True)
    notes.write_text('Hardcase adds a verified paired retrieval workbench with bounded suites, rank changes, receipt readbacks, cancellation and privacy-conscious diagnostic exports. The reciprocal-rank fusion preview is browser-only and has no relevance claim.\n\nThe first frozen held-out study and independent ranking audit are retained in evidence/evaluation. Full results, uncertainty, failed historical attempts and scope limits remain in the repository. The accepted serving variant stays float32; later INT8 execution does not erase earlier portability failures.\n\nThe public demo is available at https://mekala27-45.github.io/hardcase/#compare . The pretrained baseline remains the default. This code release grants no model promotion or operator authority.\n\nExact-commit contract CI and Pages build/tests/deployment passed before this tag. See RESULTS.md and docs/COMPARISON.md.\n',encoding='utf-8')
    subprocess.run(['gh','release','create',request['tag'],'--target',sha,'--title','Hardcase v0.2.0: verified retrieval diagnostics','--notes-file',str(notes)],check=True)


if __name__=='__main__':
    run()
