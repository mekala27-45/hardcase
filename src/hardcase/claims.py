"""The only renderer for measured numeric prose."""
from pathlib import Path
from .contracts import digest, finite, load_json, require

NAMESPACES = {"data_inventory", "actual_training", "teacher_supervision", "retrieval_quality", "export_parity", "serving_measurement", "scripted_release", "live_request"}


def validate_measurement(item):
    require(isinstance(item, dict), "MISSING_EVIDENCE")
    require(item.get("namespace") in NAMESPACES, "UNKNOWN_EVIDENCE_MODE")
    for key in ("method", "split", "aggregation", "unit", "started_at", "ended_at", "source"):
        require(isinstance(item.get(key), str) and bool(item[key].strip()), f"MISSING_{key.upper()}")
    require(item.get("status") in {"observed", "failed", "pending"}, "UNKNOWN_STATUS")
    require(item.get("kind") == "observed", "PLANNED_IS_NOT_OBSERVED")
    require(isinstance(item.get("denominator"), int) and item["denominator"] > 0, "INVALID_DENOMINATOR")
    require(len(item.get("source_digest", "")) == 64 and all(c in "0123456789abcdef" for c in item["source_digest"]), "INVALID_SOURCE_DIGEST")
    require(item["started_at"] <= item["ended_at"], "INVALID_WINDOW")
    if item["status"] == "observed":
        require(finite(item.get("value")), "OBSERVATION_REQUIRED")
    else:
        require(item.get("value") is None, "FAILED_OR_PENDING_NUMBER")
    require(not(item["namespace"] == "live_request" and item.get("fresh") and item.get("replayed")), "REPLAY_IS_NOT_FRESH")
    return item


def render_measurement(item, source_bytes=None):
    item = validate_measurement(item)
    if source_bytes is not None:
        import hashlib
        require(hashlib.sha256(source_bytes).hexdigest() == item["source_digest"], "SOURCE_CHANGED")
    value = format(item["value"], ".8g") if item["status"] == "observed" else "not measured"
    return f"{item['method']} | {item['aggregation']} | {value} {item['unit']} | denominator {item['denominator']} | {item['split']} | {item['namespace']} | {item['started_at']} to {item['ended_at']} | source {item['source']} ({item['source_digest']})"


CHECKLIST = [
    "Scaffold, preregistration and actual gradient/export/free-host probes.",
    "Evidence-bound claim renderer with missing-data and mode checks.",
    "Licensed data capture, grouped splits, purge and frozen inventories.",
    "Full-corpus BM25 and unchanged encoder baselines with independent checks.",
    "Frozen weak-negative lists, actual teacher scores and recorded audit.",
    "Three actual training arms, parameter-change evidence and validation selection.",
    "Working float32 ONNX, quantization investigation and matched resource evidence.",
    "Compatible bundle registry with atomic aliases, promotion and rollback rules.",
    "Live learned inference verified by browser, separate client and fresh DB read.",
    "Complete frozen held-out rankings, independent metrics and paired analysis.",
    "Measured serving stages, memory, admission behavior and bounded public smoke.",
    "Evidence-bound release decision and all six independently observed fault cases.",
    "Five working views with genuine live search and inspectable model evidence.",
    "Both validated themes, primary fonts and responsive accessibility checks.",
    "Agent guidance, three skills, SPEC, model cards, notices and operating notes.",
    "Passing CI, bounded worker requests and retained artifact provenance.",
    "Clean-worktree rederivation and final live artifact/persistence verification.",
    "Authorized release and tag after commits with this evidence checklist.",
]


def render_checklist(evidence):
    lines = []
    for index, title in enumerate(CHECKLIST, 1):
        row = evidence.get(str(index), {})
        done = row.get("status") == "done" and row.get("evidence") and row.get("verified") is True
        lines.append(f"{index}  {'done' if done else 'not done'}: {title}\n   Evidence: {row.get('evidence', 'Required execution evidence is missing.')}")
    return "\n".join(lines)


def render_results(root):
    root = Path(root)
    state_path = root / "evidence/completion.json"
    state = load_json(state_path) if state_path.exists() else {}
    statement = (root / "docs/STATEMENT.txt").read_text()
    body = "# Hardcase results\n\n" + statement + "\n## Completion evidence\n\n" + render_checklist(state) + "\n"
    (root / "RESULTS.md").write_text(body, encoding="utf-8")
    return body


if __name__ == "__main__":
    render_results(Path.cwd())
