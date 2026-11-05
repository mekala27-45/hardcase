import math
import unittest
from hardcase.mining.retrieval import BM25, reciprocal_rank_fusion
from hardcase.mining.candidates import weak_negatives, sample_schedule, select_checkpoint


class RetrievalTests(unittest.TestCase):
    def test_bm25_hand_reference(self):
        model = BM25({"a": "red red", "b": "blue"})
        expected = math.log(2) * 2 * 2.5 / (2 + 1.5 * (0.25 + 0.75 * 2 / 1.5))
        self.assertAlmostEqual(model.search("red")[0][1], expected)

    def test_stable_tie(self):
        self.assertEqual([r[0] for r in BM25({"z": "red", "a": "red"}).search("missing")], ["a", "z"])

    def test_empty_refuses(self):
        with self.assertRaises(ValueError):
            BM25({})

    def test_fusion_hand_reference(self):
        self.assertEqual(reciprocal_rank_fusion(["b", "a"], ["a", "c"]), ["a", "b", "c"])

    def test_duplicate_ranking_refuses(self):
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion(["a", "a"])

    def test_excludes_all_positives_and_copies(self):
        docs = {str(i): f"document {i}" for i in range(60)} | {"copy": "document 1"}
        result = weak_negatives("q", ["1", "2"], docs, list(docs)[:50], list(reversed(docs))[:50], 2701)
        for key in ("uniform", "hard"):
            self.assertEqual(len(result[key]), 4)
            self.assertFalse({r["id"] for r in result[key]} & {"1", "2", "copy"})
            self.assertTrue(all(r["judgment"] == "unjudged" for r in result[key]))

    def test_shortage_refuses(self):
        with self.assertRaises(ValueError):
            weak_negatives("q", ["a"], {"a": "x"}, [], [], 1)

    def test_schedule_cycle(self):
        schedule = sample_schedule(["b", "a"], {"a": ["x", "y"], "b": ["z"]}, 4, 2701)
        self.assertEqual({r["query_id"] for r in schedule[:2]}, {"a", "b"})
        self.assertEqual([r["positive_id"] for r in schedule if r["query_id"] == "a"], ["x", "y"])

    def test_selection_missing_not_zero(self):
        with self.assertRaises(ValueError):
            select_checkpoint([{"status": "failed", "ndcg10": None}], ["uniform_contrastive"])
