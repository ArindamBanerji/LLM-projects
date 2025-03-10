# controllers/error_test_controller.py
from fastapi import Request
from utils.error_utils import NotFoundError, ValidationError, BadRequestError
from controllers import BaseController
from typing import Dict, Any

async def test_not_found(request: Request) -> Dict[str, Any]:
    """
    Test route that raises a NotFoundError.
    This is for manual testing of error handling.
    """
    raise NotFoundError(message="This is a test NotFoundError")

async def test_validation_error(request: Request) -> Dict[str, Any]:
    """
    Test route that raises a ValidationError.
    This is for manual testing of error handling.
    """
    raise ValidationError(
        message="This is a test ValidationError",
        details={"field1": "Invalid value", "field2": "Required field"}
    )

async def test_bad_request(request: Request) -> Dict[str, Any]:
    """
    Test route that raises a BadRequestError.
    This is for manual testing of error handling.
    """
    raise BadRequestError(message="This is a test BadRequestError")

async def test_success_response(request: Request) -> Dict[str, Any]:
    """
    Test route that returns a success response using BaseController.
    This is for manual testing of the success response format.
    """
    return BaseController.create_success_response(
        data={"test": "value", "items": [1, 2, 3]},
        message="This is a test success response"
    )
