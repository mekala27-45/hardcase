import unittest
from evaluation.slices import overlap, describe


class SliceTests(unittest.TestCase):
    def test_known_overlap_and_empty_query(self):
        documents={'d':{'visible_text':'alpha beta'}}
        self.assertEqual(overlap('alpha gamma',{'d':1},documents),1/3)
        self.assertEqual(overlap('',{'d':1},documents),0)

    def test_incomplete_cell_does_not_report_complete_mean(self):
        queries={'q1':{'text':'alpha'},'q2':{'text':'alpha beta'}}
        labels=[{'query_id':q,'document_id':'d','score':1} for q in queries]
        documents={'d':{'visible_text':'alpha beta','truncated':True}}
        bins={'query_length_characters':[20,40],'max_relevant_token_jaccard':[.2,.8]}
        rows=[{'method':'base','query_id':'q1','status':'completed','metrics':{'ndcg10':1}},{'method':'base','query_id':'q2','status':'unexecuted','metrics':None}]
        report=describe(queries,labels,documents,bins,rows)
        cell=next(r for r in report['summaries'] if r['slice']=='length_bin')
        self.assertEqual(cell['planned_queries'],2)
        self.assertIsNone(cell['mean_ndcg10'])
