# tests/test_service_integration.py
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

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
from services import (
    get_material_service, get_p2p_service, 
    register_service, get_service, clear_service_registry
)
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
        
        # Clear the service registry to ensure a clean state
        clear_service_registry()
        
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
        assert "Invalid material" in str(excinfo.value.message)
        assert "NONEXISTENT" in str(excinfo.value.message)
        
        # Check error details
        if hasattr(excinfo.value, 'details'):
            assert excinfo.value.details.get("material_number") == "NONEXISTENT"
    
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
        
        # It should actually work with INACTIVE materials (just not DEPRECATED ones)
        requisition = self.p2p_service.create_requisition(req_data)
        assert requisition is not None
        assert requisition.items[0].material_number == "INACTIVE001"
        
        # Now let's deprecate a material and verify it fails
        self.material_service.deprecate_material("INACTIVE001")
        
        req_data = RequisitionCreate(
            description="Requisition with Deprecated Material",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="INACTIVE001",
                    description="Deprecated Material Item",
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
        assert "Invalid material" in str(excinfo.value.message)
        assert "INACTIVE001" in str(excinfo.value.message)
    
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
        
        assert "Invalid material" in str(excinfo.value.message)
        assert "MAT001" in str(excinfo.value.message)
    
    def test_service_factory_dependency_injection(self):
        """Test that the service factory correctly handles dependency injection"""
        # Clear service registry
        clear_service_registry()
        
        # Create a test state manager
        test_state_manager = StateManager()
        
        # Get a material service instance with the test state manager
        material_service = get_material_service(test_state_manager)
        
        # Verify it's using our test state manager
        assert material_service.state_manager is test_state_manager
        
        # Add a test material
        material_service.create_material(
            MaterialCreate(
                material_number="FACTORY001",
                name="Factory Test Material"
            )
        )
        
        # Get a P2P service with the same state manager
        p2p_service = get_p2p_service(test_state_manager)
        
        # Verify it's using our test state manager and the material service we created
        assert p2p_service.state_manager is test_state_manager
        assert p2p_service.material_service.state_manager is test_state_manager
        
        # Verify we can access the material we created
        material = p2p_service.material_service.get_material("FACTORY001")
        assert material.name == "Factory Test Material"
    
    def test_service_registry(self):
        """Test the service registry functionality"""
        # Clear service registry
        clear_service_registry()
        
        # Create mock services
        mock_material_service = MagicMock()
        mock_p2p_service = MagicMock()
        
        # Register the mock services
        register_service("material", mock_material_service)
        register_service("p2p", mock_p2p_service)
        
        # Get the services from the registry
        retrieved_material_service = get_service("material")
        retrieved_p2p_service = get_service("p2p")
        
        # Verify we got the correct services
        assert retrieved_material_service is mock_material_service
        assert retrieved_p2p_service is mock_p2p_service
        
        # Verify behavior when service doesn't exist
        with pytest.raises(KeyError):
            get_service("nonexistent")
    
    def test_error_propagation_between_services(self):
        """Test that errors are properly propagated between services"""
        # Create a mock material service that raises NotFoundError
        mock_material_service = MagicMock()
        mock_material_service.get_material.side_effect = NotFoundError(
            message="Material not found in mock",
            details={"material_id": "MOCKMAT001"}
        )
        
        # Create a P2P service with the mock material service
        p2p_service = P2PService(self.state_manager, mock_material_service)
        
        # Create a requisition that references the non-existent material
        req_data = RequisitionCreate(
            description="Requisition with Mock Material",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="MOCKMAT001",
                    description="Mock Material Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        # This should raise ValidationError due to the NotFoundError from the material service
        with pytest.raises(ValidationError) as excinfo:
            p2p_service.create_requisition(req_data)
        
        # Verify error message includes information from the material service error
        assert "Invalid material" in str(excinfo.value.message)
        assert "MOCKMAT001" in str(excinfo.value.message)
        
        # Verify the material service was called with the correct material ID
        mock_material_service.get_material.assert_called_with("MOCKMAT001")
