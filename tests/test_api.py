from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_analyze_basic():
    payload = {
        "posts": [
            {
                "id": "p1",
                "platform": "twitter",
                "author": "alice",
                "text": "Great product launch in Jakarta! Congrats to the team.",
            },
            {
                "id": "p2",
                "platform": "facebook",
                "author": "bob",
                "text": "This is terrible news.",
            }
        ]
    }
    r = client.post("/api/v1/analyze", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) == 2
    assert "stats" in data
