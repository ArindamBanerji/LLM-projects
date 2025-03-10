# utils/error_utils.py
from typing import Dict, Any, Optional, List, Type
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.requests import Request

class AppError(Exception):
    """
    Base exception class for application errors.
    All custom exceptions should inherit from this.
    """
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    
    def __init__(
        self, 
        message: str = "An unexpected error occurred", 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary representation.
        Useful for serialization and testing.
        """
        return {
            "status_code": self.status_code,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }

class ValidationError(AppError):
    """Exception for data validation errors"""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "validation_error"

class NotFoundError(AppError):
    """Exception for resource not found errors"""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"

class AuthenticationError(AppError):
    """Exception for authentication errors"""
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"

class AuthorizationError(AppError):
    """Exception for authorization errors"""
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "authorization_error"

class BadRequestError(AppError):
    """Exception for general bad request errors"""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"

class ConflictError(AppError):
    """Exception for data conflict errors"""
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"

def create_error_response(error: AppError) -> JSONResponse:
    """
    Create a standardized JSON error response.
    
    Args:
        error: The AppError instance
        
    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": error.error_code,
            "message": error.message,
            "details": error.details
        }
    )

# Global exception handler function to be registered in main.py
async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Global exception handler for AppError exceptions.
    
    Args:
        request: FastAPI request
        exc: The AppError instance
        
    Returns:
        Standardized error response
    """
    # Optionally log the error here
    print(f"Error: {exc.error_code} - {exc.message}")
    
    # Determine if we should redirect or return JSON based on Accept header
    accept = request.headers.get("accept", "")
    
    if "text/html" in accept:
        # For web UI requests, we could redirect to an error page
        # For this minimal implementation, we'll still return JSON
        return create_error_response(exc)
    else:
        # For API requests, return JSON response
        return create_error_response(exc)

# Register all exception handlers
def setup_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Register handler for our base AppError class (catches all subclasses too)
    app.add_exception_handler(AppError, app_exception_handler)
    
    # Handle FastAPI's HTTPException
    app.add_exception_handler(
        HTTPException,
        lambda request, exc: JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "details": {}
            }
        )
    )
    
    # Register a catch-all handler for unexpected exceptions
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        print(f"Unhandled exception: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "details": {"type": str(type(exc).__name__)}
            }
        )
