import unittest
from hardcase.contracts import load_json
from hardcase.registry.gates import release_gate


class GateTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_json("requests/experiment.json")["promotion"]
        self.good = {"three_arms_complete": True, "validation_gain": 0.02, "float32_parity": True, "heldout_complete": True, "test_gain": 0.01, "interval_lower": -0.005, "recall100_change": 0.0, "warm_p95_ms": 500, "peak_rss_mib": 500, "live_bundle_verified": True}

    def test_clean(self):
        self.assertTrue(release_gate(self.good, self.policy)["passed"])

    def test_each_violation_refuses(self):
        for key, value in {"three_arms_complete": False, "validation_gain": 0.009, "float32_parity": False, "heldout_complete": False, "test_gain": -0.001, "interval_lower": -0.01, "recall100_change": -0.021, "warm_p95_ms": 1500, "peak_rss_mib": 768, "live_bundle_verified": False}.items():
            with self.subTest(key=key):
                self.assertFalse(release_gate(self.good | {key: value}, self.policy)["passed"])

    def test_missing_evidence_refuses(self):
        self.assertFalse(release_gate({}, self.policy)["passed"])
