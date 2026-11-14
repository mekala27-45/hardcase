"""Bounded open-loop local API measurement, never a public stress test."""
import concurrent.futures
import json
import math
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from hardcase.contracts import atomic_json, load_json, require, utcnow
from hardcase.registry.postgres import connect

BASE='http://127.0.0.1:8000'


def request(path,payload=None,token=None,key=None):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    if key:headers['Idempotency-Key']=key
    call=urllib.request.Request(BASE+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers,method='POST' if payload is not None else 'GET')
    try:
        with urllib.request.urlopen(call,timeout=15) as response:
            return response.status,json.load(response)
    except urllib.error.HTTPError as error:
        return error.code,json.load(error)


def measure():
    queries=load_json('artifacts/export/timing-queries.json')
    server_pid=int(Path('artifacts/runtime/api.pid').read_text())
    tokens=[]
    for _ in range(4):
        status,body=request('/api/v1/sessions',{})
        require(status==200,'LOCAL_SESSION_FAILED')
        tokens.append(body['capability'])
    rows=[]
    start=time.perf_counter()
    status,cold=request('/api/v1/search',{'query':queries[0]['text'],'alias':'experimental','top_k':10},tokens[0],str(uuid.uuid4()))
    require(status==200 and cold['fresh'] and not cold['replayed'],'LOCAL_FIRST_INFERENCE_FAILED')
    cold_observation={'status':status,'milliseconds':(time.perf_counter()-start)*1000,'receipt':cold,'definition':'first visitor query after startup probe; includes API and local database'}
    for rate in (1,2):
        begin=time.perf_counter()
        active=set()
        def run_one(index,scheduled):
            actual=time.perf_counter()
            try:
                status,body=request('/api/v1/search',{'query':queries[index%len(queries)]['text'],'alias':'experimental','top_k':10},tokens[index%4],str(uuid.uuid4()))
                return {'rate':rate,'index':index,'scheduled_offset_ms':(scheduled-begin)*1000,'scheduler_lag_ms':(actual-scheduled)*1000,'end_to_end_ms':(time.perf_counter()-scheduled)*1000,'status':status,'receipt_id':body.get('id'),'bundle_id':body.get('bundle_id'),'fresh':body.get('fresh'),'replayed':body.get('replayed'),'stages':body.get('timings'),'error':body.get('detail')}
            except Exception as error:
                return {'rate':rate,'index':index,'status':'client_failure','end_to_end_ms':(time.perf_counter()-scheduled)*1000,'error':type(error).__name__}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for index in range(rate*60):
                scheduled=begin+index/rate
                delay=scheduled-time.perf_counter()
                if delay>0:time.sleep(delay)
                finished={future for future in active if future.done()}
                rows.extend(future.result() for future in finished)
                active-=finished
                if len(active)>=4:
                    rows.append({'rate':rate,'index':index,'status':'client_concurrency_refused','end_to_end_ms':None})
                else:
                    active.add(pool.submit(run_one,index,scheduled))
            rows.extend(future.result() for future in active)
    summary=[]
    for rate in (1,2):
        subset=[r for r in rows if r['rate']==rate]
        completed=[r for r in subset if r['status']==200]
        times=sorted(r['end_to_end_ms'] for r in completed)
        summary.append({'requests_per_second':rate,'duration_seconds':60,'scheduled':len(subset),'completed':len(completed),'refused_or_failed':len(subset)-len(completed),'warm_p95_ms':times[math.ceil(.95*len(times))-1] if len(completed)==len(subset) else None,'aggregation':'nearest-rank scheduled-arrival latency; complete denominator required'})
    with connect() as db:
        observed=db.execute('SELECT receipt FROM hardcase.query_receipts WHERE id=%s',(cold['id'],)).fetchone()
    require(observed and observed['receipt']['bundle_id']==cold['bundle_id'] and observed['receipt']['top_document_ids']==cold['top_document_ids'],'LOCAL_INDEPENDENT_RECEIPT_MISMATCH')
    status_text=Path(f'/proc/{server_pid}/status').read_text()
    peak_kib=int(next(line.split()[1] for line in status_text.splitlines() if line.startswith('VmHWM:')))
    atomic_json('evidence/serving/local-open-loop.json',{'namespace':'serving_measurement','environment':'GitHub standard CPU; local HTTP and ephemeral PostgreSQL; not public Vercel','bundle_id':cold['bundle_id'],'observed_at':utcnow(),'concurrency_cap':4,'server_peak_rss_mib':peak_kib/1024,'memory_observer':'Independent Linux /proc server process VmHWM high-water mark','first_request':cold_observation,'summaries':summary,'observations':sorted(rows,key=lambda r:(r['rate'],r['index'])),'independent_db_match':True,'public_live_verified':False})


if __name__=='__main__':
    measure()
