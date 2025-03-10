# tests/test_url_service.py
import pytest
from meta_routes import RouteDefinition, HttpMethod, ALL_ROUTES
from services.url_service import URLService

# Create test routes for isolated testing
TEST_ROUTES = [
    RouteDefinition(
        name="test_simple",
        path="/test",
        methods=[HttpMethod.GET],
        controller="controllers.test_controller.test_action",
        template=None
    ),
    RouteDefinition(
        name="test_with_param",
        path="/test/{id}",
        methods=[HttpMethod.GET],
        controller="controllers.test_controller.test_with_param",
        template=None
    ),
    RouteDefinition(
        name="test_with_multiple_params",
        path="/test/{category}/{id}",
        methods=[HttpMethod.GET],
        controller="controllers.test_controller.test_with_multiple_params",
        template=None
    )
]

class TestURLService:
    def setup_method(self):
        # Create a URLService with our test routes
        self.url_service = URLService()
        # Override the route_map with our test routes
        self.url_service.route_map = {route.name: route for route in TEST_ROUTES}
    
    def test_get_url_for_simple_route(self):
        """Test generating a URL for a simple route with no parameters"""
        url = self.url_service.get_url_for_route("test_simple")
        assert url == "/test"
    
    def test_get_url_with_param(self):
        """Test generating a URL with a parameter"""
        url = self.url_service.get_url_for_route("test_with_param", {"id": 123})
        assert url == "/test/123"
    
    def test_get_url_with_multiple_params(self):
        """Test generating a URL with multiple parameters"""
        url = self.url_service.get_url_for_route("test_with_multiple_params", {
            "category": "books",
            "id": 456
        })
        assert url == "/test/books/456"
    
    def test_nonexistent_route(self):
        """Test that a ValueError is raised for a non-existent route"""
        with pytest.raises(ValueError) as excinfo:
            self.url_service.get_url_for_route("nonexistent_route")
        assert "not found in route registry" in str(excinfo.value)
    
    def test_param_substitution_type_handling(self):
        """Test parameter values of different types"""
        # Test with integer
        url = self.url_service.get_url_for_route("test_with_param", {"id": 123})
        assert url == "/test/123"
        
        # Test with string
        url = self.url_service.get_url_for_route("test_with_param", {"id": "abc"})
        assert url == "/test/abc"
        
        # Test with boolean
        url = self.url_service.get_url_for_route("test_with_param", {"id": True})
        assert url == "/test/True"

    def test_real_route_compatibility(self):
        """Test that our service works with the actual routes in ALL_ROUTES"""
        # Create a new service with the actual routes
        real_service = URLService()
        
        # Test that we can generate a URL for the dashboard route
        url = real_service.get_url_for_route("dashboard")
        assert url == "/dashboard"
        
        # Test that we can generate a URL for the root route
        url = real_service.get_url_for_route("root")
        assert url == "/"
