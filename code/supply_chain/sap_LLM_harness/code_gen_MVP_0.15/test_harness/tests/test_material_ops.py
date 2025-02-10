"""
Unit tests for SAP mock material management operations.
Tests core material functionality for test harness MVP 0.1.

This module provides comprehensive testing for:
- Material availability checking
- Material master creation
- Error handling
- Data validation
"""

import unittest
import asyncio
from typing import Dict, Any

from test_harness.mock_sap.api_operations import MockMaterialManagement
from test_harness.mock_sap.sap_types import SAPResponse, SAPError

class TestMaterialOperations(unittest.TestCase):
    """Test material management operations"""
    
    def setUp(self):
        """Initialize test environment before each test"""
        self.material_mgmt = MockMaterialManagement()
        
        # Test data
        self.test_material = {
            'material_id': 'TEST001',
            'description': 'Test Material',
            'type': 'RAW',
            'base_unit': 'KG',
            'plant_data': {
                'PLANT_1': {
                    'storage_location': 'A01',
                    'unrestricted_stock': 500.0
                }
            }
        }
    
    async def test_initial_material_check(self):
        """Test default material availability from seed data"""
        response = await self.material_mgmt.check_material_availability(
            material_id='MAT001',
            plant='PLANT_1'
        )
        # Verify successful response
        self.assertTrue(response.success)
        self.assertIsNotNone(response.data)
        
        # Verify material data
        self.assertEqual(response.data['material_id'], 'MAT001')
        self.assertEqual(response.data['description'], 'Raw Material A')
        self.assertEqual(response.data['base_unit'], 'KG')
        self.assertEqual(response.data['unrestricted_stock'], 1000.0)
        self.assertEqual(response.data['storage_location'], 'A01')
        
        # Verify valuation data
        self.assertIn('valuation', response.data)
        valuation = response.data['valuation']
        self.assertEqual(valuation['standard_price'], 10.00)
        self.assertEqual(valuation['price_unit'], 1)
        self.assertEqual(valuation['currency'], 'USD')
    
    async def test_create_and_verify_material(self):
        """Test material creation and subsequent verification"""
        # Create material
        create_response = await self.material_mgmt.create_material_master(
            self.test_material
        )
        self.assertTrue(create_response.success)
        self.assertEqual(create_response.data['material_id'], 'TEST001')
        self.assertEqual(
            create_response.data['message'],
            'Material master created successfully'
        )
        
        # Verify created material
        verify_response = await self.material_mgmt.check_material_availability(
            material_id='TEST001',
            plant='PLANT_1'
        )
        self.assertTrue(verify_response.success)
        self.assertEqual(verify_response.data['material_id'], 'TEST001')
        self.assertEqual(verify_response.data['description'], 'Test Material')
        self.assertEqual(verify_response.data['unrestricted_stock'], 500.0)
    
    async def test_material_creation_without_id(self):
        """Test material creation without material ID"""
        invalid_material = {
            'description': 'Invalid Material',
            'type': 'RAW',
            'base_unit': 'KG'
        }
        
        response = await self.material_mgmt.create_material_master(invalid_material)
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'MAT_CREATE_001')
        self.assertIn('Missing material ID', response.error.message)
    
    async def test_duplicate_material_creation(self):
        """Test duplicate material creation handling"""
        # Create initial material
        await self.material_mgmt.create_material_master(self.test_material)
        
        # Attempt duplicate creation
        duplicate_response = await self.material_mgmt.create_material_master(
            self.test_material
        )
        self.assertFalse(duplicate_response.success)
        self.assertEqual(duplicate_response.error.code, 'MAT_CREATE_002')
        self.assertIn('already exists', duplicate_response.error.message)
    
    async def test_missing_required_fields(self):
        """Test material creation with missing required fields"""
        invalid_material = {
            'material_id': 'TEST002'
            # Missing description, type, and base_unit
        }
        
        response = await self.material_mgmt.create_material_master(invalid_material)
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'MAT_CREATE_003')
        self.assertIn('Missing required fields', response.error.message)
    
    async def test_invalid_material_check(self):
        """Test invalid material handling"""
        response = await self.material_mgmt.check_material_availability(
            material_id='INVALID_MAT',
            plant='PLANT_1'
        )
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'MAT_AVAIL_002')
        self.assertIn('not found', response.error.message)
    
    async def test_invalid_plant_check(self):
        """Test invalid plant handling"""
        response = await self.material_mgmt.check_material_availability(
            material_id='MAT001',
            plant='INVALID_PLANT'
        )
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'MAT_AVAIL_003')
        self.assertIn('not configured', response.error.message)
    
    async def test_empty_input_handling(self):
        """Test handling of empty inputs"""
        # Test empty material_id
        response1 = await self.material_mgmt.check_material_availability(
            material_id='',
            plant='PLANT_1'
        )
        self.assertFalse(response1.success)
        self.assertEqual(response1.error.code, 'MAT_AVAIL_001')
        
        # Test empty plant
        response2 = await self.material_mgmt.check_material_availability(
            material_id='MAT001',
            plant=''
        )
        self.assertFalse(response2.success)
        self.assertEqual(response2.error.code, 'MAT_AVAIL_001')
    
    async def test_default_values(self):
        """Test default value handling in material creation"""
        minimal_material = {
            'material_id': 'TEST003',
            'description': 'Minimal Test Material',
            'type': 'RAW',
            'base_unit': 'EA'
        }
        
        # Create material with minimal data
        create_response = await self.material_mgmt.create_material_master(
            minimal_material
        )
        self.assertTrue(create_response.success)
        
        # Verify defaults were applied
        material_data = self.material_mgmt.get_material_master_data('TEST003')
        self.assertIsNotNone(material_data)
        
        # Verify plant data defaults
        self.assertIn('plant_data', material_data)
        self.assertIn('PLANT_1', material_data['plant_data'])
        plant_data = material_data['plant_data']['PLANT_1']
        self.assertEqual(plant_data['storage_location'], 'A01')
        self.assertEqual(plant_data['unrestricted_stock'], 0.0)
        
        # Verify valuation data defaults
        self.assertIn('valuation_data', material_data)
        valuation_data = material_data['valuation_data']
        self.assertEqual(valuation_data['standard_price'], 0.0)
        self.assertEqual(valuation_data['price_unit'], 1)
        self.assertEqual(valuation_data['currency'], 'USD')
    
    async def test_get_material_master_data(self):
        """Test direct material data access"""
        # First create a material
        await self.material_mgmt.create_material_master(self.test_material)
        
        # Get material data
        material_data = self.material_mgmt.get_material_master_data('TEST001')
        
        # Verify data
        self.assertIsNotNone(material_data)
        self.assertEqual(material_data['material_id'], 'TEST001')
        self.assertEqual(material_data['description'], 'Test Material')
        self.assertEqual(material_data['type'], 'RAW')
        self.assertEqual(material_data['base_unit'], 'KG')
        self.assertEqual(
            material_data['plant_data']['PLANT_1']['unrestricted_stock'],
            500.0
        )

if __name__ == '__main__':
    unittest.main()