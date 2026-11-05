import hashlib
import unittest
from hardcase.claims import render_measurement, render_checklist


class ClaimTests(unittest.TestCase):
    def setUp(self):
        self.item = dict(namespace="actual_training", method="uniform_contrastive", split="fit", aggregation="optimizer_updates", unit="updates", started_at="2026-11-05T00:00:00Z", ended_at="2026-11-05T01:00:00Z", source="evidence/train.json", source_digest=hashlib.sha256(b"sample").hexdigest(), status="observed", kind="observed", denominator=1, value=120)

    def test_clean_source(self):
        self.assertIn("120 updates", render_measurement(self.item, b"sample"))

    def test_changed_source(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_CHANGED"):
            render_measurement(self.item, b"other")

    def test_missing(self):
        with self.assertRaises(ValueError):
            render_measurement({})

    def test_planned_not_observed(self):
        with self.assertRaisesRegex(ValueError, "PLANNED"):
            render_measurement(self.item | {"kind": "planned"})

    def test_nonfinite(self):
        with self.assertRaises(ValueError):
            render_measurement(self.item | {"value": float("nan")})

    def test_null_not_zero(self):
        self.assertIn("not measured", render_measurement(self.item | {"status": "pending", "value": None}))

    def test_replay_not_fresh(self):
        with self.assertRaisesRegex(ValueError, "REPLAY"):
            render_measurement(self.item | {"namespace": "live_request", "fresh": True, "replayed": True})

    def test_checklist_fails_closed(self):
        text = render_checklist({"1": {"status": "done", "evidence": "code exists"}})
        self.assertIn("1  not done", text)
        self.assertEqual(text.count("not done:"), 18)
