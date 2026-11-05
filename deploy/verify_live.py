"""Verify separately captured live observations before opening the test vault.

The caller supplies raw browser/client observations and an independently read
database receipt export. This verifier does not make requests or accept secrets.
"""
from hardcase.contracts import atomic_json, digest, load_json, require, utcnow


def verify(observations, database, package):
    expected=next(row for row in package['bundles'] if row['method']!='base_float32')
    require(database.get('observer')=='independent_database_connection','INDEPENDENT_DB_OBSERVER_REQUIRED')
    by_id={row['id']:row for row in database['receipts']}
    seen=set()
    for channel in ('browser','separate_client'):
        observation=observations[channel]
        receipt=observation['receipt']
        require(observation.get('origin')=='public_production','PUBLIC_PRODUCTION_REQUIRED')
        require(receipt['status']=='completed' and receipt.get('fresh') is True and receipt.get('replayed') is False,'FRESH_LEARNED_REQUEST_REQUIRED')
        require(receipt['id'] not in seen,'INDEPENDENT_REQUEST_REQUIRED')
        seen.add(receipt['id'])
        require(receipt['bundle_id']==expected['id'] and receipt['alias']=='experimental','LEARNED_BUNDLE_MISMATCH')
        require(receipt['deployment_id']==observations['deployment_id'],'LIVE_DEPLOYMENT_CHANGED')
        require(receipt['query_digest']==observation['expected_query_digest'],'QUERY_IDENTITY_MISMATCH')
        require(receipt.get('top_document_ids') and receipt['top_document_ids']==[row['id'] for row in receipt['results']],'LIVE_RESULT_IDS_MISMATCH')
        stored=by_id.get(receipt['id'])
        require(stored is not None and stored['status']=='completed' and stored['receipt']==receipt,'INDEPENDENT_DB_RECEIPT_MISMATCH')
        for key in ('graph_digest','tokenizer_digest','corpus_digest','index_digest'):
            require(receipt[key]==expected[key],'LIVE_ARTIFACT_MISMATCH_'+key.upper())
    return {'status':'verified','learned_fresh_browser':True,'learned_fresh_client':True,'independent_db_match':True,'bundle_id':expected['id'],'deployment_id':observations['deployment_id'],'browser_receipt_id':observations['browser']['receipt']['id'],'client_receipt_id':observations['separate_client']['receipt']['id'],'observations_digest':digest(observations),'database_observations_digest':digest(database),'package_digest':digest(package),'verified_at':utcnow()}


if __name__=='__main__':
    atomic_json('evidence/live/pretest.json',verify(load_json('evidence/live/observations.json'),load_json('evidence/live/independent-db.json'),load_json('evidence/live/package.json')))
