import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure app is importable regardless of current working directory
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ["GROQ_API_KEY"] = "mock-groq-key-for-tests"

from app.main import app

client = TestClient(app)

def test_health_and_kb():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["kb_entries"] >= 10
    assert "model" in data

    kb_res = client.get("/api/knowledge-base")
    assert kb_res.status_code == 200
    kb_data = kb_res.json()
    assert len(kb_data) >= 10

def test_create_lead_validation():
    payload = {
        "requirement": "too short",
        "company_name": "Test Co",
        "contact_email": "test@example.com"
    }
    response = client.post("/api/leads", json=payload)
    assert response.status_code == 422
