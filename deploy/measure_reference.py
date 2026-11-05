"""Post-freeze matched timing audit. Never changes the selected serving variant."""
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from hardcase.contracts import atomic_json, digest, file_digest, load_json, require, utcnow
from hardcase.training.encoder import load_encoder, encode, parameter_hashes
from hardcase.mining.retrieval import exact_search
from deploy.package_runtime import safe_unpack


def torch_measure():
    import psutil
    import torch
    torch.set_num_threads(2)
    selection=load_json('artifacts/training/selection.json')
    candidate=selection['candidate']
    documents=load_json('data/processed/documents.json')
    queries=load_json('artifacts/export/timing-queries.json')
    timer=time.perf_counter()
    model,tokenizer=load_encoder(Path(candidate['checkpoint'])/'encoder')
    require(digest(parameter_hashes(model))==candidate['state_digest'],'REFERENCE_STATE_CHANGED')
    load_ms=(time.perf_counter()-timer)*1000
    ids=sorted(documents)
    matrix=encode(model,tokenizer,[documents[d]['visible_text'] for d in ids],256,receipt_path='evidence/serving/reference-corpus-encoding.json',identity=candidate['state_digest'])
    process=psutil.Process()
    peak=process.memory_info().rss
    rows=[]
    for q in queries[:3]:encode(model,tokenizer,[q['text']],256)
    for repeat in range(5):
        for q in queries:
            started=time.perf_counter()
            vector=encode(model,tokenizer,[q['text']],256)[0]
            encoding_ms=(time.perf_counter()-started)*1000
            search_start=time.perf_counter()
            ranked=exact_search(vector,matrix,ids,10)
            results=[{'id':d,'title':documents[d]['title'],'score':float(score),'visible_text':documents[d]['visible_text'],'truncated':documents[d]['truncated']} for d,score in ranked]
            search_ms=(time.perf_counter()-search_start)*1000
            serialization_start=time.perf_counter()
            json.dumps(results,allow_nan=False)
            serialization_ms=(time.perf_counter()-serialization_start)*1000
            rows.append({'query_id':q['id'],'repeat':repeat,'encoding_ms':encoding_ms,'search_ms':search_ms,'serialization_ms':serialization_ms,'total_ms':(time.perf_counter()-started)*1000})
            peak=max(peak,process.memory_info().rss)
    import resource
    peak=max(peak,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    atomic_json('evidence/serving/torch-reference.json',{'namespace':'serving_measurement','method':'selected_pytorch_parent','state_digest':candidate['state_digest'],'query_digest':digest(queries),'cold_load_ms':load_ms,'peak_rss_mib':peak/1024**2,'observations':rows,'queries':len(queries),'repeats':5,'threads':2,'platform':platform.platform(),'observed_at':utcnow(),'purpose':'Post-freeze matched reference audit; serving selection unchanged.'})
    teacher_diagnostic(model,tokenizer,matrix,ids)


def teacher_diagnostic(model,tokenizer,matrix,ids):
    from hardcase.training.loss import validate_candidate_alignment
    queries=load_json('data/processed/train-queries.json')
    lists=load_json('data/processed/candidates.json')
    scores=load_json('data/processed/teacher-scores.json')
    frozen=load_json('data/manifests/preparation.json')
    require(digest(lists)==frozen['candidate_digest'] and digest(scores)==frozen['teacher_digest'],'DIAGNOSTIC_FROZEN_LIST_CHANGED')
    audit=load_json('artifacts/preparation/mining-audit.json')
    query_ids=sorted({row['query_id'] for row in audit})
    row_index={d:i for i,d in enumerate(ids)}
    observations=[]
    started=utcnow()
    for query_id in query_ids:
        positive=sorted(lists[query_id]['positives'])[0]
        candidates=[positive]+[r['id'] for r in lists[query_id]['hard']]
        record=scores[query_id+':'+positive]
        validate_candidate_alignment(candidates,lists[query_id]['positives'],record)
        vector=encode(model,tokenizer,[queries[query_id]['text']],256)[0]
        student=[float(matrix[row_index[d]]@vector) for d in candidates]
        comparable,concordant,ties=0,0,0
        for i in range(len(candidates)):
            for j in range(i+1,len(candidates)):
                left=student[i]-student[j]
                right=record['scores'][i]-record['scores'][j]
                if left==0 or right==0:ties+=1
                else:
                    comparable+=1
                    concordant+=int(left*right>0)
        observations.append({'query_id':query_id,'candidate_ids':candidates,'teacher_scores':record['scores'],'student_cosines':student,'comparable_pairs':comparable,'concordant_pairs':concordant,'ties_excluded':ties,'pair_agreement':concordant/comparable if comparable else None})
    denominator=sum(r['comparable_pairs'] for r in observations)
    atomic_json('evidence/serving/teacher-agreement.json',{'namespace':'teacher_supervision','split':'fit audit lists; training-exposed diagnostic','queries':len(query_ids),'candidate_lists_digest':digest(lists),'teacher_scores_digest':digest(scores),'selection_rule':'Distinct queries in the frozen preparation audit; lexicographically first known positive per query','observations':observations,'comparable_pairs':denominator,'pair_agreement':sum(r['concordant_pairs'] for r in observations)/denominator if denominator else None,'started_at':started,'ended_at':utcnow(),'interpretation':'Agreement with weak teacher supervision only. This is neither held-out relevance nor independent quality.'})


def run():
    delivery=load_json('artifacts/downloads/delivery.json')
    with urllib.request.urlopen('https://raw.githubusercontent.com/mekala27-45/hardcase/results/training-42113390181/evidence/training/selection.json',timeout=30) as response:
        selection=json.load(response)
    require(selection['selection_id']==delivery['selection_id'] and digest({k:v for k,v in selection.items() if k!='selection_id'})==selection['selection_id'],'REFERENCE_SELECTION_CHANGED')
    atomic_json('artifacts/training/selection.json',selection)
    arm=selection['candidate']['arm']
    require(arm in load_json('requests/experiment.json')['arms'],'UNKNOWN_REFERENCE_ARM')
    asset=next(r for r in delivery['assets'] if r['name']==arm+'.tar.gz')
    target=Path('artifacts/downloads')/asset['name']
    with urllib.request.urlopen('https://github.com/mekala27-45/hardcase/releases/download/training-assets-42113390181/'+asset['name'],timeout=60) as response, target.open('wb') as stream:
        total=0
        while chunk:=response.read(1024*1024):
            total+=len(chunk)
            require(total<1024**3,'REFERENCE_ASSET_LIMIT')
            stream.write(chunk)
    require(file_digest(target)==asset['sha256'],'REFERENCE_ASSET_CHANGED')
    safe_unpack(target,'.')
    subprocess.run([sys.executable,__file__,'--torch'],check=True)
    exported=load_json('artifacts/export/selection.json')
    for method in ('candidate_float32','candidate_int8'):
        if method not in exported['bundles']:
            atomic_json('evidence/serving/'+method+'-matched.json',{'status':'unsupported','measurement':None})
            continue
        subprocess.run([sys.executable,'-m','hardcase.inference.measure',exported['bundles'][method],'artifacts/export/timing-queries.json','evidence/serving/'+method+'-matched.json',exported['bundles']['base_float32']],check=True)
    subprocess.run([sys.executable,'deploy/compare_timing.py'],check=True)
    atomic_json('evidence/serving/matched-context.json',{'source_commit':os.getenv('GITHUB_SHA'),'run_id':os.getenv('GITHUB_RUN_ID'),'platform':platform.platform(),'export_id':exported['export_id'],'selected_variant_unchanged':exported['variant'],'timing_inputs_digest':digest(load_json('artifacts/export/timing-queries.json')),'comparison':'Separate fresh processes on the same runner. PyTorch reference and symmetric ONNX variants; no network or database in these timings.'})


if __name__=='__main__':
    torch_measure() if '--torch' in sys.argv else run()
