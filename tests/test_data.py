import io
import json
import unittest
import zipfile
from hardcase.data.capture import records, judgments, safe_members, normalize
from hardcase.data.grouping import leakage_purge, grouped_split, groups_with_positives, trigrams, similarity


class DataTests(unittest.TestCase):
    def test_clean_records(self):
        self.assertEqual(records(b'{"_id":"01","text":"no effect"}', "queries")["01"]["text"], "no effect")

    def test_missing_inventory(self):
        with self.assertRaisesRegex(ValueError, "EMPTY"):
            records(b"", "queries")

    def test_duplicate_identity(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            records(b'{"_id":"a","text":"x"}\n{"_id":"a","text":"y"}', "queries")

    def test_archive_escape(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("../secret", "x")
        with zipfile.ZipFile(data) as z:
            with self.assertRaisesRegex(ValueError, "UNSAFE"):
                safe_members(z)

    def test_qrel_missing_reference(self):
        with self.assertRaisesRegex(ValueError, "REFERENCE"):
            judgments(b"query-id\tcorpus-id\tscore\nq\td\t1\n", {"q": {}}, {})

    def test_qrel_nonfinite(self):
        with self.assertRaisesRegex(ValueError, "SCORE"):
            judgments(b"query-id\tcorpus-id\tscore\nq\td\tnan\n", {"q": {}}, {"d": {}})

    def test_negation_units_preserved(self):
        self.assertEqual(normalize("  No change at 10 mg.\r\n  "), "No change at 10 mg.")

    def test_text_purge_without_labels(self):
        result = leakage_purge({"a": "No change at 10 mg", "b": "Another observation"}, {"t": "NO change at 10 mg"})
        self.assertEqual(result["purged"], ["a"])
        self.assertEqual(result["test_unchanged"], ["t"])

    def test_shared_positive_transitive(self):
        qs = {"a": "alpha", "b": "beta", "c": "gamma"}
        rows = [{"query_id": q, "document_id": d, "score": 1} for q, d in [("a", "x"), ("b", "x"), ("b", "y"), ("c", "y")]]
        self.assertEqual(groups_with_positives(qs, rows), [["a", "b", "c"]])

    def test_split_independent_of_input_order(self):
        qs = {str(i): f"unique statement {i * 1709}" for i in range(40)}
        rows = [{"query_id": q, "document_id": q, "score": 1} for q in qs]
        a = grouped_split(qs, rows, 2701)
        b = grouped_split(dict(reversed(list(qs.items()))), list(reversed(rows)), 2701)
        self.assertEqual(a, b)
        self.assertFalse(set(a["fit"]) & set(a["validation"]))

    def test_empty_split_refuses(self):
        with self.assertRaises(ValueError):
            grouped_split({}, [], 2701)
