"""Restore frozen evaluation inputs only after independent live evidence is admitted."""
import re
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile
from hardcase.contracts import atomic_json,digest,file_digest,load_json,require
from deploy.package_runtime import safe_unpack


def download(tag,names,destination):
    require(re.fullmatch(r'(input|training)-assets-[0-9]+',tag) is not None,'UNAPPROVED_ASSET_TAG')
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    command=['gh','release','download',tag,'--dir',str(destination)]
    for name in names:command.extend(['--pattern',name])
    subprocess.run(command,check=True)


def run():
    request=load_json('requests/evaluate.json')
    live=load_json('evidence/live/pretest.json')
    require(live.get('status')=='verified' and all(live.get(k) is True for k in ('learned_fresh_browser','learned_fresh_client','independent_db_match')) and digest(live)==request['pretest_live_digest'],'PRETEST_LIVE_EVIDENCE_MISSING')
    runtime=load_json('requests/runtime.json')
    require(runtime['export_id']==request['export_id'],'RUNTIME_EVALUATION_FREEZE_CHANGED')
    selection=load_json('evidence/training/selection.json')
    require(selection['selection_id']==request['selection_id'] and digest({k:v for k,v in selection.items() if k!='selection_id'})==selection['selection_id'],'SELECTED_CHECKPOINTS_CHANGED')
    download('input-assets-42109854166',['train-inputs.zip','test-vault.zip'],'artifacts/downloads/inputs')
    retained=load_json('requests/retain.json')
    for name,expected in retained['assets'].items():
        require(file_digest(Path('artifacts/downloads/inputs')/name)==expected,'INPUT_HASH_CHANGED')
    with ZipFile('artifacts/downloads/inputs/train-inputs.zip') as archive:archive.extractall('.')
    with ZipFile('artifacts/downloads/inputs/test-vault.zip') as archive:archive.extractall('data/vault')
    names=[r['arm']+'.tar.gz' for r in selection['arms']]
    download('training-assets-42113390181',names+['delivery.json'],'artifacts/downloads/checkpoints')
    original=load_json('artifacts/downloads/checkpoints/delivery.json')
    require(original['selection_id']==selection['selection_id'],'TRAINING_DELIVERY_CHANGED')
    for name in names:
        asset=next(a for a in original['assets'] if a['name']==name)
        path=Path('artifacts/downloads/checkpoints')/name
        require(file_digest(path)==asset['sha256'],'CHECKPOINT_ASSET_CHANGED')
        safe_unpack(path,'.')
    download(runtime['release_tag'],['serving-bundles.tar.gz','delivery.json'],'artifacts/downloads/serving')
    archive=Path('artifacts/downloads/serving/serving-bundles.tar.gz')
    require(file_digest(archive)==runtime['asset_sha256'],'SERVING_ASSET_CHANGED')
    safe_unpack(archive,'.')
    exported=load_json('artifacts/export/selection.json')
    require(exported['export_id']==request['export_id'] and exported['variant']==runtime['variant'] and exported['selection_id']==selection['selection_id'],'RESTORED_EXPORT_CHANGED')
    atomic_json('artifacts/training/selection.json',selection)
    atomic_json('artifacts/evaluation-restoration.json',{'selection_id':selection['selection_id'],'export_id':exported['export_id'],'serving_release_tag':runtime['release_tag'],'pretest_live_digest':request['pretest_live_digest'],'status':'restored_after_live_gate'})


if __name__=='__main__':
    run()
