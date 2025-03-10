# tests/test_integration.py
from fastapi.testclient import TestClient
import pytest
from main import app

client = TestClient(app)

class TestIntegration:
    def test_root_redirects_to_dashboard(self):
        """Test that the root path redirects to /dashboard"""
        response = client.get("/", allow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/dashboard"
    
    def test_dashboard_accessible(self):
        """Test that the dashboard is accessible and contains expected content"""
        response = client.get("/dashboard")
        assert response.status_code == 200
        
        # Check if the content contains our welcome message
        content = response.text
        assert "Welcome to the mini-meta harness!" in content
        
        # Check if the URL is displayed correctly
        assert "Current page URL: /dashboard" in content
