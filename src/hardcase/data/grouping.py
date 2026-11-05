import unicodedata
from hardcase.contracts import digest, require


def audit_text(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def trigrams(text):
    text = audit_text(text)
    return {text[i:i + 3] for i in range(max(1, len(text) - 2))}


def similarity(left, right):
    union = left | right
    return len(left & right) / len(union) if union else 1.0


class Components:
    def __init__(self, ids):
        self.parent = {x: x for x in sorted(ids)}

    def find(self, node):
        while node != self.parent[node]:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, a, b):
        a, b = sorted((self.find(a), self.find(b)))
        self.parent[b] = a

    def groups(self):
        groups = {}
        for node in sorted(self.parent):
            groups.setdefault(self.find(node), []).append(node)
        return list(groups.values())


def text_groups(queries, threshold=0.9):
    components = Components(queries)
    ids = sorted(queries)
    grams = {q: trigrams(queries[q]) for q in ids}
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if similarity(grams[a], grams[b]) >= threshold:
                components.union(a, b)
    return components


def leakage_purge(train, test, threshold=0.9):
    require(not set(train) & set(test), "SPLIT_ID_COLLISION")
    components = text_groups(train | test, threshold)
    test_roots = {components.find(q) for q in test}
    purged = sorted(q for q in train if components.find(q) in test_roots)
    return {"kept": sorted(set(train) - set(purged)), "purged": purged, "test_unchanged": sorted(test), "rule": "NFC casefold whitespace character trigram Jaccard connected components", "threshold": threshold, "audit_inputs": "train and test query text only; no test relevance labels"}


def groups_with_positives(queries, qrels, threshold=0.9):
    components = text_groups(queries, threshold)
    doc_queries = {}
    for row in qrels:
        if row["query_id"] in queries and row["score"] > 0:
            doc_queries.setdefault(row["document_id"], []).append(row["query_id"])
    for ids in doc_queries.values():
        for other in ids[1:]:
            components.union(ids[0], other)
    return components.groups()


def grouped_split(queries, qrels, seed, fraction=0.2, threshold=0.9):
    require(0 < fraction < 1 and bool(queries), "INVALID_SPLIT_INPUT")
    groups = groups_with_positives(queries, qrels, threshold)
    rows, fit, validation = [], [], []
    for group in sorted(groups, key=lambda g: g[0]):
        key = digest({"seed": seed, "members": group})
        split = "validation" if int(key, 16) / 2**256 < fraction else "fit"
        (validation if split == "validation" else fit).extend(group)
        rows.append({"group_id": key, "members": group, "split": split})
    require(fit and validation, "EMPTY_GROUPED_PARTITION")
    fit_docs = {r["document_id"] for r in qrels if r["score"] > 0 and r["query_id"] in set(fit)}
    validation_docs = {r["document_id"] for r in qrels if r["score"] > 0 and r["query_id"] in set(validation)}
    require(not fit_docs & validation_docs, "SUPERVISION_DOC_OVERLAP")
    return {"fit": sorted(fit), "validation": sorted(validation), "groups": rows, "positive_document_overlap": 0, "seed": seed}
