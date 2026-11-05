import math
import random
from hardcase.contracts import require


def quantile(values, probability):
    values = sorted(values)
    position = (len(values) - 1) * probability
    lo, hi = math.floor(position), math.ceil(position)
    return values[lo] * (hi - position) + values[hi] * (position - lo) if lo != hi else values[lo]


def paired_groups(differences, groups):
    members = [q for group in groups for q in group]
    require(members and len(members) == len(set(members)) and set(members) == set(differences), "INCOMPLETE_PAIRED_INVENTORY")
    require(all(value is not None and math.isfinite(value) for value in differences.values()), "MISSING_PAIRED_VALUE")
    return [(sum(differences[q] for q in group), len(group)) for group in groups]


def grouped_bootstrap(differences, groups, seed=2701, resamples=10000):
    rows = paired_groups(differences, groups)
    require(len(rows) >= 2 and resamples > 1, "INSUFFICIENT_INDEPENDENT_GROUPS")
    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        sampled = [rows[rng.randrange(len(rows))] for _ in rows]
        draws.append(sum(x for x, _ in sampled) / sum(n for _, n in sampled))
    return {"mean_difference": sum(differences.values()) / len(differences), "lower": quantile(draws, 0.025), "upper": quantile(draws, 0.975), "groups": len(groups), "queries": len(differences), "group_sizes": [len(g) for g in groups], "resamples": resamples, "seed": seed, "algorithm": "whole-group percentile bootstrap with linear quantiles and query weighting", "degenerate": min(draws) == max(draws)}


def grouped_sign_flip(differences, groups, seed=2701, flips=10000):
    rows = paired_groups(differences, groups)
    observed = abs(sum(differences.values()) / len(differences))
    rng = random.Random(seed)
    at_least = 0
    for _ in range(flips):
        statistic = abs(sum(total * rng.choice((-1, 1)) for total, _ in rows) / len(differences))
        at_least += statistic >= observed - 1e-15
    return (at_least + 1) / (flips + 1)


def benjamini_hochberg(p_values):
    require(bool(p_values) and all(p is not None and 0 <= p <= 1 for p in p_values), "INCOMPLETE_COMPARISON_FAMILY")
    order = sorted(range(len(p_values)), key=lambda i: (p_values[i], i))
    result = [None] * len(order)
    previous = 1.0
    for rank in range(len(order), 0, -1):
        index = order[rank - 1]
        previous = min(previous, p_values[index] * len(order) / rank)
        result[index] = previous
    return result
