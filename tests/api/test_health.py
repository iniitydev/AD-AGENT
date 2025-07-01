import pytest
from fastapi.testclient import TestClient
# Adjust the import path if src.main directly defines 'app'
# If 'app' is in a submodule, e.g., src.app.main, adjust accordingly.
# Assuming 'app' is directly in src.main for now as per user's snippet for src/main.py
from src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "services" in data
    assert data["version"] == app.version # Check against FastAPI app's version

    services = data["services"]
    assert services["database"] == "available"
    assert services["ml_service"] == "available"
    assert services["storage"] == "available"

def test_system_info():
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "Iniity AI Agent" # Corrected expected value
    assert data["version"] == app.version # Check against FastAPI app's version
    assert data["author"] == "Iniity Inc." # Corrected expected value
    assert data["license"] == "MIT"
    assert "repository" in data # Check key existence
