"""
Enhanced SAP API Simulator

Provides a simplified mock SAP API simulation framework with 
integrated material management capabilities for test harness MVP 0.1.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

# Import common types and operations
from sap_types import SAPResponse, SAPError
from api_operations import MockMaterialManagement

class SAPSimulator:
    """
    SAP API simulator with core simulation functionality for MVP 0.1.
    
    Key features:
    - Basic authentication
    - Operation routing
    - State management
    - Material operations
    """
    
    def __init__(
        self, 
        config: Optional[Dict[str, Any]] = None,
        material_management: Optional[MockMaterialManagement] = None
    ):
        """
        Initialize the SAP simulator
        
        Args:
            config: Configuration dictionary for simulator behavior
            material_management: Optional custom material management mock
        """
        # Configure logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize configuration with defaults
        self.config = config or {
            'token_expiry_minutes': 60,
            'require_authentication': True
        }
        
        # Initialize state
        self._state = {
            'authentication': {},
            'operations': {}
        }
        
        # Initialize material management
        self.material_management = material_management or MockMaterialManagement()
        
        # Authentication token storage
        self._auth_tokens: Dict[str, Dict[str, Any]] = {}
    
    async def authenticate(
        self, 
        credentials: Dict[str, str]
    ) -> SAPResponse:
        """
        Authenticate user and generate session token
        
        Args:
            credentials: Dictionary containing username and password
        
        Returns:
            SAPResponse with authentication result
        """
        try:
            # Basic authentication validation
            if not credentials.get('username') or not credentials.get('password'):
                return SAPResponse.error_response(
                    code='AUTH001',
                    message='Invalid credentials'
                )
            
            # Generate authentication token
            token = str(uuid.uuid4())
            expiration = datetime.utcnow() + timedelta(
                minutes=self.config['token_expiry_minutes']
            )
            
            # Store token information
            self._auth_tokens[token] = {
                'username': credentials['username'],
                'created_at': datetime.utcnow(),
                'expires_at': expiration
            }
            
            # Log successful authentication
            self.logger.info(
                f"Authentication successful for user: {credentials['username']}"
            )
            
            return SAPResponse.success_response({
                'token': token,
                'expires_at': expiration.isoformat()
            })
        
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return SAPResponse.error_response(
                code='AUTH999',
                message=f'Authentication system error: {str(e)}'
            )
    
    def validate_token(self, token: str) -> bool:
        """
        Validate an authentication token
        
        Args:
            token: Authentication token to validate
        
        Returns:
            Boolean indicating token validity
        """
        # Skip validation if authentication is disabled
        if not self.config['require_authentication']:
            return True
        
        # Check if token exists
        if token not in self._auth_tokens:
            return False
        
        # Check token expiration
        token_info = self._auth_tokens[token]
        if datetime.utcnow() > token_info['expires_at']:
            # Remove expired token
            del self._auth_tokens[token]
            return False
        
        return True
    
    async def execute_request(
        self, 
        operation: str, 
        parameters: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> SAPResponse:
        """
        Execute a simulated SAP API request
        
        Args:
            operation: The specific operation to execute
            parameters: Operation-specific parameters
            auth_token: Optional authentication token
        
        Returns:
            SAPResponse with operation result
        """
        try:
            # Validate authentication token if required
            if self.config['require_authentication']:
                if not auth_token or not self.validate_token(auth_token):
                    return SAPResponse.error_response(
                        code='AUTH002',
                        message='Invalid or expired token'
                    )
            
            # Route operations to appropriate handlers
            operation_routes = {
                # Material Management Operations
                'check_material_availability': 
                    self.material_management.check_material_availability,
                'create_material_master': 
                    self.material_management.create_material_master
            }
            
            # Find and execute the appropriate operation
            if operation not in operation_routes:
                return SAPResponse.error_response(
                    code='OPERATION_001',
                    message=f'Unsupported operation: {operation}'
                )
            
            # Execute the operation
            operation_handler = operation_routes[operation]
            response = await operation_handler(**parameters)
            
            # Log successful operation
            self.logger.info(f"Operation executed successfully: {operation}")
            
            return response
        
        except Exception as e:
            self.logger.error(f"Request execution error for {operation}: {str(e)}")
            return SAPResponse.error_response(
                code='REQUEST_999',
                message=f'Request execution failed: {str(e)}'
            )
    
    def get_state(self) -> Dict[str, Any]:
        """
        Retrieve current simulator state
        
        Returns:
            Dictionary representing the current state
        """
        return self._state.copy()
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Set simulator state
        
        Args:
            state: State dictionary to set
        """
        self._state = state.copy()
    
    def reset_state(self) -> None:
        """
        Reset simulator state to initial configuration
        """
        self._state = {
            'authentication': {},
            'operations': {}
        }
        self._auth_tokens.clear()
        self.logger.info("Simulator state reset")

# Demonstration code
async def main():
    """
    Demonstration of simulator functionality
    """
    # Initialize simulator
    simulator = SAPSimulator()
    
    try:
        # Authenticate
        auth_response = await simulator.authenticate({
            'username': 'test_user',
            'password': 'test_password'
        })
        print("Authentication Response:", auth_response)
        
        # Check material availability if authentication successful
        if auth_response.success:
            token = auth_response.data['token']
            material_check = await simulator.execute_request(
                'check_material_availability', 
                {
                    'material_id': 'MAT001', 
                    'plant': 'PLANT_1'
                },
                auth_token=token
            )
            print("Material Availability:", material_check)
    
    except Exception as e:
        print(f"Error in simulator demonstration: {e}")

# Allow direct script execution for testing
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())