# Sentiment Analyzer API

A FastAPI-based service that ingests social posts/comments, performs sentiment analysis and NER, and builds a lightweight knowledge graph. A Streamlit UI visualizes posts, statistics, and relationships.

## Features
- Sentiment analysis using VADER
- NER via spaCy if available (fallback to regex-based extraction)
- Knowledge graph with NetworkX (users, posts, entities)
- FastAPI endpoints for analysis and graph
- Streamlit UI for visualization

## Setup

### 1) Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Optional: Install spaCy English model for better NER
```bash
python -m spacy download en_core_web_sm
```

### 4) Run the API
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Visit http://localhost:8000/docs for interactive API docs.

### 5) Run the Streamlit UI
```bash
streamlit run app/streamlit_app.py
```
The UI will open at http://localhost:8501.

## API Quickstart

- Analyze sample posts
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "posts": [
      {
        "id": "p1",
        "platform": "twitter",
        "author": "alice",
        "author_id": "u1",
        "text": "Great product launch in Jakarta! Congrats to the team.",
        "timestamp": "2025-12-15T08:00:00Z",
        "url": "https://twitter.com/1"
      }
    ]
  }'
```

- Get latest graph
```bash
curl http://localhost:8000/api/v1/graph
```

## Notes
- This project provides ingestion placeholders; follow each platform's ToS and legal constraints. Prefer official APIs.
- The knowledge graph is ephemeral in-memory for demos. Persist with a DB if needed.
