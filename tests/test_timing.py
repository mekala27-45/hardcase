import unittest
from deploy.compare_timing import aggregate


class TimingTests(unittest.TestCase):
    def rows(self):
        return [{'query_id':str(q),'repeat':r,'encoding_ms':r+1,'search_ms':2,'serialization_ms':3,'total_ms':r+6} for q in range(30) for r in range(5)]

    def test_repeats_aggregate_within_query(self):
        values=aggregate(self.rows())
        self.assertEqual(len(values),30)
        self.assertEqual(values['0']['total_ms'],8)

    def test_missing_and_duplicate_repeat_refused(self):
        rows=self.rows()
        with self.assertRaisesRegex(ValueError,'TIMING_REPEAT_INVENTORY_CHANGED'):
            aggregate(rows[:-1])
        rows[-1]['repeat']=3
        with self.assertRaisesRegex(ValueError,'TIMING_REPEAT_INVENTORY_CHANGED'):
            aggregate(rows)
