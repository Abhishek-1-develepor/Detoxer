# Detoxer — E-Commerce Store with ML-Powered Review Sentiment Analysis

A full-stack Flask application that combines an e-commerce store with a
machine learning pipeline that automatically classifies customer reviews
as **positive**, **neutral**, or **negative** — and detects complaints.

Built as an **ML internship project** demonstrating the complete pipeline:

> Data → Cleaning → EDA → Preprocessing → TF-IDF → Model → Evaluation → Deployment

---

## 🎯 Features

### 👤 User Side
- Register / Login (with password hashing)
- Browse product catalogue with images
- Add to cart / Buy now
- Write product reviews (rating + text)
- View order history

### 🛠️ Admin Side
- Dashboard with product stats & inventory
- Add / Edit / Delete products (with image URL)
- Live stock status (In Stock / Low Stock / Critical)
- Export products to CSV

### 🧠 ML-Powered Review Analysis
- Sentiment classification of every review
- Auto-flagging of complaints (negative sentiment OR rating ≤ 2)
- Sentiment summary per product (positive / neutral / negative %)
- Rating breakdown (5★ → 1★)
- Confusion-matrix-based model evaluation in notebook

---

## 🧠 ML Pipeline

```
Raw review text
      │
      ▼
┌─────────────────────────────────┐
│  1. Data Cleaning & EDA          │
│     - remove nulls / duplicates   │
│     - drop < 3-word reviews       │
│     - truncate > 300-word reviews │
│     - rating → label mapping:     │
│         4-5★ → positive           │
│         3★   → neutral            │
│         1-2★ → negative           │
└─────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  2. Text Preprocessing            │
│     - lowercase                   │
│     - remove URLs & punctuation   │
│     - remove stopwords            │
│     - Porter Stemmer              │
└─────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  3. Feature Extraction            │
│     - TF-IDF vectorizer           │
│     - ngram_range = (1, 2)        │
│     - max_features = 10000        │
│     - sublinear_tf = True         │
└─────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  4. Model Training                │
│     - Train/test split (80/20)    │
│     - LinearSVC (C=1.5)           │
│     - class_weight = balanced     │
└─────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  5. Evaluation                    │
│     - Accuracy / Precision        │
│     - Recall / F1 (macro)         │
│     - Confusion matrix            │
└─────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  6. Deployment                    │
│     - Save model.pkl + vectorizer │
│     - Load once in Flask          │
│     - Predict on live reviews     │
└─────────────────────────────────┘
```

---

## 📊 Model Performance

Trained on a **balanced 6,000-row dataset** (2,000 per class).

| Model | Accuracy | F1 (macro) |
|---|---|---|
| Multinomial Naive Bayes (α=1.0) | 75.25% | 0.7501 |
| Multinomial Naive Bayes (α=0.1) | 79.17% | — |
| Logistic Regression (C=1) | 82.17% | — |
| Logistic Regression (C=2) | 84.58% | — |
| **LinearSVC (C=1.5, pos_heavy)** | **86.25%** | **0.8624** |

**Final model**: LinearSVC — **86.25% accuracy**, balanced performance across all 3 classes.

Per-class metrics (final model):

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Negative | 0.86 | 0.86 | 0.86 |
| Neutral | 0.86 | **0.90** | 0.88 |
| Positive | 0.86 | 0.83 | 0.85 |

---

## 🗂️ Project Structure

```
Mini project/
├── app.py                          ← Flask entry point
├── requirements.txt
├── render.yaml                     ← deployment config
├── README.md
│
├── accuracy.ipynb                  ← ML training + evaluation notebook
├── reviews_balanced.csv            ← cleaned, balanced training data
│
├── ml/                             ← ML inference package
│   ├── __init__.py
│   ├── loader.py                   ← load model + vectorizer once
│   ├── predictor.py                ← preprocess + predict
│   └── report.py                   ← build analysis report
│
├── ml_artifacts/                   ← trained model files
│   ├── model.pkl
│   └── vectorizer.pkl
│
├── templates/
│   ├── home.html                   ← landing + login modal
│   ├── dashboard.html              ← admin dashboard
│   ├── product.html                ← user store page
│   ├── orders.html                 ← order history
│   └── admin_ml_reviews.html       ← ML review analysis page
│
└── static/
    ├── style.css                   ← home page styles
    ├── dashboard.css               ← dashboard styles
    ├── dashboard.js                ← dashboard logic
    ├── product.css                 ← store styles
    ├── admin_ml_reviews.css        ← ML page styles
    ├── logo.jpg
    └── rename.gif
```

---

## 🚀 Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/detoxer.git
cd detoxer
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download NLTK data

```bash
python -m nltk.downloader punkt punkt_tab stopwords
```

### 5. Run the app

```bash
python app.py
```

Open: **http://127.0.0.1:5000**

---

## 📓 Retraining the Model

If you change the dataset or want to retrain:

1. Open `accuracy.ipynb` in Jupyter
2. Run all cells sequentially
3. Model artifacts will be saved to `ml_artifacts/`
4. Restart Flask — the new model loads automatically

Or run the retraining script directly:

```bash
python retrain.py
```

---

## ☁️ Deployment

Deployed on **Render.com** (free tier).

### One-click deploy

1. Push the repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repo
4. Render auto-detects `render.yaml`

Or set manually:

| Setting | Value |
|---|---|
| Build Command | `pip install -r requirements.txt && python -m nltk.downloader punkt punkt_tab stopwords` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120` |
| Python Version | `3.10.10` |

### Environment Variables

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.10.10` |
| `FLASK_ENV` | `production` |
| `NLTK_DATA` | `/opt/render/project/src/nltk_data` |

---

## 🔐 Default Credentials

Register your own admin/user accounts. No accounts are seeded by default.

Example:
- Register as **admin** → add products, view ML analysis
- Register as **user** → browse, buy, write reviews

---

## 🧪 Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | Flask 3.0 |
| Database | SQLite |
| ML Library | scikit-learn 1.7 |
| NLP | NLTK (tokenize, stopwords, stemmer) |
| Data | pandas, numpy |
| Deployment | Gunicorn + Render |

---

## 📚 Learnings

This project demonstrates:

- End-to-end ML pipeline (data → model → deployment)
- Handling class imbalance via undersampling + oversampling
- Text preprocessing with NLTK
- TF-IDF feature engineering
- Comparing multiple classifiers
- Model persistence with pickle
- Serving ML predictions through a REST API
- Flask blueprint-style architecture (models / services / controllers)
- Deploying ML apps on free tier platforms

---

## 🧑‍💻 Author

**Your Name**
- GitHub: [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)
- Email: your@email.com

---

## 📝 License

MIT License — free to use for learning and portfolio purposes.