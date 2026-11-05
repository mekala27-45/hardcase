"""Run as an independent process to keep Torch memory out of serving evidence."""
import json
import sys
import time
from pathlib import Path
from hardcase.contracts import atomic_json, load_json, utcnow
from .bundle import Bundle


def main():
    import psutil
    process = psutil.Process()
    start = time.perf_counter()
    bundle = Bundle(sys.argv[1])
    cold_load_ms = (time.perf_counter() - start) * 1000
    companion = Bundle(sys.argv[4]) if len(sys.argv) > 4 else None
    queries = load_json(sys.argv[2])
    for query in queries[:3]:
        bundle.search(query["text"])
    observations = []
    rss = process.memory_info().rss
    for repeat in range(5):
        for query in queries:
            start = time.perf_counter()
            results, timing = bundle.search(query["text"])
            serialize_start = time.perf_counter()
            json.dumps(results, allow_nan=False)
            timing["serialization_ms"] = (time.perf_counter() - serialize_start) * 1000
            timing["total_ms"] = (time.perf_counter() - start) * 1000
            rss = max(rss, process.memory_info().rss)
            observations.append({"query_id": query["id"], "repeat": repeat, **timing})
    ordered = sorted(r["total_ms"] for r in observations)
    try:
        import resource
        rss = max(rss, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024))
    except ImportError:
        rss = max(rss, getattr(process.memory_info(), 'peak_wset', rss))
    result = {"namespace": "serving_measurement", "bundle_id": bundle.id, "companion_bundle": companion.id if companion else None, "cold_load_ms": cold_load_ms, "peak_rss_mib": rss / 1024**2, "warm_p95_ms": ordered[int(0.95 * (len(ordered) - 1))], "observations": observations, "queries": len(queries), "repeats": 5, "warmup_queries": min(3, len(queries)), "measured_at": utcnow(), "torch_imported": "torch" in sys.modules, "measurement": "CPU inference and serialization; network and DB excluded"}
    atomic_json(sys.argv[3], result)


if __name__ == "__main__":
    main()
