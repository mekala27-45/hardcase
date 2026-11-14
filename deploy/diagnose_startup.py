"""Observe cross-runner startup drift without relaxing bundle admission."""
import os
import platform
from pathlib import Path
import numpy as np
from hardcase.contracts import atomic_json, load_json, utcnow
from hardcase.inference.bundle import Bundle


def run():
    rows=[]
    for method in ('base_float32','candidate_float32','candidate_int8'):
        root=Path('artifacts/bundles')/method
        if not root.exists():
            rows.append({'method':method,'status':'unavailable'})
            continue
        try:
            bundle=Bundle(root,startup_probe=False)
            probe=load_json(root/'probe.json')
            observed=bundle.encode(probe['texts'])
            expected=np.asarray(probe['vectors'])
            errors=np.max(np.abs(observed-expected),axis=1)
            cosine=1-np.sum(observed*expected,axis=1)
            rows.append({'method':method,'bundle_id':bundle.id,'status':'measured','probe_max_abs_errors':errors.tolist(),'probe_cosine_distances':cosine.tolist(),'required_max_abs_error':probe['max_abs_error'],'startup_passed':bool(np.max(errors)<=probe['max_abs_error']),'cpu_provider':bundle.session.get_providers()})
            del bundle
        except Exception as error:
            rows.append({'method':method,'status':'failed','error':str(error)[:300]})
    cpu=Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists() else ''
    result={'namespace':'export_parity','purpose':'Diagnostic only; startup refusal remains enforced. No change to frozen model, vectors or tolerances.','platform':platform.platform(),'cpu_model':next((s.split(':',1)[1].strip() for s in cpu.splitlines() if s.startswith('model name')),None),'source_commit':os.getenv('GITHUB_SHA'),'run_id':os.getenv('GITHUB_RUN_ID'),'observed_at':utcnow(),'rows':rows}
    atomic_json('evidence/runtime/startup-diagnostic.json',result)
    print(result)


if __name__=='__main__':
    run()
