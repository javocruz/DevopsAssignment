def brier_score(probs, outcomes):
    # Nothing to score yet. None is easier to show than a fake zero.
    if not probs:
        return None
    total = 0
    for prob, outcome in zip(probs, outcomes):
        total += (prob - outcome) ** 2
    return total / len(probs)


def calibration_buckets(probs, outcomes, n_buckets=10):
    grouped = {}
    for prob, outcome in zip(probs, outcomes):
        # int(1.0 * 10) is 10, which is past the last bucket, so cap it.
        index = min(int(prob * n_buckets), n_buckets - 1)
        if index not in grouped:
            grouped[index] = {"probs": [], "outcomes": []}
        grouped[index]["probs"].append(prob)
        grouped[index]["outcomes"].append(outcome)

    buckets = []
    for index in sorted(grouped):
        bucket_probs = grouped[index]["probs"]
        bucket_outcomes = grouped[index]["outcomes"]
        low = index / n_buckets
        high = (index + 1) / n_buckets
        buckets.append({
            "range": f"{low:.1f}-{high:.1f}",
            "count": len(bucket_probs),
            "avg_pred": sum(bucket_probs) / len(bucket_probs),
            "actual_rate": sum(bucket_outcomes) / len(bucket_outcomes),
        })
    return buckets
