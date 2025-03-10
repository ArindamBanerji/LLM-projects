# tests/test_dashboard_controller.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi import Request
from fastapi.responses import RedirectResponse
from controllers.dashboard_controller import show_dashboard, redirect_to_dashboard

class TestDashboardController:
    def setup_method(self):
        # Create a mock request
        self.mock_request = MagicMock(spec=Request)
    
    @pytest.mark.asyncio  # Add this decorator
    async def test_show_dashboard(self):
        """Test that show_dashboard returns the expected context"""
        # Call the controller method
        result = await show_dashboard(self.mock_request)
        
        # Check the result
        assert isinstance(result, dict)
        assert "welcome_message" in result
        assert result["welcome_message"] == "Welcome to the mini-meta harness!"
    
    @pytest.mark.asyncio  # Add this decorator
    async def test_redirect_to_dashboard(self):
        """Test that redirect_to_dashboard returns a RedirectResponse to the dashboard URL"""
        # Mock the URL service to return a predetermined dashboard URL
        with patch('controllers.dashboard_controller.url_service.get_url_for_route') as mock_get_url:
            mock_get_url.return_value = "/dashboard"
            
            # Call the controller method
            result = await redirect_to_dashboard(self.mock_request)
            
            # Verify the URL service was called correctly
            mock_get_url.assert_called_once_with("dashboard")
            
            # Check the result
            assert isinstance(result, RedirectResponse)
            assert result.status_code == 307  # Temporary redirect status code
            assert result.headers["location"] == "/dashboard"