# controllers/__init__.py
from typing import Dict, Any, Optional, Type, TypeVar, List, Union
from fastapi import Request, Response, Body, Query, Path, Form, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ValidationError as PydanticValidationError
from services.url_service import url_service
from utils.error_utils import ValidationError, NotFoundError, BadRequestError

T = TypeVar('T', bound=BaseModel)

class BaseController:
    """
    Base controller class with common methods for request handling.
    """
    
    @staticmethod
    async def parse_json_body(request: Request, model_class: Type[T]) -> T:
        """
        Parse and validate request body against a Pydantic model.
        
        Args:
            request: FastAPI request
            model_class: Pydantic model class to validate against
            
        Returns:
            Validated model instance
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            json_body = await request.json()
            return model_class(**json_body)
        except PydanticValidationError as e:
            validation_errors = {}
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                validation_errors[field] = error["msg"]
            
            raise ValidationError(
                message="Invalid request data",
                details={"validation_errors": validation_errors}
            )
        except Exception as e:
            raise BadRequestError(
                message=f"Error parsing request body: {str(e)}"
            )
    
    @staticmethod
    async def parse_query_params(request: Request, model_class: Type[T]) -> T:
        """
        Parse and validate query parameters against a Pydantic model.
        
        Args:
            request: FastAPI request
            model_class: Pydantic model class to validate against
            
        Returns:
            Validated model instance
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            query_params = dict(request.query_params)
            return model_class(**query_params)
        except PydanticValidationError as e:
            validation_errors = {}
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                validation_errors[field] = error["msg"]
            
            raise ValidationError(
                message="Invalid query parameters",
                details={"validation_errors": validation_errors}
            )
    
    @staticmethod
    def create_success_response(
        data: Any = None, 
        message: str = "Success", 
        status_code: int = 200
    ) -> JSONResponse:
        """
        Create a standardized success response.
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            
        Returns:
            Standardized JSON response
        """
        return JSONResponse(
            status_code=status_code,
            content={
                "success": True,
                "message": message,
                "data": data
            }
        )
    
    @staticmethod
    def redirect_to_route(
        route_name: str, 
        params: Optional[Dict[str, Any]] = None,
        status_code: int = 307  # Changed from 303 to 307 (Temporary Redirect)
    ) -> RedirectResponse:
        """
        Create a redirect response to a named route.
        
        Args:
            route_name: Name of the route to redirect to
            params: Optional route parameters
            status_code: HTTP status code for the redirect (default: 307 Temporary Redirect)
            
        Returns:
            RedirectResponse to the generated URL
        """
        url = url_service.get_url_for_route(route_name, params)
        return RedirectResponse(url=url, status_code=status_code)
