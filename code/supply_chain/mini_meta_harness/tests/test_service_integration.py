# tests/test_service_integration.py
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from models.material import (
    Material, MaterialCreate, MaterialUpdate, MaterialType, MaterialStatus
)
from models.p2p import (
    Requisition, RequisitionCreate, RequisitionItem,
    Order, OrderCreate, OrderItem,
    DocumentStatus
)
from services.material_service import MaterialService
from services.p2p_service import P2PService
from services.state_manager import StateManager
from utils.error_utils import NotFoundError, ValidationError

class TestServiceIntegration:
    """
    Tests for integration between Material and P2P services.
    These tests verify that the services work correctly together.
    """

    def setup_method(self):
        """Set up test environment before each test"""
        # Create a shared state manager for testing
        self.state_manager = StateManager()
        
        # Create service instances for testing
        self.material_service = MaterialService(self.state_manager)
        self.p2p_service = P2PService(self.state_manager, self.material_service)
        
        # Create some test materials
        self.material_service.create_material(
            MaterialCreate(
                material_number="MAT001",
                name="Test Material 1",
                type=MaterialType.RAW,
                description="Test material for integration tests"
            )
        )
        self.material_service.create_material(
            MaterialCreate(
                material_number="MAT002",
                name="Test Material 2",
                type=MaterialType.FINISHED,
                description="Another test material"
            )
        )
    
    def test_create_requisition_with_materials(self):
        """Test creating a requisition that references materials"""
        # Create a requisition with references to materials
        req_data = RequisitionCreate(
            document_number="REQWITHMATERIALS",
            description="Requisition with Materials",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="MAT001",
                    description="Raw Material Item",
                    quantity=10,
                    unit="KG",
                    price=50
                ),
                RequisitionItem(
                    item_number=2,
                    material_number="MAT002",
                    description="Finished Material Item",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        
        # Verify the requisition was created with material references
        assert requisition.document_number == "REQWITHMATERIALS"
        assert len(requisition.items) == 2
        assert requisition.items[0].material_number == "MAT001"
        assert requisition.items[1].material_number == "MAT002"
    
    def test_create_requisition_with_invalid_material(self):
        """Test creating a requisition with a non-existent material"""
        # Try to create a requisition with a non-existent material
        req_data = RequisitionCreate(
            description="Requisition with Invalid Material",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="NONEXISTENT",  # Non-existent material
                    description="Invalid Material Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        # Should raise ValidationError
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.create_requisition(req_data)
        
        # Verify error message mentions the invalid material
        assert "Material NONEXISTENT not found" in str(excinfo.value)
    
    def test_create_requisition_with_inactive_material(self):
        """Test creating a requisition with an inactive material"""
        # Create a material and then mark it as inactive
        self.material_service.create_material(
            MaterialCreate(
                material_number="INACTIVE001",
                name="Inactive Material",
                type=MaterialType.RAW
            )
        )
        
        # Make the material inactive
        self.material_service.update_material(
            "INACTIVE001",
            MaterialUpdate(status=MaterialStatus.INACTIVE)
        )
        
        # Try to create a requisition with the inactive material
        req_data = RequisitionCreate(
            description="Requisition with Inactive Material",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="INACTIVE001",
                    description="Inactive Material Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        # Should raise ValidationError
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.create_requisition(req_data)
        
        # Verify error message mentions the material is not active
        assert "Material INACTIVE001 is not active" in str(excinfo.value)
    
    def test_end_to_end_procurement_flow(self):
        """Test the end-to-end procurement flow from requisition to order"""
        # 1. Create a requisition
        req_data = RequisitionCreate(
            document_number="FLOW001",
            description="Flow Test Requisition",
            requester="Test User",
            department="Procurement",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="MAT001",
                    description="Raw Material Item",
                    quantity=10,
                    unit="KG",
                    price=50
                ),
                RequisitionItem(
                    item_number=2,
                    material_number="MAT002",
                    description="Finished Material Item",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        assert requisition.status == DocumentStatus.DRAFT
        
        # 2. Submit the requisition
        submitted_req = self.p2p_service.submit_requisition("FLOW001")
        assert submitted_req.status == DocumentStatus.SUBMITTED
        
        # 3. Approve the requisition
        approved_req = self.p2p_service.approve_requisition("FLOW001")
        assert approved_req.status == DocumentStatus.APPROVED
        
        # 4. Create an order from the requisition
        order = self.p2p_service.create_order_from_requisition(
            requisition_number="FLOW001",
            vendor="Test Vendor",
            payment_terms="Net 30"
        )
        
        assert order is not None
        assert order.requisition_reference == "FLOW001"
        assert len(order.items) == 2
        assert order.items[0].material_number == "MAT001"
        assert order.items[1].material_number == "MAT002"
        
        # 5. Check that the requisition status was updated
        updated_req = self.p2p_service.get_requisition("FLOW001")
        assert updated_req.status == DocumentStatus.ORDERED
    
    def test_material_status_affects_procurement(self):
        """Test that changes in material status affect the procurement process"""
        # Create a requisition with a material
        req_data = RequisitionCreate(
            document_number="MATSTATUSTEST",
            description="Material Status Test",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="MAT001",
                    description="Test Material Item",
                    quantity=10,
                    unit="KG",
                    price=50
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        
        # Now deprecate the material
        self.material_service.deprecate_material("MAT001")
        
        # Create a new requisition with the same (now deprecated) material
        req_data2 = RequisitionCreate(
            description="Material Status Test 2",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="MAT001",
                    description="Deprecated Material Item",
                    quantity=10,
                    unit="KG",
                    price=50
                )
            ]
        )
        
        # This should now fail because the material is deprecated
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.create_requisition(req_data2)
        
        assert "Material MAT001 is not active" in str(excinfo.value)
    
    def test_order_creation_with_material_validation(self):
        """Test that order creation validates material status"""
        # Create a material that we'll immediately deprecate
        self.material_service.create_material(
            MaterialCreate(
                material_number="QUICKDEPRECATE",
                name="Quickly Deprecated Material"
            )
        )
        
        # Deprecate the material
        self.material_service.deprecate_material("QUICKDEPRECATE")
        
        # Try to create an order with the deprecated material
        order_data = OrderCreate(
            description="Order with Deprecated Material",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    material_number="QUICKDEPRECATE",
                    description="Deprecated Material Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        # Should raise ValidationError
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.create_order(order_data)
        
        assert "Material QUICKDEPRECATE is not active" in str(excinfo.value)