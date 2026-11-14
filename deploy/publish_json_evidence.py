"""Publish only result JSON onto a current source tree, without reverting workflows."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def git(*args,cwd=None):
    return subprocess.run(['git',*args],cwd=cwd,check=True)


def run(prefix,arguments):
    root=Path.cwd().resolve()
    branch=os.environ['GITHUB_REF_NAME']
    run_id=os.environ['GITHUB_RUN_ID']
    if branch not in {'main','build/day27-evidence-completion'} or not re.fullmatch(r'[a-z-]+',prefix) or not run_id.isdigit():
        raise ValueError('UNAPPROVED_RESULT_DESTINATION')
    files={}
    for argument in arguments:
        source=(root/argument).resolve()
        if not source.is_relative_to(root) or not (argument.startswith('evidence/') or argument=='requests/runtime.json'):
            raise ValueError('UNAPPROVED_RESULT_SOURCE')
        if not source.exists():continue
        candidates=source.rglob('*') if source.is_dir() else [source]
        for path in candidates:
            if path.is_file() and path.suffix in {'.json','.jsonl'}:
                if not path.resolve().is_relative_to(root) or path.stat().st_size>10*1024**2:
                    raise ValueError('UNSAFE_RESULT_FILE')
                relative=str(path.relative_to(root))
                files[relative]=path.read_text()
    if not files:raise ValueError('NO_RESULT_FILES')
    for path,content in files.items():
        print('HARDCASE_EVIDENCE_FILE='+json.dumps({'path':path,'content':content}),flush=True)
    git('fetch','origin',branch)
    with tempfile.TemporaryDirectory(prefix='hardcase-result-publisher-') as temporary:
        checkout=Path(temporary)/'checkout'
        git('worktree','add','--detach',str(checkout),'origin/'+branch)
        git('switch','-c','results/'+prefix+'-'+run_id,cwd=checkout)
        for relative,content in files.items():
            target=checkout/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(content,encoding='utf-8',newline='\n')
        git('config','user.name','Ajay Mekala',cwd=checkout)
        git('config','user.email','mekalaajayk@gmail.com',cwd=checkout)
        git('add','--',*files,cwd=checkout)
        git('commit','-m','evidence: preserve observed '+prefix+' results from '+os.environ['GITHUB_SHA'],cwd=checkout)
        git('push','origin','HEAD',cwd=checkout)


if __name__=='__main__':
    run(sys.argv[1],sys.argv[2:])
