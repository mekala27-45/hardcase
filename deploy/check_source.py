"""Check tracked text and built assets without echoing possible secret values."""
import json
import os
import re
import subprocess
from pathlib import Path
from hardcase.contracts import atomic_json, require, utcnow

PATTERNS={
 'private_key':re.compile('-----BEGIN '+'(?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'aws_access_key':re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
 'github_credential':re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
 'external_database_password':re.compile(r'postgres(?:ql)?://[^/\s:@]+:[^@\s]+@(?!(?:localhost|127\.0\.0\.1)(?::|/))[^/\s]+'),
 'raw_session_capability':re.compile(r'["\x27]capability["\x27]\s*:\s*["\x27][A-Za-z0-9_-]{40,100}["\x27]')
}
TEXT={'.py','.ts','.tsx','.js','.json','.jsonl','.md','.txt','.yml','.yaml','.html','.css','.toml','.sql'}


def run():
    tracked=subprocess.check_output(['git','ls-files','-z'],text=True).split('\0')
    paths=[Path(p) for p in tracked if p and Path(p).suffix in TEXT and Path(p).is_file()]
    paths.extend(p for p in Path('site/dist').rglob('*') if p.is_file() and p.suffix in TEXT)
    findings=[]
    for path in paths:
        text=path.read_text(encoding='utf-8',errors='strict')
        for name,pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append({'path':str(path),'rule':name})
    report={'status':'passed' if not findings else 'failed','files_checked':len(paths),'findings':findings,'source_commit':os.getenv('GITHUB_SHA','local'),'observed_at':utcnow(),'scope':'Tracked text and existing built site text; no secret values printed; this scan does not certify absence of all possible sensitive content'}
    atomic_json('evidence/verification/source-scan.json',report)
    print(json.dumps({'status':report['status'],'files_checked':len(paths),'findings':findings}))
    require(not findings,'POSSIBLE_SECRET_IN_PUBLISHABLE_TEXT')


if __name__=='__main__':
    run()
