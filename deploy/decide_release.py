"""Assemble a refusal or eligible proposal from content-bound observed evidence.

This command never promotes an alias. Missing evidence remains missing.
"""
from pathlib import Path
from hardcase.contracts import atomic_json, digest, load_json, require, utcnow
from hardcase.registry.gates import release_gate


def decide(config, sources):
    selection=sources.get('selection',{})
    exported=sources.get('export',{})
    study=sources.get('evaluation',{})
    live=sources.get('live',{})
    serving=sources.get('serving',{})
    candidate=selection.get('candidate',{}).get('arm')
    variant=exported.get('variant')
    target=exported.get('validation',{}).get(variant,{}).get('bundle_id')
    for name,identity in (('selection','selection_id'),('export','export_id'),('evaluation','report_digest')):
        source=sources.get(name,{})
        if source:
            require(digest({k:v for k,v in source.items() if k!=identity})==source.get(identity),'CHANGED_'+name.upper()+'_CONTENT')
    if exported:
        require(exported.get('selection_id')==selection.get('selection_id'),'RELEASE_SELECTION_MISMATCH')
    if study:
        require(study.get('selection_id')==selection.get('selection_id') and study.get('export_id')==exported.get('export_id') and study.get('candidate')==candidate,'RELEASE_EVALUATION_MISMATCH')
    if live:
        require(live.get('bundle_id')==target,'RELEASE_LIVE_BUNDLE_MISMATCH')
    if serving:
        require(serving.get('bundle_id')==target and serving.get('origin')=='public_production','RELEASE_SERVING_SCOPE_MISMATCH')
        require(serving.get('deployment_ids')==[live.get('deployment_id')],'RELEASE_SERVING_DEPLOYMENT_MISMATCH')
    runs=sources.get('runs',{})
    complete_arms=len(runs)==len(config['arms']) and all(runs.get(arm,{}).get('status')=='completed' and runs[arm].get('actual_updates')==config['optimizer_updates'] and runs[arm].get('examples')==config['optimizer_updates']*config['microbatch_queries']*config['accumulation_steps'] for arm in config['arms'])
    base_validation=sources.get('preparation',{}).get('baseline_validation',{}).get('base_encoder')
    candidate_validation=selection.get('candidate',{}).get('ndcg10')
    parity=exported.get('parity',{}).get('candidate_float32',{})
    float_ok=parity.get('status')=='completed' and parity.get('token_parity') is True and bool(parity.get('max_abs_errors')) and bool(parity.get('cosine_distances')) and max(parity['max_abs_errors'])<=config['export']['max_abs_error'] and max(parity['cosine_distances'])<=config['export']['max_cosine_distance']
    methods={r['method']:r for r in study.get('methods',[])}
    all_methods=['bm25','base_encoder']+config['arms']
    heldout=study.get('status')=='completed' and study.get('main_completed_rows')==study.get('main_planned_rows')==5*config['expected']['test_queries'] and set(methods)==set(all_methods) and all(r.get('completed_queries')==r.get('planned_queries')==config['expected']['test_queries'] for r in methods.values())
    interval=study.get('primary',{}).get('estimate') or {}
    candidate_recall=methods.get(candidate,{}).get('recall100')
    base_recall=methods.get('base_encoder',{}).get('recall100')
    public_complete=serving.get('status')=='completed' and serving.get('planned')==serving.get('completed')==12 and serving.get('warm_denominator')==10
    observed={'three_arms_complete':complete_arms,'validation_gain':candidate_validation-base_validation if candidate_validation is not None and base_validation is not None else None,'float32_parity':float_ok,'heldout_complete':heldout,'test_gain':interval.get('mean_difference') if heldout else None,'interval_lower':interval.get('lower') if heldout else None,'recall100_change':candidate_recall-base_recall if heldout and candidate_recall is not None and base_recall is not None else None,'warm_p95_ms':serving.get('warm_p95_ms') if public_complete else None,'peak_rss_mib':serving.get('peak_rss_mib') if public_complete else None,'live_bundle_verified':live.get('status')=='verified' and all(live.get(k) is True for k in ('learned_fresh_browser','learned_fresh_client','independent_db_match'))}
    decision=release_gate(observed,config['promotion'])
    decision.update(namespace='scripted_release',model_execution=False,bundle_id=target,candidate=candidate,variant=variant,decision='eligible_for_authorized_promotion' if decision['passed'] else 'candidate_refused_default_remains_baseline',default_model='Pretrained baseline',source_digests={k:digest(v) for k,v in sources.items()},observed=observed,created_at=utcnow())
    decision['decision_digest']=digest(decision)
    return decision


def main():
    paths={'selection':'evidence/training/selection.json','export':'evidence/export/selection.json','evaluation':'evidence/evaluation/report.json','live':'evidence/live/pretest.json','serving':'evidence/serving/public-smoke.json','preparation':'evidence/preparation/prepare.json'}
    sources={name:load_json(path) for name,path in paths.items() if Path(path).exists()}
    config=load_json('requests/experiment.json')
    sources['runs']={arm:load_json(f'evidence/training/{arm}/run.json') for arm in config['arms'] if Path(f'evidence/training/{arm}/run.json').exists()}
    atomic_json('evidence/release/decision.json',decide(config,sources))


if __name__=='__main__':
    main()
