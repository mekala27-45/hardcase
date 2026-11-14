"""Regrade retained rankings without importing the evaluator's metric functions.

This checks recorded execution, not a new model run. Missing export rows remain
missing; they are never filled with zero. Run only after the frozen live gate.
"""
import math
from hardcase.contracts import digest, require, utcnow

METRICS = ('ndcg10', 'recall10', 'recall100', 'mrr10')


def reference_metrics(ranking, relevance):
    require(len(ranking) == len(set(ranking)), 'DUPLICATE_RETRIEVED_ID')
    require(all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in relevance.values()), 'INVALID_QRELS')
    positives = {key for key, value in relevance.items() if value > 0}
    require(bool(positives), 'NO_USABLE_QRELS')
    def discounted(values):
        return math.fsum(math.expm1(value * math.log(2)) / math.log2(rank + 1)
                         for rank, value in enumerate(values, 1))
    ideal = discounted(sorted(relevance.values(), reverse=True)[:10])
    hits = [rank for rank, key in enumerate(ranking[:100], 1) if key in positives]
    return {'ndcg10': discounted([relevance.get(key, 0) for key in ranking[:10]]) / ideal,
            'recall10': sum(rank <= 10 for rank in hits) / len(positives),
            'recall100': len(hits) / len(positives),
            'mrr10': 1 / hits[0] if hits and hits[0] <= 10 else 0.0}


def audit(config, request, source, queries, documents, labels, artifacts):
    failures = []
    checks = 0
    def check(condition, code):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(code)
    def same_number(left, right):
        return type(left) in (int, float) and math.isfinite(left) and math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)
    main_methods = ['bm25', 'base_encoder'] + config['arms']
    exports = ['candidate_float32', 'candidate_int8']
    methods = main_methods + exports
    ids = sorted(queries)
    expected = {(method, query) for method in methods for query in ids}
    report = artifacts['report']
    inventory = artifacts['planned-inventory']
    check(len(ids) == config['expected']['test_queries'], 'QUERY_COUNT')
    check(len(documents) == config['expected']['documents'], 'CORPUS_COUNT')
    check(ids == sorted(source['test_ids']), 'QUERY_IDENTITY')
    check(digest(labels) == source['test_labels_digest'] == report.get('label_digest'), 'LABEL_IDENTITY')
    check(digest({k: v for k, v in report.items() if k != 'report_digest'}) == report.get('report_digest'), 'REPORT_DIGEST')
    check(report.get('selection_id') == request['selection_id'] and report.get('export_id') == request['export_id'], 'FROZEN_SELECTION')
    check(inventory.get('query_ids') == ids and inventory.get('main_methods') == main_methods and inventory.get('export_methods') == exports, 'PLANNED_INVENTORY')
    check(inventory.get('corpus_ids_digest') == digest(sorted(documents)), 'CORPUS_IDENTITY')
    check(inventory.get('main_rows') == len(main_methods)*len(ids) and inventory.get('export_rows') == len(exports)*len(ids), 'PLANNED_DENOMINATORS')
    gold = {}
    for row in labels:
        q, d, score = row['query_id'], row['document_id'], row['score']
        check(q in queries and d in documents, 'QREL_INVENTORY')
        previous = gold.setdefault(q, {})
        check(d not in previous, 'DUPLICATE_QREL')
        previous[d] = score
    rows = artifacts['main-rows'] + artifacts['export-rows']
    keys = [(r['method'], r['query_id']) for r in rows]
    check(len(keys) == len(set(keys)) and set(keys) == expected, 'ROW_COVERAGE')
    executions = {r['method']: r for r in artifacts['executions']}
    check(len(executions) == len(artifacts['executions']) and set(executions) == set(methods), 'EXECUTION_COVERAGE')
    recalculated = {}
    for method in methods:
        rankings = artifacts.get(method+'-rankings', {})
        execution = executions.get(method, {})
        check(set(rankings) <= set(ids), 'UNKNOWN_RANKING_QUERY:'+method)
        check(execution.get('rankings_digest') == digest(rankings), 'RANKING_DIGEST:'+method)
        check(execution.get('completed_queries') == len(rankings), 'EXECUTION_COUNT:'+method)
        if method in main_methods or method == 'candidate_float32':
            check(execution.get('status') == 'completed' and set(rankings) == set(ids), 'REQUIRED_METHOD_INCOMPLETE:'+method)
        for q, ranking in rankings.items():
            check(isinstance(ranking, list) and len(ranking) == min(100, len(documents)) and set(ranking) <= set(documents), 'RANKING_INVENTORY:'+method+':'+q)
            try:
                recalculated[method, q] = reference_metrics(ranking, gold.get(q, {}))
            except (ValueError, TypeError, OverflowError):
                failures.append('INVALID_RANKING_OR_QRELS:'+method+':'+q)
    for row in rows:
        key = row['method'], row['query_id']
        values = recalculated.get(key)
        if values is None:
            check(row.get('status') != 'completed' and row.get('metrics') is None, 'MISSING_RESULT_HAS_METRICS:'+str(key))
        else:
            check(row.get('status') == 'completed' and isinstance(row.get('metrics'), dict), 'ROW_STATUS:'+str(key))
            for metric, value in values.items():
                check(same_number((row.get('metrics') or {}).get(metric), value), 'METRIC:'+str(key)+':'+metric)
    for table, names in (('methods', main_methods), ('exports', exports)):
        summaries = report.get(table, [])
        check(len(summaries) == len(names) and {r['method'] for r in summaries} == set(names), 'SUMMARY_COVERAGE:'+table)
        for row in summaries:
            present = [recalculated[row['method'], q] for q in ids if (row['method'], q) in recalculated]
            complete = len(present) == len(ids)
            check(row.get('planned_queries') == len(ids) and row.get('completed_queries') == len(present), 'SUMMARY_DENOMINATOR:'+row['method'])
            check(row.get('status') == ('completed' if complete else 'incomplete'), 'SUMMARY_STATUS:'+row['method'])
            for metric in METRICS:
                value = math.fsum(r[metric] for r in present) / len(ids) if complete else None
                check(row.get(metric) is None if value is None else same_number(row.get(metric), value), 'SUMMARY_METRIC:'+row['method']+':'+metric)
    groups = artifacts['test-groups']
    members = [q for group in groups for q in group]
    check(all(groups) and len(members) == len(set(members)) and set(members) == set(ids), 'GROUP_PARTITION')
    check(digest(groups) == report.get('groups_digest'), 'GROUP_DIGEST')
    candidate = report.get('candidate')
    if all((method, q) in recalculated for method in (candidate, 'base_encoder') for q in ids):
        difference = math.fsum(recalculated[candidate, q]['ndcg10']-recalculated['base_encoder', q]['ndcg10'] for q in ids) / len(ids)
        check(same_number((report.get('primary', {}).get('estimate') or {}).get('mean_difference'), difference), 'PRIMARY_MEAN')
    else:
        check(report.get('primary', {}).get('estimate') is None, 'INCOMPLETE_PRIMARY_ESTIMATE')
    complete_main = sum((m,q) in recalculated for m in main_methods for q in ids)
    complete_exports = sum((m,q) in recalculated for m in exports for q in ids)
    check(report.get('status') == 'completed' and complete_main == len(main_methods)*len(ids), 'MAIN_COMPLETION')
    check(report.get('main_completed_rows') == complete_main and report.get('main_planned_rows') == len(main_methods)*len(ids), 'MAIN_COUNTS')
    check(report.get('export_completed_rows') == complete_exports and report.get('export_planned_rows') == len(exports)*len(ids), 'EXPORT_COUNTS')
    return {'status': 'passed' if not failures else 'failed', 'passed': not failures,
            'namespace': 'independent_ranking_audit', 'model_execution': False,
            'report_digest': report.get('report_digest'), 'request_digest': digest(request),
            'checks': checks, 'failures': sorted(set(failures)),
            'main_verified_rows': complete_main, 'export_verified_rows': complete_exports,
            'source_digests': {k: digest(v) for k, v in artifacts.items()},
            'metric_tolerance': {'absolute': 1e-12, 'relative': 1e-12}, 'verified_at': utcnow()}


