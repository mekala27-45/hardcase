"""Ephemeral CI database fault observations, distinct from live deployment proof."""
import concurrent.futures
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from hardcase.contracts import atomic_json, digest, require, utcnow
from hardcase.registry.postgres import connect, register_bundle, transition, alias_snapshot
from hardcase.api.receipts import new_session, admit, commit_receipt, read_receipt


def proposal(current, target, generation, evaluation, policy, key=None):
    return {'idempotency_key': key or str(uuid.uuid4()), 'alias': 'default', 'current_bundle_id': current, 'target_bundle_id': target, 'expected_generation': generation, 'target_deployment_id': 'local', 'evaluation_digest': evaluation, 'policy_digest': policy, 'proposer': 'ephemeral-ci-test', 'expires_at': (datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()}


def run():
    from psycopg.types.json import Jsonb
    require(os.environ.get('HARDCASE_TEST_DATABASE') == '1', 'EPHEMERAL_TEST_SCOPE_REQUIRED')
    with connect() as db:
        db.execute(Path('db/migrations/001_registry.sql').read_text(), prepare=False)
    a, b = [register_bundle({'fixture': name, 'namespace': 'scripted_release', 'model_execution': False}) for name in ('base', 'candidate')]
    policy = digest({'test_gate': True})
    report = {'passed': True, 'policy_digest': policy, 'bundle_id': b, 'namespace': 'scripted_release'}
    evaluation = digest(report)
    with connect() as db:
        db.execute("INSERT INTO hardcase.evaluation_reports(id,report) VALUES (%s,%s)", (evaluation, Jsonb(report)))
        for name in ('base', 'default'):
            db.execute("INSERT INTO hardcase.release_aliases(name,bundle_id,generation) VALUES (%s,%s,1)", (name, a))
        db.execute("INSERT INTO hardcase.release_events(id,proposal_digest,alias,target_bundle_id,generation,kind,receipt) VALUES ('initialize-test',%s,'default',%s,1,'initialize','{}')", (digest('initial'), a))
    evidence = {'namespace': 'scripted_release', 'environment': 'ephemeral PostgreSQL 18 CI service', 'model_execution': False, 'started_at': utcnow(), 'cases': []}
    available = {a, b}
    barrier = threading.Barrier(2)
    def compete(index):
        p = proposal(a, b, 1, evaluation, policy)
        barrier.wait(timeout=10)
        try:
            return {'status': 'committed', 'receipt': transition(p, available)}
        except ValueError as error:
            return {'status': 'refused', 'reason': str(error)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(compete, range(2)))
    observed = alias_snapshot('default')
    require(sorted(r['status'] for r in outcomes) == ['committed', 'refused'] and observed['generation'] == 2, 'CAS_RACE_FAILURE')
    evidence['cases'].append({'case': 'cas_race', 'status': 'passed', 'outcomes': outcomes, 'independent_observer': observed})
    token = new_session()['capability']
    admission = admit(token, 'inflight-original', {'query_digest': digest('authored fixture query'), 'alias': 'default', 'top_k': 10})
    rollback = transition(proposal(b, a, 2, evaluation, policy), available, 'rollback')
    result = commit_receipt(admission, {'id': admission['request_id'], 'alias': 'default', 'bundle_id': admission['bundle_id'], 'admission_generation': admission['generation'], 'results': [{'id': 'fixture'}]})
    observed_receipt = read_receipt(token, admission['request_id'])
    require(observed_receipt['bundle_id'] == b and observed_receipt['admission_generation'] == 2 and observed_receipt['completion_generation'] == 3 and alias_snapshot('default')['bundle_id'] == a, 'INFLIGHT_SNAPSHOT_FAILURE')
    evidence['cases'].append({'case': 'rollback_during_inflight', 'status': 'passed', 'rollback': rollback, 'independent_receipt': observed_receipt, 'inference': 'fixture; actual bundle verification is separate'})
    death_admission = admit(token, 'process-death-receipt', {'query_digest': digest('process death fixture'), 'alias': 'default', 'top_k': 10})
    child = "from hardcase.registry.postgres import connect; import time; db=connect(); db.execute(\"UPDATE hardcase.query_receipts SET status='completed',receipt='{}',completed_at=now() WHERE id=%s\", ('" + death_admission['request_id'] + "',)); print('UNCOMMITTED',flush=True); time.sleep(30); db.commit()"
    worker = subprocess.Popen([sys.executable, '-c', child], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    require(worker.stdout.readline().strip() == 'UNCOMMITTED', 'FAULT_CHILD_NOT_READY')
    worker.terminate()
    worker.wait(timeout=10)
    with connect() as db:
        observed = db.execute('SELECT id,status,receipt FROM hardcase.query_receipts WHERE id=%s', (death_admission['request_id'],)).fetchone()
        require(observed['status'] == 'pending' and observed['receipt'] is None, 'PARTIAL_RECEIPT_COMMIT')
        db.execute("UPDATE hardcase.sessions SET busy_until=now()-interval '1 second' WHERE capability_digest=%s", (death_admission['session_digest'],))
    evidence['cases'].append({'case': 'process_death_before_receipt_commit', 'status': 'passed', 'child_exit': worker.returncode, 'independent_observer': dict(observed), 'recovery': 'Expired lease permits a new request; original pending key is never reported completed.'})
    admission = admit(token, 'revoke-before-commit', {'query_digest': digest('another authored query'), 'alias': 'default', 'top_k': 10})
    with connect() as db:
        recovered = db.execute('SELECT status,receipt FROM hardcase.query_receipts WHERE id=%s', (death_admission['request_id'],)).fetchone()
        require(recovered['status'] == 'timeout' and recovered['receipt']['error'] == 'WORKER_LEASE_EXPIRED', 'STALE_REQUEST_NOT_FINALIZED')
        evidence['cases'][-1]['post_lease_independent_observation'] = dict(recovered)
        db.execute("UPDATE hardcase.bundle_status SET valid=false,reason='ephemeral fault' WHERE bundle_id=%s", (a,))
    try:
        commit_receipt(admission, {'id': admission['request_id'], 'alias': 'default', 'bundle_id': a, 'results': [{'id': 'must-not-escape'}]})
        raise AssertionError('REVOCATION_NOT_REFUSED')
    except ValueError as error:
        require(str(error) == 'BUNDLE_REVOKED_BEFORE_COMMIT', 'WRONG_REVOCATION_ERROR')
    with connect() as db:
        observed = db.execute("SELECT status,receipt FROM hardcase.query_receipts WHERE id=%s", (admission['request_id'],)).fetchone()
    require(observed['status'] == 'revoked' and observed['receipt']['results'] == [], 'REVOKED_RESULTS_ESCAPED')
    evidence['cases'].append({'case': 'revocation_before_commit', 'status': 'passed', 'independent_observer': dict(observed)})
    with connect() as db:
        try:
            db.execute("UPDATE hardcase.bundles SET manifest='{}' WHERE id=%s", (a,))
            raise AssertionError('IMMUTABLE_BUNDLE_MUTATED')
        except Exception as error:
            require('IMMUTABLE_EVIDENCE' in str(error), 'WRONG_IMMUTABILITY_ERROR')
            db.rollback()
    evidence['ended_at'] = utcnow()
    evidence['status'] = 'passed'
    atomic_json('evidence/faults/postgres.json', evidence)
    print(json.dumps({'status': 'passed', 'observed_cases': len(evidence['cases']), 'evidence': 'evidence/faults/postgres.json'}))


if __name__ == '__main__':
    run()
