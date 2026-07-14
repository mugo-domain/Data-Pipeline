# App Sentiment Analysis Pipeline

An automated, end-to-end pipeline for scraping Google Play Store reviews, running NLP sentiment inference, storing results in a MySQL database, and surfacing insights in a Power BI dashboard. Built and validated on the **Safaricom MyOne App** (cross-validated F1 ≈ 0.90); configurable for any app on the Play Store.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Setup & Installation](#setup--installation)
6. [Configuration](#configuration)
7. [Running the Pipeline](#running-the-pipeline)
8. [Model Details](#model-details)
9. [Database Schema](#database-schema)
10. [Power BI Dashboard](#power-bi-dashboard)
11. [Adapting to a Different App](#adapting-to-a-different-app)
12. [Results](#results)

---

## Overview

This pipeline answers one question continuously: **how do users feel about your app, and is that changing over time?**

It runs weekly (or on demand), pulls the latest Play Store reviews, classifies each one as Positive, Negative, or Neutral, and writes the results to a MySQL table that a Power BI dashboard reads directly. No manual steps after initial setup.

**Key capability:** the entire stack from scraper to dashboard is automated via a `.bat` runner script (Windows). Replace the app ID in the config and the pipeline works for any Play Store app.

---

## Architecture

```
Google Play Store
       │
       ▼
 [ Scraper ]          google-play-scraper / requests
       │
       ▼
 [ NLP Cleaning ]     lowercasing, punctuation, stopword removal
       │
       ▼
 [ Feature Extraction ]   Word2Vec embeddings (trained on review corpus)
       │
       ▼
 [ LightGBM Classifier ]  Positive / Negative
       │
       ▼
 [ MySQL Database ]    reviews table with predictions + metadata
       │
       ▼
 [ Power BI Dashboard ]   weekly refresh, DAX measures, trend visuals
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Scraping | `google-play-scraper` (Python) |
| NLP Cleaning | `re`, `nltk` |
| Embeddings | `gensim` Word2Vec |
| Classification | `lightgbm` |
| Storage | MySQL (`mysql-connector-python`) |
| Visualisation | Power BI Desktop (DirectQuery / scheduled refresh) |
| Automation | Windows `.bat` script + Task Scheduler |
| Environment | Python 3.11 virtual environment |

---

## Project Structure

```
app-sentiment-pipeline/
│
├── data/
│   ├── raw/                  # Raw scraped reviews (JSON)
│   └── processed/            # Cleaned reviews ready for inference
│
├── models/
│   ├── word2vec.model        # Trained Word2Vec model
│   └── lgbm_sentiment.pkl    # Trained LightGBM classifier
│
├── src/
│   ├── scraper.py            # Pulls reviews from Play Store
│   ├── clean.py              # NLP preprocessing
│   ├── embed.py              # Word2Vec averaging → feature vectors
│   ├── infer.py              # LightGBM inference
│   └── db_writer.py          # Writes predictions to MySQL
│
├── notebooks/
│   ├── 01_eda.ipynb          # Exploratory analysis on raw reviews
│   ├── 02_train_word2vec.ipynb
│   └── 03_train_lgbm.ipynb   # Model training + cross-validation
│
├── dashboard/
│   └── sentiment_dashboard.pbix   # Power BI file
│
├── run_pipeline.bat           # One-click pipeline runner (Windows)
├── config.py                  # All configurable settings in one place
├── requirements.txt
└── README.md
```

---

## Setup & Installation

**Prerequisites:** Python 3.11, MySQL Server, Power BI Desktop.

```bash
# 1. Clone the repo
git clone https://github.com/your-username/app-sentiment-pipeline.git
cd app-sentiment-pipeline

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up the MySQL database
mysql -u root -p < schema.sql
```

**requirements.txt**
```
google-play-scraper
nltk
gensim
lightgbm
scikit-learn
mysql-connector-python
pandas
numpy
python-dotenv
```

---

## Configuration

All settings live in `config.py` — edit this file to point the pipeline at a different app or database.

```python
# config.py

# ── App ──────────────────────────────────────────────────────────────────────
APP_ID     = "com.safaricom.myone"   # Change this to any Play Store app ID
APP_LANG   = "en"
APP_COUNTRY = "ke"
REVIEWS_PER_RUN = 500                # How many reviews to pull each run

# ── Database ──────────────────────────────────────────────────────────────────
DB_HOST = "localhost"
DB_NAME = "sentiment_db"
DB_USER = "root"
DB_PASSWORD = ""   

# ── Model Paths ───────────────────────────────────────────────────────────────
WORD2VEC_PATH = "models/word2vec.model"
LGBM_PATH     = "models/lgbm_sentiment.pkl"
```

Store your DB password in a `.env` file and load it with `python-dotenv`.

---

## Running the Pipeline

**Single run (terminal):**
```bash
python src/scraper.py
python src/clean.py
python src/embed.py
python src/infer.py
python src/db_writer.py
```

**One-click (Windows):**
```bat
:: run_pipeline.bat
@echo off
call venv\Scripts\activate
python src/scraper.py
python src/clean.py
python src/embed.py
python src/infer.py
python src/db_writer.py
echo Pipeline complete.
pause
```

**Scheduled weekly run:** add `run_pipeline.bat` to Windows Task Scheduler.

---

## Model Details

### Preprocessing
- Lowercase, strip punctuation and URLs
- Remove English stopwords (NLTK)
- Tokenise

### Embeddings
- Word2Vec trained on the full review corpus (skip-gram, vector size 100, window 5)
- Review embedding = mean of all token vectors

### Classifier
- LightGBM multi-class (Positive / Negative / Neutral)
- Labels derived from star ratings: 4–5 → Positive, 3 → Neutral, 1–2 → Negative
- Cross-validated macro F1: **≈ 0.90**

### Training data
The initial model was trained on Safaricom MyOne App reviews. For a new app, retrain using `notebooks/03_train_lgbm.ipynb` after collecting enough reviews — typically 1,000+ labelled examples give stable results.

---

## Database Schema

```sql
CREATE TABLE reviews (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    review_id     VARCHAR(255) UNIQUE,
    app_id        VARCHAR(255),
    review_text   TEXT,
    star_rating   TINYINT,
    review_date   DATE,
    sentiment     VARCHAR(20),          -- Positive / Negative / Neutral
    confidence    FLOAT,
    inserted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Power BI Dashboard

Connect Power BI to the MySQL `reviews` table using the MySQL connector.

**Key DAX measure — % Positive sentiment:**
```dax
% Positive =
DIVIDE(
    COUNTROWS(FILTER(reviews, reviews[sentiment] = "Positive")),
    COUNTROWS(reviews)
)
```

Suggested visuals:
- Weekly % Positive trend line (reveals dips after app updates or outages)
- Sentiment breakdown donut chart
- Raw review table with sentiment label and confidence score
- Word cloud of most frequent terms per sentiment class

---

## Adapting to a Different App

1. Update `APP_ID` in `config.py` to the target app's Play Store package name.
   - Example: `com.instagram.android`, `com.kopo.android`, `com.equitybank.android`
2. Run the scraper to collect reviews.
3. Retrain Word2Vec and LightGBM using the new corpus (`notebooks/02` and `03`).
4. Save updated models to `models/`.
5. Run the pipeline — everything downstream is unchanged.

The cleaning, embedding, and inference code has no app-specific logic. Only the model weights need retraining when switching apps.

---

## Results

Validated on Safaricom MyOne App reviews:

| Metric | Value |
|---|---|
| Cross-validated macro F1 | ≈ 0.90 |
| Classes | Positive, Negative, Neutral |
| Pipeline frequency | Weekly automated run |
| Dashboard metric | % Positive sentiment (DAX) |

A Q2 dip in % Positive sentiment was identified during live monitoring, demonstrating the pipeline's ability to surface real product signals.

---

## Author

**Centi (Emmanuel Mugo)**
Data Science · NLP · Applied ML
[LinkedIn](https://linkedin.com/in/emmanuel-mugo) · [GitHub](https://github.com/your-username)
