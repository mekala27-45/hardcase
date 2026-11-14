import copy
import math
import unittest
from evaluation.audit import audit, reference_metrics
from hardcase.contracts import digest


class IndependentAuditTests(unittest.TestCase):
    def fixture(self):
        methods = ['bm25', 'base_encoder', 'uniform_contrastive', 'hard_contrastive', 'hard_distilled']
        exports = ['candidate_float32', 'candidate_int8']
        queries = {'q1': {}, 'q2': {}}
        docs = {'a': {}, 'b': {}}
        labels = [{'query_id': q, 'document_id': 'a', 'score': 1} for q in queries]
        config = {'arms': methods[2:], 'expected': {'test_queries': 2, 'documents': 2}}
        request = {'selection_id': 'selected', 'export_id': 'exported'}
        source = {'test_ids': list(queries), 'test_labels_digest': digest(labels)}
        artifact = {'planned-inventory': {'query_ids': list(queries), 'main_methods': methods, 'export_methods': exports, 'main_rows': 10, 'export_rows': 4, 'corpus_ids_digest': digest(sorted(docs))}, 'main-rows': [], 'export-rows': [], 'executions': [], 'test-groups': [['q1'], ['q2']]}
        report = {'status': 'completed', **request, 'candidate': 'hard_contrastive', 'label_digest': digest(labels), 'groups_digest': digest(artifact['test-groups']), 'methods': [], 'exports': [], 'main_completed_rows': 10, 'main_planned_rows': 10, 'export_completed_rows': 2, 'export_planned_rows': 4, 'primary': {'estimate': {'mean_difference': 0.0}}}
        for method in methods+exports:
            available = method != 'candidate_int8'
            ranks = {q: ['a','b'] for q in queries} if available else {}
            artifact[method+'-rankings'] = ranks
            artifact['executions'].append({'method': method, 'rankings_digest': digest(ranks), 'status': 'completed' if available else 'failed', 'completed_queries': len(ranks)})
            metrics = dict.fromkeys(('ndcg10','recall10','recall100','mrr10'), 1.0) if available else None
            artifact['main-rows' if method in methods else 'export-rows'].extend({'method': method, 'query_id': q, 'status': 'completed' if available else 'unexecuted', 'metrics': copy.deepcopy(metrics)} for q in queries)
            report['methods' if method in methods else 'exports'].append({'method': method, 'status': 'completed' if available else 'incomplete', 'planned_queries': 2, 'completed_queries': 2 if available else 0, **(metrics or dict.fromkeys(('ndcg10','recall10','recall100','mrr10')))})
        report['report_digest'] = digest(report)
        artifact['report'] = report
        return config, request, source, queries, docs, labels, artifact

    def test_reference_with_graded_relevance_and_unjudged_document(self):
        m = reference_metrics(['unknown', 'low', 'high'], {'high': 3, 'low': 1})
        expected = (1/math.log2(3)+7/math.log2(4))/(7+1/math.log2(3))
        self.assertAlmostEqual(m['ndcg10'], expected)
        self.assertEqual(m['mrr10'], 0.5)
        self.assertEqual(m['recall100'], 1)

    def test_valid_audit_keeps_unsupported_export_missing(self):
        self.assertTrue(audit(*self.fixture())['passed'])

    def test_tampering_missing_duplicates_unknown_and_nonfinite_are_refused(self):
        def change_metric(a): a['main-rows'][0]['metrics']['ndcg10'] = 0.9
        def remove_row(a): a['main-rows'].pop()
        def duplicate_row(a): a['main-rows'][-1] = copy.deepcopy(a['main-rows'][0])
        def unknown_doc(a): a['bm25-rankings']['q1'][0] = 'outside'
        def duplicate_doc(a): a['bm25-rankings']['q1'] = ['a','a']
        def missing_as_zero(a): a['export-rows'][-1]['metrics'] = {'ndcg10': 0}
        def wrong_group(a): a['test-groups'] = [['q1'], ['q1']]
        def wrong_primary(a): a['report']['primary']['estimate']['mean_difference'] = 0.1
        def nonfinite(a): a['main-rows'][0]['metrics']['ndcg10'] = float('nan')
        for mutation in [change_metric, remove_row, duplicate_row, unknown_doc, duplicate_doc, missing_as_zero, wrong_group, wrong_primary, nonfinite]:
            with self.subTest(mutation=mutation.__name__):
                args = self.fixture()
                mutation(args[-1])
                # Nonfinite JSON is refused before a trustworthy receipt can be emitted.
                try:
                    self.assertFalse(audit(*args)['passed'])
                except ValueError:
                    self.assertEqual(mutation.__name__, 'nonfinite')

    def test_changed_original_labels_cannot_be_regraded_silently(self):
        args = self.fixture()
        args[-2][0]['score'] = 2
        self.assertFalse(audit(*args)['passed'])
