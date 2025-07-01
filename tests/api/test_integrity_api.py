import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import json
from pathlib import Path

# Assuming your FastAPI app instance is named 'app' in 'src.main'
from src.main import app

client = TestClient(app)

# --- Tests for GET /api/v1/integrity ---

def test_get_integrity_status_success():
    """Test GET /api/v1/integrity when verification is successful."""
    mock_verify_result = {
        "verified": True,
        "signature_verified": True,
        "signature_message": "Signature OK",
        "files_checked": 10,
        "files_ok": 10,
        "failed_files_details": [],
        "error_message": None
    }
    with patch("src.main.verify_integrity_script", return_value=mock_verify_result) as mock_verify:
        response = client.get("/api/v1/integrity")
        assert response.status_code == 200
        assert response.json() == mock_verify_result
        mock_verify.assert_called_once_with(project_root_str=str(Path(".").resolve()))

def test_get_integrity_status_failure_tampered():
    """Test GET /api/v1/integrity when verification fails (tampering)."""
    mock_verify_result = {
        "verified": False,
        "signature_verified": True,
        "signature_message": "Signature OK",
        "files_checked": 10,
        "files_ok": 9,
        "failed_files_details": [{"path": "src/some_file.py", "status": "CHANGED"}],
        "error_message": None
    }
    with patch("src.main.verify_integrity_script", return_value=mock_verify_result) as mock_verify:
        response = client.get("/api/v1/integrity")
        assert response.status_code == 200 # API call is successful, content indicates verification failure
        assert response.json() == mock_verify_result
        mock_verify.assert_called_once()

def test_get_integrity_status_manifest_not_found():
    """Test GET /api/v1/integrity when manifest file is not found by the script."""
    mock_verify_result = {
        "verified": False,
        "error_message": f"Manifest file not found at {Path('.') / 'sovereign_manifest.json'}"
        # Other fields might be absent or default if script exits early
    }
    with patch("src.main.verify_integrity_script", return_value=mock_verify_result) as mock_verify:
        # The API endpoint itself should return 500 if verify_integrity_script returns an error_message like this
        # based on current API logic: if verification_result.get("error_message"): raise HTTPException
        response = client.get("/api/v1/integrity")
        assert response.status_code == 500
        assert response.json()["detail"] == mock_verify_result["error_message"]
        mock_verify.assert_called_once()

def test_get_integrity_status_script_exception():
    """Test GET /api/v1/integrity when the script raises an unexpected exception."""
    with patch("src.main.verify_integrity_script", side_effect=Exception("Unexpected script error")) as mock_verify:
        response = client.get("/api/v1/integrity")
        assert response.status_code == 500
        assert "Internal server error during integrity verification: Unexpected script error" in response.json()["detail"]
        mock_verify.assert_called_once()

# --- Tests for POST /api/v1/integrity/generate ---

def test_generate_integrity_manifest_success():
    """Test POST /api/v1/integrity/generate for successful manifest generation."""
    mock_manifest_content = {
        "manifest_version": "2.5.0",
        "timestamp": "2023-10-01T10:00:00Z",
        "files": {"src/main.py": "sha256:somehash"},
        "git_info": {}
    }
    with patch("src.main.generate_manifest_script", return_value=mock_manifest_content) as mock_generate:
        response = client.post("/api/v1/integrity/generate")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "success"
        assert json_response["message"] == "Manifest generated successfully."
        assert json_response["manifest"] == mock_manifest_content
        mock_generate.assert_called_once_with(project_root_str=str(Path(".").resolve()))

def test_generate_integrity_manifest_script_returns_none():
    """Test POST /api/v1/integrity/generate when script fails to generate (returns None)."""
    with patch("src.main.generate_manifest_script", return_value=None) as mock_generate:
        response = client.post("/api/v1/integrity/generate")
        assert response.status_code == 500
        assert response.json()["detail"] == "Manifest generation failed (script returned None)."
        mock_generate.assert_called_once()

def test_generate_integrity_manifest_script_exception():
    """Test POST /api/v1/integrity/generate when script raises an unexpected exception."""
    with patch("src.main.generate_manifest_script", side_effect=Exception("Unexpected generation error")) as mock_generate:
        response = client.post("/api/v1/integrity/generate")
        assert response.status_code == 500
        assert "Internal server error during manifest generation: Unexpected generation error" in response.json()["detail"]
        mock_generate.assert_called_once()
