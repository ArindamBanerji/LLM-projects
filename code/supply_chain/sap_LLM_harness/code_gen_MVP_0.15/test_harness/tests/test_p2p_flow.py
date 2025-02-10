"""
Unit tests for SAP mock P2P (Procure-to-Pay) operations.
Tests core P2P functionality for test harness MVP 0.1.

This module provides comprehensive testing for:
- Purchase Requisition creation and management
- Purchase Order creation and management
- Document status tracking
- Error handling and validation
"""

import unittest
from datetime import datetime, timedelta
from typing import Dict, Any, List

from test_harness.mock_sap.p2p_apis import P2PSimulator
from test_harness.mock_sap.sap_types import SAPResponse, SAPError

class TestP2PFlow(unittest.TestCase):
    """Test P2P process flows"""
    
    def setUp(self):
        """Initialize test environment"""
        self.p2p_simulator = P2PSimulator()
        # Reset state explicitly at setup
        self.p2p_simulator.reset_state()
        
        # Default test data
        self.delivery_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Test data - PR
        self.pr_data = {
            'material_id': 'MAT001',
            'quantity': 100,
            'delivery_date': self.delivery_date,
            'plant': 'PLANT_1'
        }
        
        # Test data - Vendor
        self.vendor_id = 'VENDOR001'

        # Error test data
        self.invalid_material_data = {
            **self.pr_data,
            'material_id': 'INVALID'
        }
        
        self.invalid_plant_data = {
            **self.pr_data,
            'plant': 'INVALID_PLANT'
        }
        
        self.zero_quantity_data = {
            **self.pr_data,
            'quantity': 0
        }
    
    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'p2p_simulator'):
            self.p2p_simulator.reset_state()

    # Helper Methods
    async def create_test_pr(self, pr_data: Dict[str, Any] = None) -> SAPResponse:
        """Helper to create a test PR"""
        data = pr_data or self.pr_data
        return await self.p2p_simulator.create_purchase_requisition(data)

    async def create_test_po(self, pr_number: str, vendor_id: str = None) -> SAPResponse:
        """Helper to create a test PO"""
        po_data = {
            'pr_number': pr_number,
            'vendor_id': vendor_id or self.vendor_id
        }
        return await self.p2p_simulator.create_purchase_order(po_data)

    # Standard Flow Tests
    async def test_pr_creation(self):
        """Test purchase requisition creation with valid data"""
        response = await self.create_test_pr()
        
        # Verify success response
        self.assertTrue(response.success)
        self.assertIsNotNone(response.data)
        self.assertIn('pr_number', response.data)
        self.assertEqual(response.data['status'], 'CREATED')
        
        # Verify PR exists in state
        state = self.p2p_simulator.get_state()
        pr_number = response.data['pr_number']
        self.assertIn(pr_number, state['purchase_requisitions'])
        
        # Verify PR data
        pr_record = state['purchase_requisitions'][pr_number]
        self.assertEqual(pr_record['material_id'], self.pr_data['material_id'])
        self.assertEqual(pr_record['quantity'], self.pr_data['quantity'])
        self.assertEqual(pr_record['plant'], self.pr_data['plant'])
    
    async def test_po_creation(self):
        """Test purchase order creation with valid PR"""
        # Create PR first
        pr_response = await self.create_test_pr()
        self.assertTrue(pr_response.success)
        pr_number = pr_response.data['pr_number']
        
        # Create PO
        po_response = await self.create_test_po(pr_number)
        
        # Verify success response
        self.assertTrue(po_response.success)
        self.assertIsNotNone(po_response.data)
        self.assertIn('po_number', po_response.data)
        self.assertEqual(po_response.data['status'], 'CREATED')
        
        # Verify PO exists in state
        state = self.p2p_simulator.get_state()
        po_number = po_response.data['po_number']
        self.assertIn(po_number, state['purchase_orders'])
        
        # Verify PO data
        po_record = state['purchase_orders'][po_number]
        self.assertEqual(po_record['pr_number'], pr_number)
        self.assertEqual(po_record['vendor_id'], self.vendor_id)
    
    async def test_document_status_check(self):
        """Test document status check functionality"""
        # Create PR
        pr_response = await self.create_test_pr()
        self.assertTrue(pr_response.success)
        pr_number = pr_response.data['pr_number']
        
        # Check PR status
        pr_status = await self.p2p_simulator.check_document_status(pr_number, 'PR')
        self.assertTrue(pr_status.success)
        self.assertEqual(pr_status.data['status'], 'CREATED')
        
        # Create PO
        po_response = await self.create_test_po(pr_number)
        self.assertTrue(po_response.success)
        po_number = po_response.data['po_number']
        
        # Check PO status
        po_status = await self.p2p_simulator.check_document_status(po_number, 'PO')
        self.assertTrue(po_status.success)
        self.assertEqual(po_status.data['status'], 'CREATED')
        
        # Check PR status after PO creation
        pr_status_after = await self.p2p_simulator.check_document_status(pr_number, 'PR')
        self.assertTrue(pr_status_after.success)
        self.assertEqual(pr_status_after.data['status'], 'ORDERED')

    # Error Test Cases
    async def test_error_invalid_material(self):
        """Test PR creation with invalid material"""
        response = await self.create_test_pr(self.invalid_material_data)
        
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'PR002')
        self.assertIn('Material INVALID not found', response.error.message)
    
    async def test_error_invalid_plant(self):
        """Test PR creation with invalid plant"""
        response = await self.create_test_pr(self.invalid_plant_data)
        
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'PR003')
        self.assertIn('Plant INVALID_PLANT not found', response.error.message)
    
    async def test_error_zero_quantity(self):
        """Test PR creation with zero quantity"""
        response = await self.create_test_pr(self.zero_quantity_data)
        
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'PR004')
        self.assertIn('Quantity must be greater than zero', response.error.message)
    
    async def test_error_invalid_pr_reference(self):
        """Test PO creation with invalid PR reference"""
        response = await self.create_test_po('INVALID_PR')
        
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'PO002')
        self.assertIn('PR INVALID_PR not found', response.error.message)
    
    async def test_error_invalid_vendor(self):
        """Test PO creation with invalid vendor"""
        # Create valid PR first
        pr_response = await self.create_test_pr()
        self.assertTrue(pr_response.success)
        
        # Try PO with invalid vendor
        response = await self.create_test_po(
            pr_response.data['pr_number'],
            'INVALID_VENDOR'
        )
        
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'PO004')
        self.assertIn('Vendor INVALID_VENDOR not found', response.error.message)
    
    async def test_error_pr_already_ordered(self):
        """Test creating duplicate PO for same PR"""
        # Create PR and first PO
        pr_response = await self.create_test_pr()
        self.assertTrue(pr_response.success)
        pr_number = pr_response.data['pr_number']
        
        # Create first PO
        first_po = await self.create_test_po(pr_number)
        self.assertTrue(first_po.success)
        
        # Try creating second PO
        second_po = await self.create_test_po(pr_number)
        
        self.assertFalse(second_po.success)
        self.assertEqual(second_po.error.code, 'PO003')
        self.assertIn('already ordered', second_po.error.message)
        
        """
Unit tests for SAP mock P2P (Procure-to-Pay) operations - Multi-Document Cases.
Extension of test_p2p_flow.py to add multi-document test scenarios.
"""

# Add these methods to the existing TestP2PFlow class in test_p2p_flow.py

    async def test_multi_create_prs(self):
        """Test creation of multiple PRs in sequence"""
        pr_numbers = []
        quantities = [100, 200, 300]  # Different quantities for each PR
        
        for qty in quantities:
            pr_data = {
                **self.pr_data,
                'quantity': qty
            }
            response = await self.create_test_pr(pr_data)
            self.assertTrue(response.success, "PR creation failed")
            pr_numbers.append(response.data['pr_number'])
        
        # Verify state
        state = self.p2p_simulator.get_state()
        self.assertEqual(
            len(state['purchase_requisitions']), 
            len(quantities),
            "Incorrect number of PRs created"
        )
        
        # Verify quantities
        for pr_number, qty in zip(pr_numbers, quantities):
            pr_record = state['purchase_requisitions'][pr_number]
            self.assertEqual(
                pr_record['quantity'], 
                qty,
                f"Incorrect quantity for PR {pr_number}"
            )
    
    async def test_multi_create_pos(self):
        """Test creation of POs for multiple PRs"""
        # Create PRs
        pr_responses = []
        quantities = [100, 200, 300]
        
        for qty in quantities:
            pr_data = {
                **self.pr_data,
                'quantity': qty
            }
            response = await self.create_test_pr(pr_data)
            self.assertTrue(response.success, "PR creation failed")
            pr_responses.append(response)
        
        # Create POs
        po_numbers = []
        for pr_response in pr_responses:
            response = await self.create_test_po(pr_response.data['pr_number'])
            self.assertTrue(response.success, "PO creation failed")
            po_numbers.append(response.data['po_number'])
        
        # Verify state
        state = self.p2p_simulator.get_state()
        self.assertEqual(
            len(state['purchase_orders']), 
            len(quantities),
            "Incorrect number of POs created"
        )
        
        # Verify all PRs are ordered
        for pr_response in pr_responses:
            pr_number = pr_response.data['pr_number']
            pr_record = state['purchase_requisitions'][pr_number]
            self.assertEqual(
                pr_record['status'], 
                'ORDERED',
                f"PR {pr_number} not in ORDERED status"
            )
    
    async def test_multi_partial_ordering(self):
        """Test partial ordering of multiple PRs"""
        # Create multiple PRs
        pr_responses = []
        quantities = [100, 200, 300, 400]
        
        for qty in quantities:
            pr_data = {
                **self.pr_data,
                'quantity': qty
            }
            response = await self.create_test_pr(pr_data)
            self.assertTrue(response.success, "PR creation failed")
            pr_responses.append(response)
        
        # Order only first two PRs
        ordered_prs = pr_responses[:2]
        for pr_response in ordered_prs:
            response = await self.create_test_po(pr_response.data['pr_number'])
            self.assertTrue(response.success, "PO creation failed")
        
        # Verify state
        state = self.p2p_simulator.get_state()
        self.assertEqual(
            len(state['purchase_orders']), 
            2,
            "Incorrect number of POs created"
        )
        
        # Verify ordered PRs status
        for pr_response in ordered_prs:
            pr_number = pr_response.data['pr_number']
            pr_record = state['purchase_requisitions'][pr_number]
            self.assertEqual(
                pr_record['status'], 
                'ORDERED',
                f"PR {pr_number} not in ORDERED status"
            )
        
        # Verify unordered PRs status
        unordered_prs = pr_responses[2:]
        for pr_response in unordered_prs:
            pr_number = pr_response.data['pr_number']
            pr_record = state['purchase_requisitions'][pr_number]
            self.assertEqual(
                pr_record['status'], 
                'CREATED',
                f"PR {pr_number} not in CREATED status"
            )

    async def test_multi_document_validation(self):
        """Test validation across multiple documents"""
        # Create PRs with same material
        pr_responses = []
        for _ in range(3):
            response = await self.create_test_pr()
            self.assertTrue(response.success, "PR creation failed")
            pr_responses.append(response)
        
        # Verify material consistency
        state = self.p2p_simulator.get_state()
        for pr_response in pr_responses:
            pr_number = pr_response.data['pr_number']
            pr_record = state['purchase_requisitions'][pr_number]
            self.assertEqual(
                pr_record['material_id'], 
                self.pr_data['material_id'],
                f"Incorrect material ID for PR {pr_number}"
            )
        
        # Create POs with same vendor
        for pr_response in pr_responses:
            response = await self.create_test_po(pr_response.data['pr_number'])
            self.assertTrue(response.success, "PO creation failed")
        
        # Verify final state
        final_state = self.p2p_simulator.get_state()
        self.assertEqual(
            len(final_state['purchase_requisitions']), 
            len(pr_responses),
            "Incorrect number of PRs in final state"
        )
        self.assertEqual(
            len(final_state['purchase_orders']), 
            len(pr_responses),
            "Incorrect number of POs in final state"
        )
    
    async def test_multi_document_state_consistency(self):
        """Test state consistency with multiple documents"""
        # Create multiple PRs
        quantities = [100, 200, 300]
        pr_numbers = []
        
        for qty in quantities:
            pr_data = {
                **self.pr_data,
                'quantity': qty
            }
            response = await self.create_test_pr(pr_data)
            self.assertTrue(response.success, "PR creation failed")
            pr_numbers.append(response.data['pr_number'])
        
        # Check intermediate state
        mid_state = self.p2p_simulator.get_state()
        self.assertEqual(
            len(mid_state['purchase_requisitions']), 
            len(quantities),
            "Incorrect number of PRs in intermediate state"
        )
        self.assertEqual(
            len(mid_state['purchase_orders']), 
            0,
            "Unexpected POs in intermediate state"
        )
        
        # Create POs for each PR
        po_numbers = []
        for pr_number in pr_numbers:
            response = await self.create_test_po(pr_number)
            self.assertTrue(response.success, "PO creation failed")
            po_numbers.append(response.data['po_number'])
        
        # Check final state
        final_state = self.p2p_simulator.get_state()
        self.assertEqual(
            len(final_state['purchase_requisitions']), 
            len(quantities),
            "Incorrect number of PRs in final state"
        )
        self.assertEqual(
            len(final_state['purchase_orders']), 
            len(quantities),
            "Incorrect number of POs in final state"
        )
        
        # Verify document relationships
        for pr_number, po_number in zip(pr_numbers, po_numbers):
            po_record = final_state['purchase_orders'][po_number]
            self.assertEqual(
                po_record['pr_number'], 
                pr_number,
                f"Incorrect PR reference in PO {po_number}"
            )