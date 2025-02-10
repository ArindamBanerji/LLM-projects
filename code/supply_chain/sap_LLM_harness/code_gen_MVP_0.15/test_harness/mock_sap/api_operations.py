"""
SAP Mock API Operations for Material Management

This module provides mock implementations of key SAP material management 
operations for the test harness MVP 0.1.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from test_harness.mock_sap.sap_types import SAPResponse, SAPError

class MockMaterialManagement:
    """
    Mock implementation of SAP material management operations.
    Simulates key material-related API calls.
    """
    
    def __init__(self, seed_data: Optional[Dict[str, Any]] = None):
        """
        Initialize mock material management with optional seed data.
        
        Args:
            seed_data (Optional[Dict[str, Any]]): Initial material data
        """
        # Configure logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize material master data
        self._material_master = seed_data or self._generate_default_material_master()

        # Valid plants for MVP 0.1
        self._valid_plants = {'PLANT_1'}
    
    def _generate_default_material_master(self) -> Dict[str, Any]:
        """
        Generate a default set of material master data.
        
        Returns:
            Dict[str, Any]: Default material master data
        """
        return {
            'MAT001': {
                'material_id': 'MAT001',
                'description': 'Raw Material A',
                'type': 'RAW',
                'base_unit': 'KG',
                'plant_data': {
                    'PLANT_1': {
                        'storage_location': 'A01',
                        'unrestricted_stock': 1000.0,
                    }
                },
                'valuation_data': {
                    'standard_price': 10.00,
                    'price_unit': 1,
                    'currency': 'USD'
                }
            },
            'MAT002': {
                'material_id': 'MAT002',
                'description': 'Finished Product B',
                'type': 'FINISHED',
                'base_unit': 'EA',
                'plant_data': {
                    'PLANT_1': {
                        'storage_location': 'A02',
                        'unrestricted_stock': 500.0,
                    }
                },
                'valuation_data': {
                    'standard_price': 25.00,
                    'price_unit': 1,
                    'currency': 'USD'
                }
            }
        }
    
    async def check_material_availability(
        self, 
        material_id: str, 
        plant: str
    ) -> SAPResponse:
        """
        Check material availability for a specific material and plant.
        
        Args:
            material_id (str): Material identifier
            plant (str): Plant code
        
        Returns:
            SAPResponse: Material availability details
        """
        try:
            # Input validation
            if not material_id or not plant:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='MAT_AVAIL_001',
                        message='Invalid material ID or plant code'
                    )
                )
            
            # Check material existence first
            if material_id not in self._material_master:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='MAT_AVAIL_002',
                        message=f'Material {material_id} not found'
                    )
                )
            
            material = self._material_master[material_id]
            
            # Check plant existence
            if plant not in material.get('plant_data', {}):
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='MAT_AVAIL_003',
                        message=f'Material {material_id} not configured for plant {plant}'
                    )
                )
            
            # Retrieve stock information
            plant_data = material['plant_data'][plant]
            availability_data = {
                'material_id': material_id,
                'plant': plant,
                'description': material['description'],
                'base_unit': material['base_unit'],
                'unrestricted_stock': plant_data['unrestricted_stock'],
                'storage_location': plant_data['storage_location'],
                'valuation': material.get('valuation_data', {})
            }
            
            self.logger.info(f"Material availability checked: {material_id} at {plant}")
            
            return SAPResponse(
                success=True,
                data=availability_data
            )
        
        except Exception as e:
            error_msg = f"Material availability check failed: {str(e)}"
            self.logger.error(error_msg)
            return SAPResponse(
                success=False,
                error=SAPError(
                    code='MAT_AVAIL_999',
                    message=error_msg
                )
            )
    
    async def create_material_master(
        self, 
        material_data: Dict[str, Any]
    ) -> SAPResponse:
        """
        Create a new material master record.
        
        Args:
            material_data (Dict[str, Any]): Material master data
        
        Returns:
            SAPResponse: Material creation result
        """
        try:
            # Validate if material_id exists
            if not material_data.get('material_id'):
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='MAT_CREATE_001',
                        message='Missing material ID'
                    )
                )
            
            material_id = material_data['material_id']
            
            # Check if material already exists
            if material_id in self._material_master:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='MAT_CREATE_002',
                        message=f'Material {material_id} already exists'
                    )
                )
            
            # Validate required fields
            required_fields = ['description', 'type', 'base_unit']
            missing_fields = [field for field in required_fields if field not in material_data]
            
            if missing_fields:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='MAT_CREATE_003',
                        message=f'Missing required fields: {", ".join(missing_fields)}'
                    )
                )
            
            # Validate plant data if provided
            if 'plant_data' in material_data:
                for plant in material_data['plant_data'].keys():
                    if plant not in self._valid_plants:
                        return SAPResponse(
                            success=False,
                            error=SAPError(
                                code='MAT_CREATE_004',
                                message=f'Invalid plant {plant} in plant_data'
                            )
                        )

            # Add default plant data if not provided
            if 'plant_data' not in material_data:
                material_data['plant_data'] = {
                    'PLANT_1': {
                        'storage_location': 'A01',
                        'unrestricted_stock': 0.0,
                    }
                }
            
            # Add default valuation data if not provided
            if 'valuation_data' not in material_data:
                material_data['valuation_data'] = {
                    'standard_price': 0.0,
                    'price_unit': 1,
                    'currency': 'USD'
                }
            
            # Store material master data
            self._material_master[material_id] = material_data
            
            self.logger.info(f"Material master created: {material_id}")
            
            return SAPResponse(
                success=True,
                data={
                    'material_id': material_id,
                    'message': 'Material master created successfully'
                }
            )
        
        except Exception as e:
            error_msg = f"Material master creation failed: {str(e)}"
            self.logger.error(error_msg)
            return SAPResponse(
                success=False,
                error=SAPError(
                    code='MAT_CREATE_999',
                    message=error_msg
                )
            )
    
    def get_material_master_data(
        self, 
        material_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get material master data for a specific material.
        Helper method for other components to access material data.
        
        Args:
            material_id (str): Material identifier
        
        Returns:
            Optional[Dict[str, Any]]: Material master data if found
        """
        return self._material_master.get(material_id)

    def is_valid_plant(self, plant: str) -> bool:
        """
        Check if a plant code is valid.
        Helper method for other components.
        
        Args:
            plant (str): Plant code to validate
        
        Returns:
            bool: True if plant is valid
        """
        return plant in self._valid_plants