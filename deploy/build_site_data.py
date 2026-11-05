import json
import os
import sys
from pathlib import Path
sys.path.insert(0, "src")
from hardcase.contracts import atomic_json, load_json, digest, file_digest
from hardcase.claims import render_measurement


def existing(path, default=None):
    path = Path(path)
    return load_json(path) if path.exists() else default


def build():
    preparation = existing("evidence/preparation/prepare.json", {})
    source = existing("evidence/preparation/source.json", {})
    selection = existing("evidence/training/selection.json", {})
    evaluation = existing("evidence/evaluation/report.json", {})
    release = existing("evidence/release/decision.json", {})
    arms, steps, parameters, claims = [], [], [], {}
    for arm in ["uniform_contrastive", "hard_contrastive", "hard_distilled"]:
        run = existing(f"evidence/training/{arm}/run.json", {})
        arms.append({"arm": arm, "status": run.get("status", "awaiting_imported_receipts"), "updates": run.get("actual_updates"), "selected_update": run.get("selected", {}).get("update")})
        path = Path(f"evidence/training/{arm}/steps.jsonl")
        if path.exists():
            arm_steps=[json.loads(line) for line in path.read_text().splitlines()]
            steps.extend(arm_steps)
            if arm_steps:
                claim={'kind':'observed','status':'observed','value':sum(row['loss'] for row in arm_steps)/len(arm_steps),'method':arm,'namespace':'actual_training','split':'fit','aggregation':'mean recorded optimizer objective','denominator':len(arm_steps),'unit':'loss','source':str(path).replace('\\','/'),'source_digest':file_digest(path),'started_at':arm_steps[0]['started_at'],'ended_at':arm_steps[-1]['ended_at']}
                claims[arm]={'measurement':claim,'rendered':render_measurement(claim),'title':f"{arm}: mean recorded objective {claim['value']:.4f} over {claim['denominator']} updates"}
        before,after=run.get('before_hashes',{}),run.get('after_hashes',{})
        for name,initial in before.items():
            parameters.append({'arm':arm,'parameter':name,'trainable':name in run.get('trainable_names',[]),'before_digest':initial,'after_digest':after.get(name),'changed':initial!=after[name] if name in after else None})
    result = {"completion_state": "Experiment in progress", "api_url": os.getenv("PUBLIC_API_URL", ""), "default_model": release.get("default_model"), "training": {"arms": arms, "steps": steps}, "evaluation": evaluation, "release": release, "data": {"inventory": [{"item": key, "observed": value, "source": "evidence/preparation/source.json"} for key, value in source.get("observed", {}).items()], "audit": existing("evidence/preparation/mining-audit.json", [])}, "source_digests": {name:file_digest(path) if Path(path).exists() else None for name,path in {"preparation":"evidence/preparation/prepare.json","selection":"evidence/training/selection.json","evaluation":"evidence/evaluation/report.json","release":"evidence/release/decision.json"}.items()}}
    atomic_json("site/public/evidence.json", result)
    for method in result['evaluation'].get('methods',[]):
        method['claims']={}
        if method.get('status')!='completed':
            continue
        for metric in ('ndcg10','recall10','recall100','mrr10'):
            item={'kind':'observed','status':'observed','value':method[metric],'method':method['method'],'namespace':'retrieval_quality','split':'held-out test','aggregation':'mean per-query '+metric,'denominator':method['planned_queries'],'unit':metric,'source':'evidence/evaluation/report.json','source_digest':file_digest('evidence/evaluation/report.json'),'started_at':evaluation['started_at'],'ended_at':evaluation['ended_at']}
            method['claims'][metric]={'measurement':item,'rendered':render_measurement(item)}
        method['claim_title']=method['method']+': '+format(method['ndcg10'],'.4f')+' mean nDCG@10 across '+str(method['planned_queries'])+' test queries'
    result['training'].update(parameters=parameters,claims=claims,selection=selection)
    result['evaluation'].update(paired_rows=existing('evidence/evaluation/paired-rows.json',[]),slices=existing('evidence/evaluation/slices.json',{}),export_drift=existing('evidence/evaluation/export-drift.json',[]),error_details=existing('evidence/evaluation/error-sample.json',[]),timing=existing('evidence/serving/paired-timing.json',{}))
    audit_comments={(r['query_id'],r['document_id']):r for r in existing('evidence/preparation/audit-commentary.json',{}).get('rows',[])}
    for row in result['data']['audit']:
        note=audit_comments.get((row['query_id'],row['document_id']))
        if note:row['review']='Assistant semantic inspection, not human expert adjudication. '+note['comment']
    result['data']['groups']=existing('evidence/preparation/split.json',{})
    result['data']['purge']=existing('evidence/preparation/purge.json',{})
    result['release']['faults']=existing('evidence/faults/runtime-transactions.json',existing('evidence/faults/postgres.json',{})).get('cases',[])+existing('evidence/faults/actual-bundles.json',{}).get('cases',[])
    result['claim_context']={'data':{'source':'evidence/preparation/source.json','source_digest':file_digest('evidence/preparation/source.json'),'namespace':'data_inventory','method':'frozen_preparation','split':'source inventory','aggregation':'verified counts','denominator':1,'unit':'documents/queries/qrel rows','started_at':preparation.get('started_at'),'ended_at':preparation.get('ended_at')}} if source else {}
    result['statement'] = ' '.join(Path('docs/STATEMENT.txt').read_text().split())
    atomic_json("site/public/evidence.json", result)


if __name__ == "__main__":
    build()
