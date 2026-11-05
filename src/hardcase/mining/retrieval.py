import math
import re
from collections import Counter
from hardcase.contracts import require


def words(text):
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


class BM25:
    """Positive Robertson IDF with explicit k1=1.5 and b=0.75."""
    def __init__(self, documents, k1=1.5, b=0.75):
        require(bool(documents), "EMPTY_CORPUS")
        self.ids = sorted(documents)
        self.counts = [Counter(words(documents[d])) for d in self.ids]
        self.lengths = [sum(row.values()) for row in self.counts]
        self.average = sum(self.lengths) / len(self.ids)
        require(self.average > 0, "EMPTY_TOKEN_CORPUS")
        self.df = Counter(term for row in self.counts for term in row)
        self.k1, self.b = k1, b

    def search(self, query, top_k=100):
        terms = words(query)
        scores = []
        n = len(self.ids)
        for doc, counts, length in zip(self.ids, self.counts, self.lengths):
            score = 0.0
            for term in terms:
                frequency = counts.get(term, 0)
                if frequency:
                    df = self.df[term]
                    idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                    score += idf * frequency * (self.k1 + 1) / (frequency + self.k1 * (1 - self.b + self.b * length / self.average))
            scores.append((doc, score))
        return sorted(scores, key=lambda row: (-row[1], row[0]))[:top_k]


def reciprocal_rank_fusion(*rankings, constant=60):
    scores = {}
    for ranking in rankings:
        ids = [r[0] if isinstance(r, (list, tuple)) else r for r in ranking]
        require(len(ids) == len(set(ids)), "DUPLICATE_RANKING_ID")
        for rank, doc in enumerate(ids, 1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (constant + rank)
    return sorted(scores, key=lambda doc: (-scores[doc], doc))


def exact_search(query_vector, matrix, ids, top_k=100):
    import numpy as np
    require(matrix.ndim == 2 and query_vector.shape == (matrix.shape[1],) and len(ids) == matrix.shape[0], "VECTOR_SHAPE")
    require(len(set(ids)) == len(ids) and np.isfinite(query_vector).all() and np.isfinite(matrix).all(), "INVALID_VECTOR_INDEX")
    scores = matrix @ query_vector
    order = np.lexsort((np.asarray(ids), -scores))[:top_k]
    return [(ids[int(i)], float(scores[i])) for i in order]
