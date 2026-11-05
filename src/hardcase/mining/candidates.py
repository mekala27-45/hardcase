from hardcase.contracts import digest, require
from hardcase.data.grouping import audit_text
from .retrieval import reciprocal_rank_fusion


def weak_negatives(query_id, positives, documents, bm25, dense, seed, count=4):
    positives = sorted(set(positives))
    require(positives and all(p in documents for p in positives), "MISSING_POSITIVE")
    positive_texts = {audit_text(documents[d]) for d in positives}
    eligible = sorted(d for d, text in documents.items() if d not in positives and audit_text(text) not in positive_texts)
    require(len(eligible) >= count, "INSUFFICIENT_WEAK_NEGATIVES")
    uniform = sorted(eligible, key=lambda d: (digest([seed, query_id, "uniform", d]), d))[:count]
    fused = reciprocal_rank_fusion(bm25, dense, constant=60)
    ranks = {doc: i for i, doc in enumerate(fused, 1)}
    hard_pool = [d for d in fused[4:50] if d in set(eligible)]
    hard = sorted(hard_pool, key=lambda d: (digest([seed, query_id, "mined", d]), d))[:count]
    fills = []
    for d in sorted(eligible, key=lambda d: (digest([seed, query_id, "fill", d]), d)):
        if len(hard) == count:
            break
        if d not in hard:
            hard.append(d)
            fills.append(d)
    result = {"query_id": query_id, "positives": positives, "uniform": [{"id": d, "judgment": "unjudged", "route": "uniform", "reason": "eligible nonpositive with nonduplicate text"} for d in uniform], "hard": [{"id": d, "judgment": "unjudged", "route": "uniform_fill" if d in fills else "fused_rank_window", "fused_rank": ranks.get(d), "reason": "eligible nonpositive with nonduplicate text"} for d in hard], "fused_ranking": fused, "fills": fills}
    result["digest"] = digest(result)
    return result


def sample_schedule(query_ids, positives, examples, seed):
    require(query_ids and examples >= len(query_ids), "SCHEDULE_MUST_COVER_FIT")
    require(len(query_ids) == len(set(query_ids)), "DUPLICATE_QUERY_ID")
    base = sorted(query_ids, key=lambda q: (digest([seed, "schedule", q]), q))
    seen = {q: 0 for q in base}
    schedule = []
    for index in range(examples):
        q = base[index % len(base)]
        choices = sorted(set(positives[q]))
        require(choices, "MISSING_POSITIVE")
        selected = choices[seen[q] % len(choices)]
        seen[q] += 1
        schedule.append({"example": index, "query_id": q, "positive_id": selected})
    return schedule


def select_checkpoint(rows, arm_order, epsilon=1e-6):
    valid = [r for r in rows if r["status"] == "completed" and r.get("ndcg10") is not None]
    require(valid, "NO_VALIDATION_EVIDENCE")
    highest = max(r["ndcg10"] for r in valid)
    tied = [r for r in valid if highest - r["ndcg10"] <= epsilon]
    return min(tied, key=lambda r: (arm_order.index(r["arm"]), r["update"]))
