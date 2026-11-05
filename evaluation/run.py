"""Frozen held-out execution. This entry point never chooses a checkpoint."""
import os
import platform
import re
import time
from pathlib import Path
from hardcase.contracts import Stage, atomic_json, digest, file_digest, load_json, require, utcnow
from hardcase.data.grouping import groups_with_positives
from hardcase.mining.retrieval import BM25, exact_search
from hardcase.training.encoder import download_locked, load_encoder, encode, parameter_hashes
from hardcase.inference.bundle import Bundle
from .metrics import grade_inventory, qrel_map
from .statistics import grouped_bootstrap, grouped_sign_flip, benjamini_hochberg, quantile


def summaries(rows, methods, planned):
    result = []
    for method in methods:
        complete = [r for r in rows if r['method'] == method and r['status'] == 'completed']
        item = {'method': method, 'status': 'completed' if len(complete) == planned else 'incomplete', 'completed_queries': len(complete), 'planned_queries': planned}
        for metric in ('ndcg10', 'recall10', 'recall100', 'mrr10'):
            item[metric] = sum(r['metrics'][metric] for r in complete) / planned if len(complete) == planned else None
        result.append(item)
    return result


def compare(rows, left, right, query_ids, groups, config):
    values = {(r['method'], r['query_id']): r['metrics'] for r in rows if r['status'] == 'completed'}
    if any((method, q) not in values for method in (left, right) for q in query_ids):
        return {'left': left, 'right': right, 'status': 'incomplete', 'estimate': None, 'p_value': None}
    changes = {q: values[left, q]['ndcg10'] - values[right, q]['ndcg10'] for q in query_ids}
    interval = grouped_bootstrap(changes, groups, config['seed'], config['bootstrap_resamples'])
    return {'left': left, 'right': right, 'status': 'completed', 'estimate': interval, 'p_value': grouped_sign_flip(changes, groups, config['seed'], config['secondary_sign_flips']), 'assumption': 'Two-sided group exchangeability; descriptive under incomplete judgments or uncertain dependence.'}


def run():
    import numpy as np
    import torch
    config = load_json('requests/experiment.json')
    request = load_json('requests/evaluate.json')
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{4,60}', request['evaluation_id']) is not None, 'UNSAFE_EVALUATION_ID')
    selection = load_json('artifacts/training/selection.json')
    exported = load_json('artifacts/export/selection.json')
    require(digest({k:v for k,v in selection.items() if k!='selection_id'}) == selection['selection_id'], 'SELECTION_CONTENT_CHANGED')
    require(digest({k:v for k,v in exported.items() if k!='export_id'}) == exported['export_id'], 'EXPORT_SELECTION_CONTENT_CHANGED')
    live = load_json('evidence/live/pretest.json')
    require(selection['selection_id'] == request['selection_id'] and exported['export_id'] == request['export_id'], 'EVALUATION_FREEZE_CHANGED')
    require(exported['selection_id'] == selection['selection_id'], 'EXPORT_PARENT_CHANGED')
    require(live.get('status') == 'verified' and live.get('learned_fresh_browser') is True and live.get('learned_fresh_client') is True and live.get('independent_db_match') is True, 'PRETEST_LIVE_EVIDENCE_MISSING')
    require(digest(live) == request['pretest_live_digest'], 'LIVE_EVIDENCE_CHANGED')
    root = Path('artifacts/evaluation') / request['evaluation_id']
    require(not root.exists(), 'EVALUATION_ATTEMPT_ALREADY_EXISTS')
    root.mkdir(parents=True)
    with Stage(root, 'run', {'request': request, 'selection': selection['selection_id'], 'export': exported['export_id']}) as terminal:
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        documents = load_json('data/processed/documents.json')
        queries = load_json('data/vault/test-queries.json')
        labels = load_json('data/vault/test-qrels.json')
        source = load_json('data/manifests/source.json')
        require(digest(labels) == source['test_labels_digest'], 'TEST_LABEL_SOURCE_CHANGED')
        require(sorted(queries) == sorted(source['test_ids']), 'TEST_INVENTORY_CHANGED')
        require(digest(documents) == load_json('data/manifests/preparation.json')['document_view_digest'], 'TEST_DOCUMENT_VIEW_CHANGED')
        ids, query_ids = sorted(documents), sorted(queries)
        methods = ['bm25', 'base_encoder'] + config['arms']
        export_methods = ['candidate_float32', 'candidate_int8']
        rankings, executions, identities = {}, [], {}
        selected_arms = {r['arm']: r for r in selection['arms']}
        atomic_json(root / 'planned-inventory.json', {'main_methods': methods, 'export_methods': export_methods, 'query_ids': query_ids, 'corpus_ids_digest': digest(ids), 'main_rows': len(methods)*len(query_ids), 'export_rows': len(export_methods)*len(query_ids), 'selection_id': selection['selection_id'], 'export_id': exported['export_id']})
        for method in methods + export_methods:
            started = utcnow()
            timer = time.perf_counter()
            rankings[method] = {}
            try:
                if method == 'bm25':
                    retriever = BM25({d: documents[d]['visible_text'] for d in ids})
                    rankings[method] = {q: [d for d, score in retriever.search(queries[q]['text'], 100)] for q in query_ids}
                    identities[method] = {'corpus_digest': digest(documents), 'algorithm': 'BM25 k1=1.5 b=0.75 positive Robertson IDF stable-ID ties'}
                elif method in export_methods:
                    require(method in exported['bundles'], 'EXPORT_VARIANT_UNAVAILABLE')
                    bundle = Bundle(exported['bundles'][method])
                    require(bundle.id == exported['validation'][method]['bundle_id'], 'EXPORT_BUNDLE_CHANGED')
                    for q in query_ids:
                        rankings[method][q] = [d for d, score in exact_search(bundle.encode([queries[q]['text']])[0], bundle.matrix, bundle.ids, 100)]
                    identities[method] = {'bundle_id': bundle.id, 'graph_digest': bundle.manifest['files']['model.onnx'], 'index_digest': bundle.manifest['files']['vectors.npy']}
                    del bundle
                else:
                    if method == 'base_encoder':
                        path = download_locked('student')
                        expected_state = load_json('data/manifests/preparation.json')['base_state_digest']
                    else:
                        checkpoint = Path(selected_arms[method]['checkpoint'])
                        manifest = load_json(checkpoint / 'manifest.json')
                        require(digest(manifest) == selected_arms[method]['manifest_digest'], 'SELECTED_CHECKPOINT_CHANGED')
                        for filename, expected in manifest['files'].items():
                            require(file_digest(checkpoint / filename) == expected, 'CHECKPOINT_FILE_CHANGED')
                        path = checkpoint / 'encoder'
                        expected_state = selected_arms[method]['state_digest']
                    model, tokenizer = load_encoder(path)
                    state_id = digest(parameter_hashes(model))
                    require(state_id == expected_state, 'EVALUATION_MODEL_CHANGED')
                    matrix = encode(model, tokenizer, [documents[d]['visible_text'] for d in ids], config['max_length'], receipt_path=root / f'{method}-corpus-encoding.json', identity=state_id)
                    vectors = encode(model, tokenizer, [queries[q]['text'] for q in query_ids], config['max_length'], receipt_path=root / f'{method}-query-encoding.json', identity=state_id)
                    rankings[method] = {q: [d for d, score in exact_search(v, matrix, ids, 100)] for q, v in zip(query_ids, vectors)}
                    identities[method] = {'state_digest': state_id, 'corpus_digest': digest(documents)}
                    del model, matrix, vectors
                status, error = 'completed', None
            except Exception as failure:
                status, error = 'failed', type(failure).__name__ + ': ' + str(failure)[:400]
            atomic_json(root / f'{method}-rankings.json', rankings[method])
            executions.append({'method': method, 'status': status, 'error': error, 'completed_queries': len(rankings[method]), 'started_at': started, 'ended_at': utcnow(), 'seconds': time.perf_counter()-timer, 'identity': identities.get(method), 'rankings_digest': digest(rankings[method])})
            atomic_json(root / 'executions.json', executions)
        main = grade_inventory(methods, query_ids, rankings, labels, set(ids))
        export_rows = grade_inventory(export_methods, query_ids, rankings, labels, set(ids))
        atomic_json(root / 'main-rows.json', main)
        atomic_json(root / 'export-rows.json', export_rows)
        groups = groups_with_positives({q: queries[q]['text'] for q in query_ids}, labels, config['query_duplicate_trigram_jaccard'])
        atomic_json(root / 'test-groups.json', groups)
        candidate = selection['candidate']['arm']
        primary = compare(main, candidate, 'base_encoder', query_ids, groups, config)
        contrasts = [('hard_contrastive','uniform_contrastive'), ('hard_distilled','hard_contrastive'), (candidate,'bm25')]
        secondary = [compare(main, a, b, query_ids, groups, config) for a, b in contrasts]
        if all(r['status'] == 'completed' for r in secondary):
            for row, adjusted in zip(secondary, benjamini_hochberg([r['p_value'] for r in secondary])):
                row['bh_adjusted_p'] = adjusted
        else:
            for row in secondary:
                row['bh_adjusted_p'] = None
        metrics = {(r['method'], r['query_id']): r['metrics'] for r in main+export_rows if r['status'] == 'completed'}
        drift = []
        for method in export_methods:
            for q in query_ids:
                left, right = rankings.get(method, {}).get(q), rankings[candidate].get(q)
                complete = left is not None and right is not None
                drift.append({'method': method, 'query_id': q, 'status': 'completed' if complete else 'unexecuted', 'top10_set_overlap': len(set(left[:10]) & set(right[:10]))/10 if complete else None, 'exact_rank_disagreement': sum(a != b for a,b in zip(left[:10], right[:10])) if complete else None, 'ndcg10_change': metrics[method,q]['ndcg10']-metrics[candidate,q]['ndcg10'] if (method,q) in metrics and (candidate,q) in metrics else None, 'recall100_change': metrics[method,q]['recall100']-metrics[candidate,q]['recall100'] if (method,q) in metrics and (candidate,q) in metrics else None})
        atomic_json(root / 'export-drift.json', drift)
        paired = []
        gold = qrel_map(labels)
        for q in query_ids:
            if ('base_encoder',q) not in metrics or (candidate,q) not in metrics:
                continue
            base, learned = metrics['base_encoder',q]['ndcg10'], metrics[candidate,q]['ndcg10']
            paired.append({'query_id': q, 'query': queries[q]['text'], 'base_ndcg10': base, 'candidate_ndcg10': learned, 'difference': learned-base, 'category': 'observed loss' if learned<base else 'observed gain' if learned>base else 'unchanged failure' if base<1 else 'unchanged success', 'relevant_documents': [{'id': d, 'base_rank': rankings['base_encoder'][q].index(d)+1 if d in rankings['base_encoder'][q] else None, 'candidate_rank': rankings[candidate][q].index(d)+1 if d in rankings[candidate][q] else None, 'view': documents[d]} for d in sorted(gold[q]) if gold[q][d]>0], 'causal_explanation': 'Not established by ranking differences.', 'teacher_behavior': 'Not measured on held-out lists.'})
        sample = sorted(paired,key=lambda r:(r['difference'],r['query_id']))[:5] + sorted(paired,key=lambda r:(-r['difference'],r['query_id']))[:5] + [r for r in paired if r['category']=='unchanged failure'][:5] + sorted(paired,key=lambda r:digest([config['seed'],r['query_id']]))[:5]
        errors = list({r['query_id']:r for r in sample}.values())
        atomic_json(root / 'error-sample.json', errors)
        train_queries = load_json('data/processed/train-queries.json')
        lengths = [len(train_queries[q]['text']) for q in load_json('data/manifests/split.json')['fit']]
        boundaries = [quantile(lengths, p) for p in (1/3,2/3)]
        slices = [{'query_id': q, 'length_bin': sum(len(queries[q]['text'])>b for b in boundaries), 'relevant_count_bin': 'one' if len([s for s in gold[q].values() if s>0])==1 else 'multiple', 'any_relevant_truncated': any(documents[d].get('truncated',False) for d,s in gold[q].items() if s>0)} for q in query_ids]
        atomic_json(root / 'slices.json', {'development_length_boundaries': boundaries, 'rows': slices, 'interpretation': 'Descriptive source-property slices; no subgroup significance claim.'})
        report = {'namespace': 'retrieval_quality', 'status': 'completed' if all(r['status']=='completed' for r in main) else 'incomplete', 'methods': summaries(main, methods, len(query_ids)), 'exports': summaries(export_rows, export_methods, len(query_ids)), 'primary': primary, 'secondary': secondary, 'errors': [{k:v for k,v in r.items() if k!='relevant_documents'} for r in errors], 'selection_id': selection['selection_id'], 'export_id': exported['export_id'], 'candidate': candidate, 'main_completed_rows': sum(r['status']=='completed' for r in main), 'main_planned_rows': len(main), 'export_completed_rows': sum(r['status']=='completed' for r in export_rows), 'export_planned_rows': len(export_rows), 'test_query_count': len(query_ids), 'corpus_count': len(ids), 'label_digest': digest(labels), 'groups_digest': digest(groups), 'source_commit': os.getenv('GITHUB_SHA','local'), 'run_id': os.getenv('GITHUB_RUN_ID','local'), 'platform': platform.platform(), 'started_at': terminal['started_at'], 'ended_at': utcnow(), 'conclusion': 'Frozen comparison only. Promotion also requires independent live and resource evidence.'}
        report['report_digest'] = digest(report)
        atomic_json(root / 'report.json', report)
        terminal.update(report_digest=report['report_digest'], main_completed_rows=report['main_completed_rows'], export_completed_rows=report['export_completed_rows'])


if __name__ == '__main__':
    run()
