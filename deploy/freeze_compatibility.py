"""Prepare a float32 compatibility fallback before test access, preserving every original byte."""
import os
import hashlib
import shutil
import tarfile
from pathlib import Path
from hardcase.contracts import atomic_json,digest,file_digest,load_json,require,utcnow
from hardcase.inference.bundle import Bundle


def run():
    request=load_json('requests/compatibility.json')
    observed=load_json('evidence/runtime/startup-diagnostic.json')
    diagnostic_bytes=Path('evidence/runtime/startup-diagnostic.json').read_bytes()
    require(hashlib.sha1(b'blob '+str(len(diagnostic_bytes)).encode()+b'\0'+diagnostic_bytes).hexdigest()==request['diagnostic_git_blob'],'DIAGNOSTIC_CHANGED')
    rows={r['method']:r for r in observed['rows']}
    require(rows['candidate_int8']['startup_passed'] is False and rows['candidate_float32']['startup_passed'] is True and rows['base_float32']['startup_passed'] is True,'FALLBACK_NOT_SUPPORTED_BY_OBSERVATION')
    require(not Path('data/vault').exists() and not Path('evidence/evaluation/report.json').exists(),'TEST_ALREADY_AVAILABLE')
    original=load_json('artifacts/export/selection.json')
    require(original['variant']=='candidate_int8' and original['export_id']==request['original_export_id'],'ORIGINAL_EXPORT_CHANGED')
    require(digest({k:v for k,v in original.items() if k!='export_id'})==original['export_id'],'ORIGINAL_EXPORT_HASH_CHANGED')
    for method in ('base_float32','candidate_float32'):
        bundle=Bundle(original['bundles'][method])
        require(bundle.id==original['validation'][method]['bundle_id'],'FALLBACK_BUNDLE_CHANGED')
        del bundle
    decision={'namespace':'export_parity','reason':'Frozen INT8 startup vectors failed the original tolerance on an independent runner; use the already-exported float32 parent without changing model or index bytes.','original_variant':'candidate_int8','variant':'candidate_float32','prior_export_id':original['export_id'],'diagnostic_sha256':file_digest('evidence/runtime/startup-diagnostic.json'),'diagnostic_run_id':observed['run_id'],'source_commit':os.getenv('GITHUB_SHA'),'run_id':os.getenv('GITHUB_RUN_ID'),'test_access':False,'created_at':utcnow(),'retraining':False,'tolerance_changed':False}
    atomic_json('artifacts/export/selection-original.json',original)
    updated={k:v for k,v in original.items() if k!='export_id'}
    updated.update(variant='candidate_float32',compatibility_fallback=decision,created_at=decision['created_at'])
    updated['export_id']=digest(updated)
    atomic_json('artifacts/export/selection.json',updated)
    atomic_json('evidence/compatibility/decision.json',decision|{'export_id':updated['export_id']})
    for name in ('selection.json','selection-original.json'):
        atomic_json('evidence/compatibility/'+name,load_json('artifacts/export/'+name))
    package=Path('artifacts/delivery')
    package.mkdir(parents=True,exist_ok=True)
    archive=package/'serving-bundles.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        tar.add('artifacts/bundles',arcname='artifacts/bundles')
        tar.add('artifacts/export',arcname='artifacts/export')
    delivery=load_json('artifacts/downloads/delivery.json')
    for asset in delivery['assets']:
        asset['origin_release_tag']='training-assets-42113390181'
        if asset['name']=='serving-bundles.tar.gz':
            asset.update(bytes=archive.stat().st_size,sha256=file_digest(archive),origin_release_tag='training-assets-'+os.environ['GITHUB_RUN_ID'])
    delivery.update(release_tag='training-assets-'+os.environ['GITHUB_RUN_ID'],status='packaged_compatibility_fallback',original_release_tag='training-assets-42113390181',export_id=updated['export_id'])
    atomic_json(package/'delivery.json',delivery)
    atomic_json('evidence/compatibility/delivery.json',delivery)


if __name__=='__main__':
    run()
