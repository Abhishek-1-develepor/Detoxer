"""ml/predictor.py — Preprocess + predict sentiment. Pure inference only."""

import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

from ml.loader import load_artifacts

# ------------------------------------------------------------
# Preprocessing — MUST match the notebook exactly
# ------------------------------------------------------------
_stop_words = set(stopwords.words("english"))
_stemmer = PorterStemmer()


def preprocess(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-z\s]", "", text)
    tokens = text.split()
    tokens = [t for t in tokens if t not in _stop_words and len(t) > 2]
    tokens = [_stemmer.stem(t) for t in tokens]
    return " ".join(tokens)


# ------------------------------------------------------------
# Predict
# ------------------------------------------------------------
def predict_sentiment(text: str) -> dict:
    """
    Returns:
        {
            "label": "positive" | "neutral" | "negative",
            "confidence": float (0..1)
        }
    """
    model, vectorizer = load_artifacts()

    clean = preprocess(text)
    if not clean.strip():
        return {"label": "neutral", "confidence": 0.0}

    vec = vectorizer.transform([clean])

    label = model.predict(vec)[0]

    # LinearSVC has no predict_proba — use decision_function as confidence proxy
    try:
        scores = model.decision_function(vec)[0]
        # Softmax over decision scores for a rough confidence
        import numpy as np
        exp = np.exp(scores - scores.max())
        proba = exp / exp.sum()
        confidence = float(proba.max())
    except Exception:
        confidence = 1.0

    return {
        "label": str(label),
        "confidence": round(confidence, 3),
    }