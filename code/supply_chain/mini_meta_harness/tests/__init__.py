# tests/__init__.py
# This file ensures the tests directory is recognized as a Python package
# and provides shared test utilities and fixtures

import pytest
from fastapi.testclient import TestClient
from main import app
from services.state_manager import state_manager

# Create a test client that can be imported by test modules
test_client = TestClient(app)

# Reset function to clean up state between tests
def reset_test_state():
    """Reset the state manager for tests"""
    state_manager.clear()
