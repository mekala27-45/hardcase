"""Generate public numeric prose from validated source artifacts only."""
from pathlib import Path
from hardcase.contracts import atomic_json, digest, file_digest, load_json, require
from hardcase.claims import render_measurement, render_results


def observation(value, method, namespace, split, aggregation, denominator, unit, path, started, ended):
    return {'kind':'observed','status':'observed','value':value,'method':method,'namespace':namespace,'split':split,'aggregation':aggregation,'denominator':denominator,'unit':unit,'source':path,'source_digest':file_digest(path),'started_at':started,'ended_at':ended}


def write(path, text):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')


def current_state():
    live_path=Path('evidence/live/pretest.json')
    study_path=Path('evidence/evaluation/report.json')
    live=load_json(live_path) if live_path.exists() else {}
    text='Public learned search has verified browser, separate-client and independent database receipts. The baseline remains the default; public sessions cannot promote or roll back a model. See [live deployment evidence](docs/LIVE-DEPLOYMENT.md). ' if live.get('status')=='verified' else 'Public learned inference remains unverified. '
    if study_path.exists():
        study=load_json(study_path)
        require(digest({k:v for k,v in study.items() if k!='report_digest'})==study['report_digest'],'CHANGED_EVALUATION_REPORT')
        text+='The first frozen held-out attempt is '+study['status']+'. Missing export rows remain missing. Its original rankings and independent regrading are in [evaluation evidence](evidence/evaluation/). '
    elif Path('requests/evaluate.json').exists():
        text+='The frozen held-out evaluation has been requested. No final test quality claim is made until its retained report and independent audit are available. '
    else:
        text+='Final held-out evaluation has not executed. '
    return text+'Training, evaluation, public runtime checks and exploratory comparisons remain separate evidence.'


def main():
    statement=Path('docs/STATEMENT.txt').read_text().strip()
    prep=load_json('evidence/preparation/prepare.json')
    lock=load_json('requests/model-lock.json')
    config=load_json('requests/experiment.json')
    measurements=[]
    for field,split,unit in [('corpus_documents','corpus','documents'),('fit_queries','fit','queries'),('validation_queries','validation','queries'),('purged_queries','leakage_audit','queries')]:
        measurements.append(observation(prep['frozen'][field],'frozen_preparation','data_inventory',split,'verified inventory',1,unit,'evidence/preparation/prepare.json',prep['started_at'],prep['ended_at']))
    for method,score in prep['baseline_validation'].items():
        measurements.append(observation(score,method,'retrieval_quality','validation','mean nDCG@10',prep['frozen']['validation_queries'],'nDCG@10','evidence/preparation/prepare.json',prep['started_at'],prep['ended_at']))
    teacher=load_json('evidence/preparation/teacher-receipt.json')
    measurements.append(observation(teacher['pairs'],'cross_encoder','teacher_supervision','fit','executed pair count',1,'pairs','evidence/preparation/teacher-receipt.json',teacher['started_at'],teacher['ended_at']))
    rendered='\n\n'.join(render_measurement(m) for m in measurements)
    atomic_json('evidence/claims/preparation.json',measurements)
    readme='# Hardcase\n\n'+statement+'\n\nA controlled study of selective retrieval-encoder fine-tuning, mined weak negatives and teacher distillation, with an inspectable ONNX serving path.\n\n[Open the workbench](https://mekala27-45.github.io/hardcase/) | [Completion evidence](RESULTS.md) | [Specification](docs/SPEC.md) | [Operations](OPERATIONS.md)\n\n## Current execution state\n\n'+current_state()+'\n\n[Actual training workflow](https://github.com/mekala27-45/hardcase/actions/runs/42113390181)\n\n## Observed preparation\n\n'+rendered+'\n\n## Reproduction\n\nRead OPERATIONS.md before executing a stage. Frozen inputs are retained under [input-assets-42109854166](https://github.com/mekala27-45/hardcase/releases/tag/input-assets-42109854166); verify requests/retain.json hashes before use. The test vault is excluded from training. Selected model assets and independent rankings are linked only after their runs complete.\n\n## Limits\n\nThis is a portfolio project, not employment experience or a medical product. The teacher is weak supervision. Published qrels can be incomplete, pretrained exposure is unknown and a single seed does not establish training stability. A completed negative result is valid.\n\n## Rights\n\nSource code is MIT licensed. Dataset and model rights remain separate; see THIRD_PARTY_NOTICES.md.\n'
    readme+='\n## Paired diagnostic workbench\n\nThe [Compare view](https://mekala27-45.github.io/hardcase/#compare) runs bounded, serial baseline/candidate pairs with alias snapshots, persisted receipt verification and explicit failure states. It shows shared documents, rank changes and a browser-only reciprocal-rank fusion preview. Downloadable reports omit raw query text and credentials. These unlabeled diagnostics do not alter the frozen study, select a checkpoint or establish quality. See [the comparison guide](docs/COMPARISON.md).\n'
    study=load_json('evidence/evaluation/report.json') if Path('evidence/evaluation/report.json').exists() else {}
    if study:
        readme+='\n## First frozen held-out result\n\n'
        for row in study.get('methods',[])+study.get('exports',[]):
            if row['status']!='completed':
                readme+=row['method']+': incomplete; no complete quality estimate.\n\n'
                continue
            for metric in ('ndcg10','recall100'):
                item=observation(row[metric],row['method'],'retrieval_quality','held-out test','mean per-query '+metric,row['planned_queries'],metric,'evidence/evaluation/report.json',study['started_at'],study['ended_at'])
                readme+=render_measurement(item)+'\n\n'
        readme+='The grouped uncertainty interval, all prespecified secondary contrasts, slices, failed exports and error examples remain in the source report. Observed differences do not establish causal explanations or training-seed stability.\n'
        primary=study.get('primary',{}).get('estimate')
        if primary:
            for field,description in [('mean_difference','candidate minus baseline mean nDCG@10'),('lower','grouped 95 percent interval lower bound'),('upper','grouped 95 percent interval upper bound')]:
                readme+='\n'+render_measurement(observation(primary[field],study['candidate'],'retrieval_quality','held-out test',description,primary['queries'],'absolute nDCG@10 change','evidence/evaluation/report.json',study['started_at'],study['ended_at']))+'\n'
        if study.get('secondary') and all(r.get('bh_adjusted_p') is not None and r['bh_adjusted_p']>.05 for r in study['secondary']):
            readme+='\nNone of the prespecified secondary contrasts clears the 0.05 BH-adjusted threshold. This study does not establish an advantage from hard-negative mining over uniform training or from distillation over hard-negative training. The validation-selected candidate remains fixed even when another arm has a higher test mean.\n'
        if any(r['method']=='candidate_int8' and r['status']=='completed' for r in study.get('exports',[])):
            readme+='\nINT8 executed on this evaluation worker. Its earlier failures on other CPU workers remain in compatibility evidence; this successful run neither erases those failures nor changes the pretest float32 serving selection.\n'
    training_path=Path('evidence/training/selection.json')
    if training_path.exists():
        trained=load_json(training_path)
        training_text='\n## Completed training and frozen validation selection\n\nThe selected candidate is '+trained['candidate']['arm']+'. Its checkpoint identity and validation-only selection are retained in [the selection manifest](evidence/training/selection.json). The comparison below uses development validation; it is not held-out quality.\n\n'
        for selected in trained['arms']:
            run_path='evidence/training/'+selected['arm']+'/run.json'
            observed_run=load_json(run_path)
            require(observed_run['status']=='completed','INCOMPLETE_IMPORTED_TRAINING')
            for key,unit,aggregation in [('actual_updates','updates','completed optimizer budget'),('examples','query examples','completed training examples')]:
                item=observation(observed_run[key],selected['arm'],'actual_training','fit',aggregation,1,unit,run_path,observed_run['started_at'],observed_run['ended_at'])
                training_text+=render_measurement(item)+'\n\n'
            item=observation(selected['ndcg10'],selected['arm'],'retrieval_quality','validation','mean selected-checkpoint nDCG@10',selected['query_count'],'nDCG@10',run_path,observed_run['started_at'],observed_run['ended_at'])
            training_text+=render_measurement(item)+'\n\n'
        export_path=Path('evidence/export/export.json')
        if export_path.exists():
            exported=load_json('evidence/export/selection.json')
            window=load_json(export_path)
            training_text+='The serving variant is '+exported['variant']+'. Selection is frozen before test access. Float32 parity and measured INT8 drift are separate records in [parity.json](evidence/export/parity.json); quantization is not an exact-equivalence claim.\n\n'
            for method,result in exported['validation'].items():
                item=observation(result['ndcg10'],method,'retrieval_quality','validation','mean symmetric-export nDCG@10',result['queries'],'nDCG@10','evidence/export/selection.json',window['started_at'],window['ended_at'])
                training_text+=render_measurement(item)+'\n\n'
        readme+=training_text
    write('README.md',readme)
    split=load_json('evidence/preparation/split.json')
    for method in ['base_encoder']+config['arms']:
        path=Path(f'evidence/training/{method}/run.json')
        run=load_json(path) if path.exists() else None
        status='Unchanged pretrained reference' if method=='base_encoder' else run.get('status') if run else 'No imported benchmark training terminal manifest yet'
        text=f'# Model card: {method}\n\n{statement}\n\nStatus: {status}.\n\nBase model: {lock["student"]["repo_id"]}\n\nPinned revision: {lock["student"]["revision"]}\n\nTeacher: {lock["teacher"]["repo_id"]} at {lock["teacher"]["revision"]}. Teacher scores are weak supervision, not evaluation labels.\n\n## Design and data\n\nThe exact planned modules, optimizer, seed, temperatures, update budget, candidate rules and selection policy are in [requests/experiment.json](../requests/experiment.json). Observed grouped development membership is in [the split manifest](../evidence/preparation/split.json). The intended use is fixed-corpus scientific document retrieval. Scores are ranking similarities, not truth probabilities.\n\n'+rendered+'\n\n## Learning evidence\n\n'
        if run and run.get('status')=='completed':
            for key,unit in [('actual_updates','optimizer updates'),('examples','query examples'),('trainable_parameters','parameters')]:
                item=observation(run[key],method,'actual_training','fit','actual completed run',1,unit,str(path).replace('\\','/'),run['started_at'],run['ended_at'])
                text+=render_measurement(item)+'\n\n'
            text+='Selected checkpoint and parameter hashes: ['+str(path).replace('\\','/')+'](../'+str(path).replace('\\','/')+').\n'
        else:
            text+='No benchmark training measurements are asserted here. Setup and resume probes are separate evidence.\n'
        text+='\n## Evaluation and deployment\n\n'+current_state()+'\n\n'
        measured=next((r for r in study.get('methods',[]) if r['method']==method),None)
        if measured and measured['status']=='completed':
            text+=render_measurement(observation(measured['ndcg10'],method,'retrieval_quality','held-out test','mean per-query nDCG@10',measured['planned_queries'],'nDCG@10','evidence/evaluation/report.json',study['started_at'],study['ended_at']))+'\n\n'
        text+='Test qrels may be incomplete, pretrained benchmark exposure is unknown, and one training seed does not demonstrate stability. Source notices are retained separately. Do not describe the teacher as an independent evaluator or this project as foundation-model pretraining.\n'
        write(f'model-cards/{method}.md',text)
    render_results(Path.cwd())


if __name__=='__main__':
    main()
