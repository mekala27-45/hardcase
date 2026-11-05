"""Initialize only missing aliases from verified packaged artifacts."""
from hardcase.contracts import atomic_json, digest, load_json, require
from hardcase.inference.bundle import Bundle
from hardcase.registry.postgres import connect, register_bundle


def register():
    from psycopg.types.json import Jsonb
    package=load_json('runtime/bundles/allowlist.json')
    model_lock=load_json('requests/model-lock.json')
    ids={}
    versions=[]
    for row in package['bundles']:
        bundle=Bundle('runtime/bundles/'+row['directory'])
        require(bundle.id==row['id'],'REGISTER_BUNDLE_MISMATCH')
        version={'schema_version':1,'parent_state_digest':bundle.manifest['parent_state_digest'],'base_repository':model_lock['student']['repo_id'],'base_revision':model_lock['student']['revision'],'config_digest':bundle.manifest['config_digest'],'pooling':bundle.manifest['pooling'],'normalization':bundle.manifest['normalization'],'dimension':bundle.manifest['dimension'],'purpose':'fixed-corpus retrieval; no truth-probability interpretation'}
        version_id=digest(version)
        with connect() as db:
            prior=db.execute('SELECT manifest FROM hardcase.model_versions WHERE id=%s',(version_id,)).fetchone()
            if prior:
                require(prior['manifest']==version,'IMMUTABLE_MODEL_VERSION_CONFLICT')
            else:
                db.execute('INSERT INTO hardcase.model_versions(id,manifest) VALUES (%s,%s)',(version_id,Jsonb(version)))
        versions.append({'method':row['method'],'model_version_id':version_id,'parent_state_digest':version['parent_state_digest'],'bundle_id':bundle.id})
        ids[row['method']]=register_bundle(bundle.manifest)
        del bundle
    candidate=[method for method in ids if method!='base_float32']
    require(len(candidate)==1,'REGISTER_CANDIDATE_AMBIGUOUS')
    expected={'base':ids['base_float32'],'default':ids['base_float32'],'experimental':ids[candidate[0]]}
    receipts=[]
    with connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(2701002)')
        for alias,target in expected.items():
            current=db.execute('SELECT * FROM hardcase.release_aliases WHERE name=%s',(alias,)).fetchone()
            if current:
                require(current['bundle_id']==target,'EXISTING_ALIAS_REQUIRES_REVIEW')
                receipts.append({'alias':alias,'bundle_id':target,'generation':current['generation'],'state':'already_present'})
                continue
            receipt={'alias':alias,'bundle_id':target,'generation':1,'kind':'initialize','package_digest':digest(package),'live_verified':False}
            event_id=digest(receipt)
            db.execute('INSERT INTO hardcase.release_aliases(name,bundle_id,generation) VALUES (%s,%s,1)',(alias,target))
            db.execute("INSERT INTO hardcase.release_events(id,proposal_digest,alias,target_bundle_id,generation,kind,receipt) VALUES (%s,%s,%s,%s,1,'initialize',%s)",(event_id,event_id,alias,target,Jsonb(receipt)))
            receipts.append(receipt)
    atomic_json('artifacts/runtime/initialization.json',{'receipts':receipts,'model_versions':versions,'status':'registered','live_verified':False})


if __name__=='__main__':
    register()
