"""Generate public numeric prose from validated source artifacts only."""
from pathlib import Path
from hardcase.contracts import atomic_json, digest, file_digest, load_json
from hardcase.claims import render_measurement, render_results


def observation(value, method, namespace, split, aggregation, denominator, unit, path, started, ended):
    return {'kind':'observed','status':'observed','value':value,'method':method,'namespace':namespace,'split':split,'aggregation':aggregation,'denominator':denominator,'unit':unit,'source':path,'source_digest':file_digest(path),'started_at':started,'ended_at':ended}


def write(path, text):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')


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
    readme='# Hardcase\n\n'+statement+'\n\nA controlled study of selective retrieval-encoder fine-tuning, mined weak negatives and teacher distillation, with an inspectable ONNX serving path.\n\n[Open the workbench](https://mekala27-45.github.io/hardcase/) | [Completion evidence](RESULTS.md) | [Specification](docs/SPEC.md) | [Operations](OPERATIONS.md)\n\n## Current execution state\n\nThe published interface displays retained evidence. Live learned search has not yet been verified. The production database credential transfer is awaiting explicit approval. Final test evaluation remains closed until the pretest live check passes. Training state is recorded in the linked workflow and imported terminal manifests, not inferred from this description.\n\n[Actual training workflow](https://github.com/mekala27-45/hardcase/actions/runs/42113390181)\n\n## Observed preparation\n\n'+rendered+'\n\n## Reproduction\n\nRead OPERATIONS.md before executing a stage. Frozen inputs are retained under [input-assets-42109854166](https://github.com/mekala27-45/hardcase/releases/tag/input-assets-42109854166); verify requests/retain.json hashes before use. The test vault is excluded from training. Selected model assets and independent rankings are linked only after their runs complete.\n\n## Limits\n\nThis is a portfolio project, not employment experience or a medical product. The teacher is weak supervision. Published qrels can be incomplete, pretrained exposure is unknown and a single seed does not establish training stability. A completed negative result is valid.\n\n## Rights\n\nSource code is MIT licensed. Dataset and model rights remain separate; see THIRD_PARTY_NOTICES.md.\n'
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
        text+='\n## Evaluation and deployment\n\nFinal held-out quality and live serving are not established by this card. See RESULTS.md and the immutable evaluation/release artifacts when available. Test qrels may be incomplete, pretrained benchmark exposure is unknown, and one training seed does not demonstrate stability. Source notices are retained separately. Do not describe the teacher as an independent evaluator or this project as foundation-model pretraining.\n'
        write(f'model-cards/{method}.md',text)
    render_results(Path.cwd())


if __name__=='__main__':
    main()
