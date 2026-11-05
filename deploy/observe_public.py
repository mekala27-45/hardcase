"""A bounded separate-client smoke check, with fresh request identities.

Runs only after requests/public-smoke.json explicitly names a verified package
and public production URL. It has no database or operator credentials.
"""
import json
import math
import time
import urllib.request
import uuid
from urllib.parse import urlparse
from hardcase.contracts import atomic_json, digest, load_json, require, utcnow
import hashlib


def run():
    request=load_json('requests/public-smoke.json')
    base=request['url'].rstrip('/')
    parsed=urlparse(base)
    require(parsed.scheme=='https' and parsed.hostname in request['approved_hosts'] and parsed.hostname.endswith('.vercel.app') and not parsed.username and parsed.path=='','APPROVED_PRODUCTION_URL_REQUIRED')
    require(request['phase']=='authorized_public_runtime','PUBLIC_RUNTIME_NOT_AUTHORIZED')
    queries=request['queries']
    require(len(queries)==12 and all(isinstance(q,str) and 1<=len(q)<=512 for q in queries),'BOUNDED_SMOKE_INVENTORY_REQUIRED')
    def call(path,payload=None,token=None):
        headers={'Content-Type':'application/json'}
        if token:
            headers['Authorization']='Bearer '+token
            headers['Idempotency-Key']=str(uuid.uuid4())
        command=urllib.request.Request(base+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers,method='POST' if payload is not None else 'GET')
        with urllib.request.urlopen(command,timeout=15) as response:
            return json.load(response)
    ready=call('/readyz')
    require(ready['ready'] and request['candidate_bundle_id'] in ready['bundles'],'PUBLIC_PACKAGE_NOT_READY')
    session=call('/api/v1/sessions',{})['capability']
    rows=[]
    started=utcnow()
    for index,query in enumerate(queries):
        if index:time.sleep(3)
        timer=time.perf_counter()
        try:
            receipt=call('/api/v1/search',{'query':query,'alias':'experimental','top_k':10},session)
            elapsed=(time.perf_counter()-timer)*1000
            require(receipt['status']=='completed' and receipt['fresh'] and not receipt['replayed'],'FRESH_REQUEST_REQUIRED')
            require(receipt['bundle_id']==request['candidate_bundle_id'],'PUBLIC_BUNDLE_CHANGED')
            stored=call('/api/v1/receipts/'+receipt['id'],token=session)
            require(stored==receipt,'PUBLIC_PERSISTENCE_READBACK_MISMATCH')
            row={'status':'completed','index':index,'milliseconds':elapsed,'receipt':receipt,'expected_query_digest':hashlib.sha256(query.encode()).hexdigest(),'persistence_readback':True,'origin':'public_production'}
        except Exception as error:
            row={'status':'failed','index':index,'milliseconds':None,'error':type(error).__name__+': '+str(error)[:180]}
        rows.append(row)
        atomic_json('evidence/live/client-observations.json',{'request_digest':digest(request),'started_at':started,'ended_at':utcnow(),'rows':rows,'planned':12,'status':'in_progress' if len(rows)<12 else 'completed' if all(r['status']=='completed' for r in rows) else 'failed'})
    warm=rows[2:]
    complete=all(row['status']=='completed' for row in rows)
    durations=sorted(row['milliseconds'] for row in warm if row['status']=='completed')
    peaks=[row['receipt']['timings'].get('process_peak_rss_mib') for row in rows if row['status']=='completed']
    atomic_json('evidence/serving/public-smoke.json',{'namespace':'serving_measurement','origin':'public_production','status':'completed' if complete else 'incomplete','bundle_id':request['candidate_bundle_id'],'deployment_ids':sorted({r['receipt']['deployment_id'] for r in rows if r['status']=='completed'}),'planned':12,'completed':sum(r['status']=='completed' for r in rows),'warm_denominator':10,'warm_p95_ms':durations[math.ceil(.95*len(durations))-1] if complete else None,'peak_rss_mib':max(peaks) if complete and all(v is not None for v in peaks) else None,'observations_digest':digest(rows),'started_at':started,'ended_at':utcnow(),'scope':'12 sequential public requests, 3-second spacing, first two excluded from warm timing; network/API/database included; not a load or reliability claim'})


if __name__=='__main__':
    run()
