import math
from hardcase.contracts import require


def grade(ranking, relevance):
    require(bool(relevance) and any(v > 0 for v in relevance.values()), "NO_USABLE_QRELS")
    require(len(ranking) == len(set(ranking)), "DUPLICATE_RETRIEVED_ID")
    require(all(math.isfinite(v) and v >= 0 for v in relevance.values()), "INVALID_QRELS")
    positive = {d for d, score in relevance.items() if score > 0}
    gains = [2**relevance.get(d, 0) - 1 for d in ranking[:10]]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted((2**score - 1 for score in relevance.values() if score > 0), reverse=True)[:10]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return {"ndcg10": dcg / idcg, "recall10": len(set(ranking[:10]) & positive) / len(positive), "recall100": len(set(ranking[:100]) & positive) / len(positive), "mrr10": next((1 / rank for rank, d in enumerate(ranking[:10], 1) if d in positive), 0.0)}


def qrel_map(rows):
    result = {}
    for row in rows:
        result.setdefault(row["query_id"], {})[row["document_id"]] = row["score"]
    return result


def grade_inventory(methods, query_ids, rankings, qrels, corpus_ids):
    rows = []
    gold = qrel_map(qrels)
    for method in methods:
        for query_id in sorted(query_ids):
            record = rankings.get(method, {}).get(query_id)
            row = {"method": method, "query_id": query_id, "status": "unexecuted", "metrics": None}
            if record is not None:
                try:
                    require(set(record).issubset(corpus_ids), "OUT_OF_CORPUS_RESULT")
                    row.update(status="completed", metrics=grade(record, gold.get(query_id, {})))
                except ValueError as error:
                    row.update(status="failed", error=str(error))
            rows.append(row)
    return rows
