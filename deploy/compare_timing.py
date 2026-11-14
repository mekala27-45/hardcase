"""Paired resource summary after repeat aggregation within query."""
from pathlib import Path
from hardcase.contracts import atomic_json, digest, load_json, require, utcnow


def aggregate(rows):
    by_query={}
    for row in rows:
        by_query.setdefault(row['query_id'],[]).append(row)
    require(len(by_query)==30,'TIMING_QUERY_INVENTORY_CHANGED')
    result={}
    for query,values in by_query.items():
        require(sorted(r['repeat'] for r in values)==list(range(5)),'TIMING_REPEAT_INVENTORY_CHANGED')
        result[query]={field:sum(r[field] for r in values)/5 for field in ('encoding_ms','search_ms','serialization_ms','total_ms')}
    return result


def run():
    exports=load_json('artifacts/export/selection.json')
    sources={'selected_pytorch_parent':'evidence/serving/torch-reference.json','candidate_float32':'evidence/serving/candidate_float32-matched.json','candidate_int8':'evidence/serving/candidate_int8-matched.json'}
    summaries,paired,observations=[],[],{}
    for method,path in sources.items():
        if not Path(path).exists():
            summaries.append({'method':method,'status':'unexecuted','mean_query_ms':None})
            continue
        raw=load_json(path)
        if raw.get('status') in {'unsupported','failed'}:
            summaries.append({'method':method,'status':raw['status'],'mean_query_ms':None,'diagnostic':raw.get('diagnostic')})
            continue
        by_query=aggregate(raw['observations'])
        observations[method]=by_query
        root=Path(exports['bundles'][method]) if method in exports['bundles'] else None
        sizes={'model_bytes':(root/'model.onnx').stat().st_size if root else None,'tokenizer_bytes':(root/'tokenizer.json').stat().st_size if root else None,'vector_bytes':(root/'vectors.npy').stat().st_size if root else None,'bundle_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) if root else None,'total_deployment_bytes':None}
        summaries.append({'method':method,'status':'completed','queries':len(by_query),'repeats':5,'mean_query_ms':sum(r['total_ms'] for r in by_query.values())/len(by_query),'peak_rss_mib':raw['peak_rss_mib'],'cold_load_ms':raw['cold_load_ms'],'source_digest':digest(raw),**sizes})
    reference=observations.get('selected_pytorch_parent',{})
    for method,rows in observations.items():
        if method=='selected_pytorch_parent':continue
        require(set(rows)==set(reference),'UNMATCHED_TIMING_QUERIES')
        for query,value in rows.items():
            paired.append({'method':method,'query_id':query,'reference_mean_ms':reference[query]['total_ms'],'variant_mean_ms':value['total_ms'],'difference_ms':value['total_ms']-reference[query]['total_ms'],'speed_ratio_reference_over_variant':reference[query]['total_ms']/value['total_ms']})
    atomic_json('evidence/serving/paired-timing.json',{'namespace':'serving_measurement','summary':summaries,'paired_query_rows':paired,'per_query_means':observations,'aggregation':'Five ordered repeats averaged within each query before pairing; thirty semantic query units. No p99 capacity claim. Runtime dependencies and host package overhead are excluded from bundle bytes.','serving_variant_unchanged':exports['variant'],'export_id':exports['export_id'],'observed_at':utcnow()})


if __name__=='__main__':
    run()
