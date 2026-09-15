"""
retrain.py — Retrain the sentiment model with the current venv's NumPy.

Run from the project root with the venv activated:
    python retrain.py

Expects:
    reviews_balanced.csv  — already cleaned and balanced dataset (from notebook)

Produces:
    ml_artifacts/model.pkl
    ml_artifacts/vectorizer.pkl
"""

import os
import re
import pickle
import numpy as np
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, f1_score, classification_report

# ============================================================
# 0. Setup
# ============================================================
print("=" * 60)
print("RETRAIN — Sentiment Model")
print("=" * 60)
print(f"Python: {__import__('sys').version.split()[0]}")
print(f"NumPy : {np.__version__}")
print(f"sklearn: {__import__('sklearn').__version__}")
print()

# NLTK data
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)

# ============================================================
# 1. Load dataset
# ============================================================
DATASET = "reviews_balanced.csv"

if not os.path.exists(DATASET):
    raise FileNotFoundError(
        f"{DATASET} not found. Run accuracy.ipynb up to the balancing step first, "
        f"or provide the CSV in the project root."
    )

df = pd.read_csv(DATASET)
print(f"Dataset loaded: {len(df)} rows")
print(f"Columns: {df.columns.tolist()}")
print(f"\nClass distribution:\n{df['label'].value_counts()}\n")

# ============================================================
# 2. Preprocess (must match notebook)
# ============================================================
stop_words = set(stopwords.words("english"))
stemmer = PorterStemmer()


def preprocess(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-z\s]", "", text)
    tokens = text.split()
    tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
    tokens = [stemmer.stem(t) for t in tokens]
    return " ".join(tokens)


print("Preprocessing...")
df["clean_text"] = df["text"].apply(preprocess)
print(f"Sample raw  : {df['text'].iloc[0][:80]}")
print(f"Sample clean: {df['clean_text'].iloc[0][:80]}\n")

# ============================================================
# 3. Split
# ============================================================
X = df["clean_text"]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train)}  Test: {len(X_test)}\n")

# ============================================================
# 4. TF-IDF
# ============================================================
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=10000,
    min_df=2,
    max_df=0.95,
    sublinear_tf=True,
)

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec  = vectorizer.transform(X_test)
print(f"Vocabulary: {len(vectorizer.vocabulary_)}")
print(f"Train matrix: {X_train_vec.shape}\n")

# ============================================================
# 5. Train
# ============================================================
model = LinearSVC(
    C=1.5,
    class_weight={"negative": 1.0, "neutral": 1.0, "positive": 1.3},
    max_iter=3000,
)
model.fit(X_train_vec, y_train)
print("✅ Model trained\n")

# ============================================================
# 6. Evaluate
# ============================================================
y_pred = model.predict(X_test_vec)

acc = accuracy_score(y_test, y_pred)
f1  = f1_score(y_test, y_pred, average="macro")

print(f"Accuracy : {acc:.4f}")
print(f"F1 macro : {f1:.4f}\n")
print("Classification Report:")
print(classification_report(y_test, y_pred, zero_division=0))

# ============================================================
# 7. Save with CURRENT numpy
# ============================================================
os.makedirs("ml_artifacts", exist_ok=True)

with open("ml_artifacts/model.pkl", "wb") as f:
    pickle.dump(model, f)
with open("ml_artifacts/vectorizer.pkl", "wb") as f:
    pickle.dump(vectorizer, f)

print("=" * 60)
print(f"✅ Saved with NumPy {np.__version__}")
print(f"   ml_artifacts/model.pkl")
print(f"   ml_artifacts/vectorizer.pkl")
print("=" * 60)

# ============================================================
# 8. Verify it loads
# ============================================================
with open("ml_artifacts/model.pkl", "rb") as f:
    m = pickle.load(f)

with open("ml_artifacts/vectorizer.pkl", "rb") as f:
    v = pickle.load(f)

print(f"\nVerify load:")
print(f"  Model type     : {type(m).__name__}")
print(f"  Vectorizer type: {type(v).__name__}")
print(f"  Classes        : {m.classes_}")

# Quick predict test
test_text = preprocess("Absolutely amazing product, works perfectly!")
vec = v.transform([test_text])
print(f"\nTest prediction: {m.predict(vec)[0]}")
print("\n✅ Done. Restart Flask and open the ML analysis page.")