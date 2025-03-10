# tests/test_template_service.py
from unittest.mock import patch, MagicMock
import pytest
from fastapi import Request
from services.template_service import TemplateService

class TestTemplateService:
    def setup_method(self):
        # Create a mocked Jinja2Templates instance
        with patch('services.template_service.Jinja2Templates') as mock_jinja:
            # Create a mock for globals that we can inspect later
            self.mock_globals = {}
            
            # Set up the mock environment with the globals
            self.mock_env = MagicMock()
            self.mock_env.globals = self.mock_globals
            
            # Set up the mock templates with the mock environment
            self.mock_templates = MagicMock()
            self.mock_templates.env = self.mock_env
            mock_jinja.return_value = self.mock_templates
            
            # Create the TemplateService
            self.template_service = TemplateService()
            
            # Verify Jinja2Templates was called with the correct directory
            mock_jinja.assert_called_once_with(directory="templates")
    
    def test_url_for_registered_in_globals(self):
        """Test that url_for is registered in the Jinja2 globals"""
        # Check that url_for was added to the environment globals
        assert "url_for" in self.mock_globals
        # Verify it points to our method
        assert self.mock_globals["url_for"] == self.template_service.url_for