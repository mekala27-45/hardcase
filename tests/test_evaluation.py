import math
import unittest
from evaluation.metrics import grade, grade_inventory
from evaluation.statistics import grouped_bootstrap, grouped_sign_flip, benjamini_hochberg


class EvaluationTests(unittest.TestCase):
    def test_manual_multiple_relevance(self):
        result = grade(["x", "a", "b"], {"a": 1, "b": 1})
        self.assertAlmostEqual(result["ndcg10"], (1/math.log2(3) + 0.5) / (1 + 1/math.log2(3)))
        self.assertEqual(result["recall10"], 1)
        self.assertEqual(result["mrr10"], 0.5)

    def test_duplicate_does_not_earn_twice(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            grade(["a", "a"], {"a": 1})

    def test_empty_ranking_observed_zero(self):
        self.assertEqual(grade([], {"a": 1})["ndcg10"], 0)

    def test_no_qrels_refuses(self):
        with self.assertRaises(ValueError):
            grade(["a"], {})

    def test_missing_execution_not_zero(self):
        rows = grade_inventory(["base", "candidate"], ["q"], {"base": {"q": ["d"]}}, [{"query_id": "q", "document_id": "d", "score": 1}], {"d"})
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[1]["metrics"])
        self.assertEqual(rows[1]["status"], "unexecuted")

    def test_grouped_query_weighted_mean(self):
        result = grouped_bootstrap({"a": 1, "b": 1, "c": -1}, [["a", "b"], ["c"]], resamples=100)
        self.assertAlmostEqual(result["mean_difference"], 1/3)
        self.assertEqual(result["group_sizes"], [2, 1])

    def test_missing_pair_blocks(self):
        with self.assertRaises(ValueError):
            grouped_bootstrap({"a": None, "b": 1}, [["a"], ["b"]])

    def test_signflip_zero(self):
        self.assertEqual(grouped_sign_flip({"a": 0, "b": 0}, [["a"], ["b"]], flips=100), 1)

    def test_bh_reference(self):
        self.assertEqual(benjamini_hochberg([0.01, 0.04, 0.03]), [0.03, 0.04, 0.04])

    def test_bh_missing_blocks_family(self):
        with self.assertRaises(ValueError):
            benjamini_hochberg([0.01, None])
