from hardcase.contracts import digest, finite


def release_gate(evidence, policy):
    """Absent measurements are failed checks, never numeric zero."""
    checks = []
    def check(name, observed, predicate, threshold):
        passed = observed is not None and predicate(observed)
        checks.append({"name": name, "passed": bool(passed), "observed": observed, "threshold": threshold})
    check("three_arms_complete", evidence.get("three_arms_complete"), lambda v: v is True, True)
    check("validation_gain", evidence.get("validation_gain"), lambda v: finite(v) and v >= policy["validation_gain_min"], policy["validation_gain_min"])
    check("float32_parity", evidence.get("float32_parity"), lambda v: v is True, True)
    check("heldout_complete", evidence.get("heldout_complete"), lambda v: v is True, True)
    check("test_gain", evidence.get("test_gain"), lambda v: finite(v) and v >= policy["test_gain_min"], policy["test_gain_min"])
    check("grouped_interval_lower", evidence.get("interval_lower"), lambda v: finite(v) and v > policy["interval_lower_exclusive"], policy["interval_lower_exclusive"])
    check("recall100_change", evidence.get("recall100_change"), lambda v: finite(v) and v >= policy["recall100_change_min"], policy["recall100_change_min"])
    check("warm_p95_ms", evidence.get("warm_p95_ms"), lambda v: finite(v) and 0 < v < policy["warm_p95_ms_max"], policy["warm_p95_ms_max"])
    check("peak_rss_mib", evidence.get("peak_rss_mib"), lambda v: finite(v) and 0 < v < policy["peak_rss_mib_max"], policy["peak_rss_mib_max"])
    check("live_bundle_verified", evidence.get("live_bundle_verified"), lambda v: v is True, True)
    return {"passed": all(r["passed"] for r in checks), "checks": checks, "policy_digest": digest(policy), "evidence_digest": digest(evidence)}
