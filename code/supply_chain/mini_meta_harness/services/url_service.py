# services/url_service.py
from typing import Dict, Any, Optional, List
import re
from meta_routes import ALL_ROUTES

class URLService:
    """
    Service for generating URLs based on route names
    """
    def __init__(self):
        self.route_map = {route.name: route for route in ALL_ROUTES}
        
    def get_url_for_route(self, route_name: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a URL for a named route, with optional path parameters
        
        Args:
            route_name: Name of the route (defined in meta_routes.py)
            params: Dictionary of path parameters (if any)
            
        Returns:
            Formatted URL string
        
        Raises:
            ValueError: If route name doesn't exist or required params are missing
        """
        if route_name not in self.route_map:
            raise ValueError(f"Route '{route_name}' not found in route registry")
            
        route = self.route_map[route_name]
        path = route.path
        
        # Find all required parameters in the path
        required_params = re.findall(r'{([^}]+)}', path)
        
        # Check if all required parameters are provided
        if required_params:
            if not params:
                raise ValueError(f"Route '{route_name}' requires parameters: {', '.join(required_params)}")
            
            missing_params = [param for param in required_params if param not in params]
            if missing_params:
                raise ValueError(f"Missing required parameters for route '{route_name}': {', '.join(missing_params)}")
        
        # If there are parameters, substitute them in the path
        if params:
            for key, value in params.items():
                # Look for path parameters like {param_name}
                placeholder = f"{{{key}}}"
                if placeholder in path:
                    path = path.replace(placeholder, str(value))
        
        return path

# Create a singleton instance
url_service = URLService()