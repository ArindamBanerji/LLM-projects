# tests/test_base_controller.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from controllers import BaseController
from utils.error_utils import ValidationError, BadRequestError

# Test models - renamed to avoid pytest collection warnings
class RequestTestModel(BaseModel):
    name: str
    age: int = Field(gt=0)

class QueryTestModel(BaseModel):
    search: str
    limit: int = 10
    offset: int = 0

class TestBaseController:
    def setup_method(self):
        """Setup for each test"""
        self.controller = BaseController()
    
    @pytest.mark.asyncio
    async def test_parse_json_body_valid(self):
        """Test parsing valid JSON body"""
        # Create a mock request with valid JSON
        mock_request = MagicMock(spec=Request)
        mock_request.json.return_value = {"name": "Test User", "age": 30}
        
        # Parse the body
        result = await BaseController.parse_json_body(mock_request, RequestTestModel)
        
        # Check the result
        assert isinstance(result, RequestTestModel)
        assert result.name == "Test User"
        assert result.age == 30
    
    @pytest.mark.asyncio
    async def test_parse_json_body_invalid(self):
        """Test parsing invalid JSON body"""
        # Create a mock request with invalid JSON (negative age)
        mock_request = MagicMock(spec=Request)
        mock_request.json.return_value = {"name": "Test User", "age": -5}
        
        # Parsing should raise ValidationError
        with pytest.raises(ValidationError) as excinfo:
            await BaseController.parse_json_body(mock_request, RequestTestModel)
        
        # Check the error details
        assert "Invalid request data" in str(excinfo.value)
        assert "validation_errors" in excinfo.value.details
    
    @pytest.mark.asyncio
    async def test_parse_json_body_missing_field(self):
        """Test parsing JSON with missing required field"""
        # Create a mock request with missing required field (name)
        mock_request = MagicMock(spec=Request)
        mock_request.json.return_value = {"age": 30}
        
        # Parsing should raise ValidationError
        with pytest.raises(ValidationError) as excinfo:
            await BaseController.parse_json_body(mock_request, RequestTestModel)
        
        # Check the error details
        assert "Invalid request data" in str(excinfo.value)
        assert "validation_errors" in excinfo.value.details
    
    @pytest.mark.asyncio
    async def test_parse_json_body_invalid_json(self):
        """Test parsing invalid JSON format"""
        # Create a mock request that raises an exception when json() is called
        mock_request = MagicMock(spec=Request)
        mock_request.json.side_effect = Exception("Invalid JSON")
        
        # Parsing should raise BadRequestError
        with pytest.raises(BadRequestError) as excinfo:
            await BaseController.parse_json_body(mock_request, RequestTestModel)
        
        # Check the error message
        assert "Error parsing request body" in str(excinfo.value)
        assert "Invalid JSON" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_parse_query_params_valid(self):
        """Test parsing valid query parameters"""
        # Create a mock request with valid query parameters
        mock_request = MagicMock(spec=Request)
        mock_request.query_params = {"search": "test", "limit": "20", "offset": "5"}
        
        # Parse the query params
        result = await BaseController.parse_query_params(mock_request, QueryTestModel)
        
        # Check the result
        assert isinstance(result, QueryTestModel)
        assert result.search == "test"
        assert result.limit == 20
        assert result.offset == 5
    
    @pytest.mark.asyncio
    async def test_parse_query_params_invalid(self):
        """Test parsing invalid query parameters"""
        # Create a mock request with invalid query parameters (negative limit)
        mock_request = MagicMock(spec=Request)
        mock_request.query_params = {"search": "test", "limit": "-20"}
        
        # Parsing should not raise an error (Pydantic will use the default value for limit)
        result = await BaseController.parse_query_params(mock_request, QueryTestModel)
        assert result.limit == -20  # Pydantic model doesn't validate limit
    
    @pytest.mark.asyncio
    async def test_parse_query_params_missing_required(self):
        """Test parsing query parameters with missing required field"""
        # Create a mock request with missing required field (search)
        mock_request = MagicMock(spec=Request)
        mock_request.query_params = {"limit": "20", "offset": "5"}
        
        # Parsing should raise ValidationError
        with pytest.raises(ValidationError) as excinfo:
            await BaseController.parse_query_params(mock_request, QueryTestModel)
        
        # Check the error details
        assert "Invalid query parameters" in str(excinfo.value)
        assert "validation_errors" in excinfo.value.details
    
    def test_create_success_response(self):
        """Test creating a success response"""
        # Create a success response
        response = BaseController.create_success_response(
            data={"id": 1, "name": "Test"},
            message="Operation successful",
            status_code=201
        )
        
        # Check the response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 201
        
        # Check the response content
        content = response.body.decode()
        assert "success" in content
        assert "Operation successful" in content
        assert "Test" in content
    
    def test_create_success_response_defaults(self):
        """Test creating a success response with default values"""
        # Create a success response with defaults
        response = BaseController.create_success_response()
        
        # Check the response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        
        # Check the response content
        content = response.body.decode()
        assert "success" in content
        assert "Success" in content
    
    def test_redirect_to_route(self):
        """Test redirecting to a route"""
        # Mock the URL service
        with patch('controllers.url_service.get_url_for_route') as mock_get_url:
            mock_get_url.return_value = "/dashboard"
            
            # Create a redirect response
            response = BaseController.redirect_to_route("dashboard")
            
            # Check the response
            assert isinstance(response, RedirectResponse)
            assert response.status_code == 307  # Now using 307 Temporary Redirect
            assert response.headers["location"] == "/dashboard"
            
            # Verify URL service was called with correct parameters
            mock_get_url.assert_called_once_with("dashboard", None)
    
    def test_redirect_to_route_with_params(self):
        """Test redirecting to a route with parameters"""
        # Mock the URL service
        with patch('controllers.url_service.get_url_for_route') as mock_get_url:
            mock_get_url.return_value = "/item/123"
            
            # Create a redirect response with parameters
            response = BaseController.redirect_to_route(
                "item_detail", 
                params={"id": 123}
            )
            
            # Check the response
            assert isinstance(response, RedirectResponse)
            assert response.status_code == 307  # Updated to 307
            assert response.headers["location"] == "/item/123"
            
            # Verify URL service was called with correct parameters
            mock_get_url.assert_called_once_with("item_detail", {"id": 123})
    
    def test_redirect_to_route_custom_status_code(self):
        """Test redirecting to a route with a custom status code"""
        # Mock the URL service
        with patch('controllers.url_service.get_url_for_route') as mock_get_url:
            mock_get_url.return_value = "/dashboard"
            
            # Create a redirect response with a custom status code
            response = BaseController.redirect_to_route(
                "dashboard", 
                status_code=status.HTTP_302_FOUND
            )
            
            # Check the response
            assert isinstance(response, RedirectResponse)
            assert response.status_code == status.HTTP_302_FOUND
            assert response.headers["location"] == "/dashboard"
