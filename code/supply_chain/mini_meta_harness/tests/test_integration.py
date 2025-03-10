# tests/test_integration.py
from fastapi.testclient import TestClient
import pytest
from main import app
from services.state_manager import state_manager

# Create a test client
client = TestClient(app)

class TestIntegration:
    def setup_method(self):
        """Reset state before each test"""
        state_manager.clear()
    
    def test_root_redirects_to_dashboard(self):
        """Test that the root path redirects to /dashboard"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/dashboard"
    
    def test_dashboard_accessible(self):
        """Test that the dashboard is accessible and contains expected content"""
        response = client.get("/dashboard")
        assert response.status_code == 200
        
        # Check basic content
        content = response.text
        assert "Welcome to the mini-meta harness!" in content
        assert "Current page URL: /dashboard" in content
        
        # Check state-based content - using more robust checks
        assert "Visit count" in content  # Just check for the label
        assert "First visit" in content  # Check for the initial visit text
        assert "Current time" in content
    
    def test_dashboard_visit_counter(self):
        """Test that the dashboard visit counter increments"""
        # Make sure we start from a clean state
        state_manager.clear()
        state_manager.set("dashboard_visits", 0)
        
        # First visit
        client.get("/dashboard")
        
        # Second visit
        response2 = client.get("/dashboard")
        
        # Check that the visit count increased
        assert state_manager.get("dashboard_visits") == 2
        
        # The second visit should not show "First visit"
        assert "First visit" not in response2.text
