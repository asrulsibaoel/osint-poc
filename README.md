# Sentiment Analyzer API

A FastAPI-based service that ingests social posts/comments, performs sentiment analysis and NER, and builds a persistent knowledge graph using Neo4j. A Streamlit UI visualizes posts, statistics, and relationships.

## Features
- Sentiment analysis using VADER
- NER via spaCy if available (fallback to regex-based extraction)
- **Persistent Knowledge graph with Neo4j** (users, posts, entities)
- FastAPI endpoints for analysis and graph
- Streamlit UI for visualization
- **Docker & Docker Compose for easy deployment**

## Quick Start with Docker (Recommended)

### 1) Clone and start all services
```bash
# Clone the repository
git clone <repo-url>
cd osint-poc

# Copy environment file and customize if needed
cp .env.example .env

# Start all services (API, Neo4j, PostgreSQL, Streamlit)
docker-compose up -d
```

### 2) Access the services
- **API**: http://localhost:8080/docs (Swagger UI)
- **Streamlit UI**: http://localhost:8501
- **Neo4j Browser**: http://localhost:7474 (login: neo4j/password123)

### 3) Stop all services
```bash
docker-compose down

# To also remove volumes (data):
docker-compose down -v
```

## Manual Setup (Development)

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

### 4) Start Neo4j (required for graph persistence)
```bash
# Using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:5.15.0-community
```

### 5) Configure environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 6) Run the API
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```
Visit http://localhost:8080/docs for interactive API docs.

### 7) Run the Streamlit UI
```bash
streamlit run app/streamlit_app.py
```
The UI will open at http://localhost:8501.

## API Quickstart

- Analyze sample posts
```bash
curl -X POST http://localhost:8080/api/v1/analyze \
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
curl http://localhost:8080/api/v1/graph
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Streamlit  │────▶│   FastAPI   │────▶│    Neo4j    │
│     UI      │     │     API     │     │   (Graph)   │
│   :8501     │     │   :8080     │     │   :7687     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ PostgreSQL  │
                    │  (Future)   │
                    │   :5432     │
                    └─────────────┘
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEO4J_URI` | Neo4j connection URI | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `password123` |
| `NEO4J_DATABASE` | Neo4j database name | `neo4j` |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://postgres:postgres@localhost:5432/osint_db` |
| `ALLOWED_ORIGINS` | CORS allowed origins (JSON array) | `["*"]` |
| `TWITTER_BEARER_TOKEN` | Twitter API bearer token | - |

## Notes
- This project provides ingestion placeholders; follow each platform's ToS and legal constraints. Prefer official APIs.
- The knowledge graph is now **persisted in Neo4j** for production use.
