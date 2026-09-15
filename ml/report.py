"""ml/report.py — Build analysis report for the admin page."""

from ml.predictor import predict_sentiment


def build_review_report(reviews):
    """reviews: list of dicts from DB. Returns summary + enriched reviews."""

    if not reviews:
        return {
            "summary": {
                "total": 0, "avg_rating": 0,
                "positive": 0, "neutral": 0, "negative": 0,
                "positive_pct": 0, "neutral_pct": 0, "negative_pct": 0,
            },
            "rating_buckets": {5: 0, 4: 0, 3: 0, 2: 0, 1: 0},
            "reviews": [],
            "complaints": [],
        }

    enriched = []
    for r in reviews:
        pred = predict_sentiment(r.get("review_text", ""))
        rating = int(r.get("rating", 3))

        # Complaint = negative sentiment OR rating <= 2
        is_complaint = pred["label"] == "negative" or rating <= 2

        enriched.append({
            **r,
            "sentiment": pred["label"],
            "confidence": pred["confidence"],
            "is_complaint": is_complaint,
        })

    total = len(enriched)
    pos = sum(1 for r in enriched if r["sentiment"] == "positive")
    neu = sum(1 for r in enriched if r["sentiment"] == "neutral")
    neg = sum(1 for r in enriched if r["sentiment"] == "negative")

    summary = {
        "total": total,
        "avg_rating": round(sum(r["rating"] for r in enriched) / total, 2),
        "positive": pos, "neutral": neu, "negative": neg,
        "positive_pct": round(pos / total * 100),
        "neutral_pct":  round(neu / total * 100),
        "negative_pct": round(neg / total * 100),
    }

    rating_buckets = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in enriched:
        rating_buckets[r["rating"]] = rating_buckets.get(r["rating"], 0) + 1

    return {
        "summary": summary,
        "rating_buckets": rating_buckets,
        "reviews": enriched,
        "complaints": [r for r in enriched if r["is_complaint"]],
    }