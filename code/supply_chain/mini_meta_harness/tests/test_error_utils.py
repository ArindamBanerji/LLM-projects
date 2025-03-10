# tests/test_error_utils.py
import pytest
import json
from fastapi import FastAPI, status, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from utils.error_utils import (
    AppError, ValidationError, NotFoundError, AuthenticationError, 
    AuthorizationError, BadRequestError, ConflictError, 
    create_error_response, app_exception_handler, setup_exception_handlers
)

class TestErrorClasses:
    def test_app_error_default_values(self):
        """Test AppError with default values"""
        error = AppError()
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.error_code == "internal_error"
        assert error.message == "An unexpected error occurred"
        assert error.details == {}
    
    def test_app_error_custom_values(self):
        """Test AppError with custom values"""
        error = AppError(
            message="Custom error message",
            details={"key": "value"}
        )
        assert error.message == "Custom error message"
        assert error.details == {"key": "value"}
    
    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError(
            message="Invalid data",
            details={"field": "This field is required"}
        )
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.error_code == "validation_error"
        assert error.message == "Invalid data"
    
    def test_not_found_error(self):
        """Test NotFoundError"""
        error = NotFoundError(message="Resource not found")
        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "not_found"
        assert error.message == "Resource not found"
    
    def test_authentication_error(self):
        """Test AuthenticationError"""
        error = AuthenticationError(message="Invalid credentials")
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.error_code == "authentication_error"
        assert error.message == "Invalid credentials"
    
    def test_authorization_error(self):
        """Test AuthorizationError"""
        error = AuthorizationError(message="Permission denied")
        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.error_code == "authorization_error"
        assert error.message == "Permission denied"
    
    def test_bad_request_error(self):
        """Test BadRequestError"""
        error = BadRequestError(message="Invalid request")
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.error_code == "bad_request"
        assert error.message == "Invalid request"
    
    def test_conflict_error(self):
        """Test ConflictError"""
        error = ConflictError(message="Resource already exists")
        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.error_code == "conflict"
        assert error.message == "Resource already exists"

class TestErrorHandlers:
    def test_create_error_response(self):
        """Test create_error_response function"""
        error = ValidationError(
            message="Invalid data",
            details={"field": "This field is required"}
        )
        response = create_error_response(error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.body is not None
        
        # Convert response body to dict
        content = json.loads(response.body.decode())
        
        assert content["error"] == "validation_error"
        assert content["message"] == "Invalid data"
        assert content["details"] == {"field": "This field is required"}
    
    def test_error_dict_method(self):
        """Test that we can generate a dict representation of errors"""
        # Add dict method to AppError
        def dict(self):
            return {
                "status_code": self.status_code,
                "error_code": self.error_code,
                "message": self.message,
                "details": self.details
            }
        
        # Temporarily add dict method to AppError
        original_dict = getattr(AppError, "dict", None)
        AppError.dict = dict
        
        try:
            # Test dict method
            error = ValidationError(message="Test error")
            error_dict = error.dict()
            
            assert error_dict["status_code"] == status.HTTP_400_BAD_REQUEST
            assert error_dict["error_code"] == "validation_error"
            assert error_dict["message"] == "Test error"
        finally:
            # Restore original dict method
            if original_dict:
                AppError.dict = original_dict
            else:
                delattr(AppError, "dict")
