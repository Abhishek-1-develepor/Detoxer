"""ml/loader.py — Load trained model + vectorizer once, cache them."""

import pickle
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS = BASE_DIR / "ml_artifacts"

_model = None
_vectorizer = None


def load_artifacts():
    """Load model + vectorizer on first call, then return cached."""
    global _model, _vectorizer

    if _model is None or _vectorizer is None:
        model_path = ARTIFACTS / "model.pkl"
        vec_path   = ARTIFACTS / "vectorizer.pkl"

        if not model_path.exists() or not vec_path.exists():
            raise FileNotFoundError(
                f"Trained artifacts not found in {ARTIFACTS}. "
                "Run accuracy.ipynb to generate model.pkl and vectorizer.pkl."
            )

        with open(model_path, "rb") as f:
            _model = pickle.load(f)
        with open(vec_path, "rb") as f:
            _vectorizer = pickle.load(f)

    return _model, _vectorizer