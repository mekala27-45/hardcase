"""Fault observations on real exported bundles in an isolated CI database."""
import concurrent.futures
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime,timezone,timedelta
from hardcase.contracts import atomic_json,digest,load_json,require,utcnow
from hardcase.inference.bundle import Bundle
from hardcase.registry.postgres import connect,transition,alias_snapshot
from hardcase.api.receipts import new_session,read_receipt
from deploy.measure_api import request


def proposal(current,target,generation,evaluation,policy):
    return {'idempotency_key':str(uuid.uuid4()),'alias':'default','current_bundle_id':current,'target_bundle_id':target,'expected_generation':generation,'target_deployment_id':'local','evaluation_digest':evaluation,'policy_digest':policy,'proposer':'isolated-real-bundle-fault-test','expires_at':(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()}


def load_service():
    from hardcase.api import server
    require(os.getenv('HARDCASE_TEST_DATABASE')=='1','ISOLATED_DATABASE_REQUIRED')
    for row in load_json('runtime/bundles/allowlist.json')['bundles']:
        value=Bundle('runtime/bundles/'+row['directory'])
        server.bundles[value.id]=value
    return server


def fresh_http(token=None):
    if token is None:
        status,body=request('/api/v1/sessions',{})
        require(status==200,'FAULT_HTTP_SESSION_FAILED')
        token=body['capability']
    status,result=request('/api/v1/search',{'query':'A fresh authored rollback recovery query about protein expression.','alias':'default','top_k':10},token,str(uuid.uuid4()))
    require(status==200 and result['fresh'] and not result['replayed'],'FAULT_FRESH_HTTP_FAILED')
    with connect() as db:
        row=db.execute('SELECT receipt FROM hardcase.query_receipts WHERE id=%s',(result['id'],)).fetchone()
    require(row and row['receipt']==result,'FAULT_INDEPENDENT_DB_MISMATCH')
    return result


def paused_inference(server,alias,mutate):
    token=new_session()['capability']
    reached,resume=threading.Event(),threading.Event()
    original=server.commit_receipt
    captured={}
    def paused(admission,receipt,status='completed'):
        captured.update(receipt)
        reached.set()
        require(resume.wait(10),'FAULT_RESUME_TIMEOUT')
        return original(admission,receipt,status)
    server.commit_receipt=paused
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(server.execute_search,server.Search(query='An authored query while the alias changes.',alias=alias,top_k=10),token,str(uuid.uuid4()))
            require(reached.wait(10),'ACTUAL_INFERENCE_BOUNDARY_NOT_REACHED')
            require(bool(captured.get('top_document_ids')),'NO_ACTUAL_RANKINGS_AT_BOUNDARY')
            action=mutate(captured)
            resume.set()
            try:
                result={'status':'completed','receipt':future.result(timeout=10)}
            except ValueError as error:
                result={'status':'refused','reason':str(error)}
    finally:
        resume.set()
        server.commit_receipt=original
    return captured,action,result


def child():
    server=load_service()
    def uncommitted(admission,receipt,status='completed'):
        from psycopg.types.json import Jsonb
        db=connect()
        db.execute("UPDATE hardcase.query_receipts SET status='completed',receipt=%s,completed_at=now() WHERE id=%s",(Jsonb(receipt),admission['request_id']))
        print(json.dumps({'boundary':'uncommitted_actual_receipt','id':admission['request_id'],'bundle_id':receipt['bundle_id'],'ranking_digest':digest(receipt['top_document_ids'])}),flush=True)
        sys.stdin.readline()
        db.rollback()
        raise RuntimeError('FAULT_CHILD_MUST_BE_TERMINATED')
    server.commit_receipt=uncommitted
    server.execute_search(server.Search(query='An authored process-death boundary query.',alias='default',top_k=10),os.environ['HARDCASE_FAULT_SESSION'],'process-death-actual')


def run():
    from psycopg.types.json import Jsonb
    server=load_service()
    package=load_json('runtime/bundles/allowlist.json')
    base=next(r['id'] for r in package['bundles'] if r['method']=='base_float32')
    candidate=next(r['id'] for r in package['bundles'] if r['method']!='base_float32')
    policy=digest({'isolated_fault_test':True,'not_quality_approval':True})
    report={'namespace':'scripted_release','passed':True,'policy_digest':policy,'bundle_id':candidate,'not_quality_evidence':True}
    evaluation=digest(report)
    with connect() as db:
        db.execute('INSERT INTO hardcase.evaluation_reports(id,report) VALUES (%s,%s)',(evaluation,Jsonb(report)))
    cases=[]
    barrier=threading.Barrier(2)
    generation=alias_snapshot('default')['generation']
    def compete(_):
        item=proposal(base,candidate,generation,evaluation,policy)
        barrier.wait(10)
        try:return {'status':'committed','receipt':transition(item,set(server.bundles))}
        except ValueError as error:return {'status':'refused','reason':str(error)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(compete,range(2)))
    current=alias_snapshot('default')
    require(sorted(r['status'] for r in outcomes)==['committed','refused'] and current['bundle_id']==candidate and current['generation']==generation+1,'ACTUAL_BUNDLE_CAS_FAILURE')
    cases.append({'case':'cas_race','status':'passed','outcomes':outcomes,'independent_observer':current})
    def rollback(_):
        return transition(proposal(candidate,base,current['generation'],evaluation,policy),set(server.bundles),'rollback')
    captured,action,result=paused_inference(server,'default',rollback)
    require(result['status']=='completed' and result['receipt']['bundle_id']==candidate and result['receipt']['completion_generation']==current['generation']+1,'ACTUAL_INFLIGHT_ROLLBACK_FAILURE')
    recovered=fresh_http()
    require(recovered['bundle_id']==base and recovered['admission_generation']==current['generation']+1,'FRESH_ROLLBACK_NOT_BASE')
    cases.append({'case':'rollback_during_inflight','status':'passed','injection':'after actual ONNX ranking and before receipt commit','transition':action,'admitted_receipt':result['receipt'],'fresh_http_and_independent_db':recovered})
    token=new_session()['capability']
    environment=os.environ.copy()
    environment['HARDCASE_FAULT_SESSION']=token
    worker=subprocess.Popen([sys.executable,__file__,'--death-child'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        line=pool.submit(worker.stdout.readline)
        try:
            boundary=json.loads(line.result(timeout=45))
            require(boundary.get('boundary')=='uncommitted_actual_receipt','WRONG_CHILD_BOUNDARY')
        finally:
            worker.terminate()
            worker.wait(timeout=10)
    with connect() as db:
        observed=db.execute('SELECT id,status,receipt,session_digest FROM hardcase.query_receipts WHERE id=%s',(boundary['id'],)).fetchone()
        require(observed['status']=='pending' and observed['receipt'] is None,'KILLED_RECEIPT_WAS_COMMITTED')
        db.execute("UPDATE hardcase.sessions SET busy_until=now()-interval '1 second' WHERE capability_digest=%s",(observed['session_digest'],))
    recovered=fresh_http(token)
    with connect() as db:
        original=db.execute('SELECT id,status,receipt FROM hardcase.query_receipts WHERE id=%s',(boundary['id'],)).fetchone()
    require(original['status']=='timeout' and recovered['bundle_id']==base,'DEAD_WORKER_RECOVERY_FAILED')
    cases.append({'case':'process_death_before_receipt_commit','status':'passed','injected_boundary':boundary,'child_exit':worker.returncode,'independent_original_receipt':dict(original),'fresh_http_and_independent_db':recovered})
    def revoke(_):
        with connect() as db:
            db.execute("UPDATE hardcase.bundle_status SET valid=false,reason='isolated integrity fault' WHERE bundle_id=%s",(candidate,))
        return {'revoked_bundle_id':candidate}
    captured,action,result=paused_inference(server,'experimental',revoke)
    with connect() as db:
        observed=db.execute('SELECT status,receipt FROM hardcase.query_receipts WHERE id=%s',(captured['id'],)).fetchone()
    require(result['status']=='refused' and result['reason']=='BUNDLE_REVOKED_BEFORE_COMMIT' and observed['status']=='revoked' and observed['receipt']['results']==[],'ACTUAL_REVOCATION_FAILURE')
    cases.append({'case':'revocation_before_commit','status':'passed','injection':'after actual ONNX ranking and before receipt commit','action':action,'result':result,'independent_observation':dict(observed)})
    atomic_json('evidence/faults/runtime-transactions.json',{'namespace':'scripted_release','environment':'isolated PostgreSQL 18 and actual ONNX packages; not production','model_execution':True,'status':'passed','cases':cases,'source_commit':os.getenv('GITHUB_SHA'),'run_id':os.getenv('GITHUB_RUN_ID'),'package_digest':digest(package),'observed_at':utcnow()})


if __name__=='__main__':
    child() if '--death-child' in sys.argv else run()
