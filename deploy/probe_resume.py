"""Real encoder state restoration on authored probe text, outside benchmark arms."""
import argparse
import os
import random
import subprocess
import sys
from pathlib import Path
from hardcase.contracts import atomic_json, digest, load_json, require
from hardcase.training.encoder import load_encoder, download_locked, pool, freeze_policy, parameter_hashes
from hardcase.training.checkpoint import save_checkpoint, load_checkpoint
from hardcase.training.loss import objective


def worker(mode, root):
    import numpy as np
    import torch
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(2701)
    np.random.seed(2701)
    random.seed(2701)
    model, tokenizer = load_encoder(download_locked('student'))
    names = freeze_policy(model)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=2e-5, weight_decay=.01)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step: 1.0)
    identity = {'mode':'resume_probe_not_benchmark','seed':2701,'trainable_names':names,'model_lock':digest(load_json('requests/model-lock.json'))}
    start = 0
    if mode == 'resumed':
        start, cursor = load_checkpoint(root/'checkpoint-1', identity, model, optimizer, scheduler)
        require(cursor == 1 and start == 1,'RESUME_CURSOR_WRONG')
    model.train()
    for update in range(start,2):
        texts = ['An authored study observed a treatment effect.', 'The authored trial measured a treatment effect.', 'A separate invented paper describes rocks.']
        batch = tokenizer(texts, padding=True, truncation=True, max_length=256, return_tensors='pt')
        vectors = pool(model,batch)
        logits = (vectors[:1]*vectors[1:]).sum(-1).unsqueeze(0)/.05
        loss,_,_ = objective(logits,torch.tensor([[True,False]]))
        loss.backward()
        torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1.)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        if mode == 'interrupted' and update == 0:
            save_checkpoint(root/'checkpoint-1',model,tokenizer,optimizer,scheduler,1,1,identity)
            os._exit(73)
    atomic_json(root/f'{mode}.json', {'parameter_hashes':parameter_hashes(model),'rng_digest':digest(torch.get_rng_state().tolist()),'scheduler':scheduler.state_dict(),'updates':2})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['continuous','interrupted','resumed'])
    args=parser.parse_args()
    root=Path('artifacts/resume-probe')
    root.mkdir(parents=True,exist_ok=True)
    if args.mode:
        return worker(args.mode,root)
    for mode in ('continuous','interrupted','resumed'):
        result=subprocess.run([sys.executable,__file__,'--mode',mode])
        require(result.returncode == (73 if mode=='interrupted' else 0),'RESUME_PROBE_CHILD_FAILED')
    left,right=load_json(root/'continuous.json'),load_json(root/'resumed.json')
    require(left==right,'NEW_PROCESS_RESUME_DIVERGED')
    atomic_json('evidence/resume/probe.json',{'status':'passed','namespace':'actual_training','purpose':'authored-text state restoration probe, not benchmark arm results','source_commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),'continuous_digest':digest(left),'resumed_digest':digest(right),'exact_parameter_hash_equality':True,'rng_equal':True,'interrupted_exit_code':73})


if __name__=='__main__':
    main()
