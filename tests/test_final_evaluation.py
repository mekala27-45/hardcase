import unittest
from evaluation.run import summaries, compare


class FinalEvaluationTests(unittest.TestCase):
    def test_incomplete_denominator_suppresses_mean(self):
        row = {'method':'candidate', 'query_id':'q1', 'status':'completed', 'metrics':{'ndcg10':1,'recall10':1,'recall100':1,'mrr10':1}}
        result = summaries([row], ['candidate'], 2)[0]
        self.assertEqual(result['completed_queries'], 1)
        self.assertIsNone(result['ndcg10'])
        self.assertEqual(result['planned_queries'], 2)

    def test_missing_pair_blocks_inference(self):
        result = compare([], 'candidate','base',['q1','q2'],[['q1'],['q2']],{})
        self.assertEqual(result['status'],'incomplete')
        self.assertIsNone(result['estimate'])
        self.assertIsNone(result['p_value'])

    def test_complete_scalar_reference(self):
        rows = [{'method':'candidate','query_id':q,'status':'completed','metrics':{m:v for m in ('ndcg10','recall10','recall100','mrr10')}} for q,v in [('q1',0.2),('q2',0.8)]]
        self.assertEqual(summaries(rows,['candidate'],2)[0]['ndcg10'],0.5)
