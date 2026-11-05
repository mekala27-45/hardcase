"""Actual exported bytes, injected corruption, independent verifier processes."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from hardcase.contracts import atomic_json, file_digest, load_json, require


def run():
    package=load_json('runtime/bundles/allowlist.json')
    base=next(r for r in package['bundles'] if r['method']=='base_float32')
    candidate=next(r for r in package['bundles'] if r['method']!='base_float32')
    rows=[]
    for fault,expected in [('corrupt_artifact_hash','CORRUPT'),('model_index_mismatch','MODEL_INDEX_MISMATCH')]:
        with tempfile.TemporaryDirectory(prefix='hardcase-fault-') as temp:
            root=Path(temp)/'candidate'
            shutil.copytree('runtime/bundles/'+candidate['directory'],root)
            if fault=='corrupt_artifact_hash':
                with (root/'model.onnx').open('r+b') as stream:
                    first=stream.read(1)
                    stream.seek(0)
                    stream.write(bytes([first[0]^1]))
            else:
                shutil.copy2('runtime/bundles/'+base['directory']+'/model.onnx',root/'model.onnx')
                manifest=load_json(root/'manifest.json')
                manifest['files']['model.onnx']=file_digest(root/'model.onnx')
                atomic_json(root/'manifest.json',manifest)
            child=subprocess.run([sys.executable,'-c','from hardcase.inference.bundle import Bundle; import sys; Bundle(sys.argv[1])',str(root)],capture_output=True,text=True)
            require(child.returncode!=0 and expected in child.stderr,'FAULT_NOT_REFUSED')
            rows.append({'case':fault,'status':'passed','injected_boundary':'temporary copy of real exported candidate before startup','candidate_bundle':candidate['id'],'base_bundle':base['id'],'independent_observer':'new Python process constructing the full Bundle','child_exit':child.returncode,'observed_code':expected,'served':False})
    atomic_json('evidence/faults/actual-bundles.json',{'namespace':'scripted_release','actual_model_artifacts':True,'cases':rows,'status':'passed'})


if __name__=='__main__':
    run()
