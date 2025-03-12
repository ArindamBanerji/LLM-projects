# tests/test_p2p_requisition_service.py
"""
Tests specifically for requisition operations in the P2P service.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from models.p2p import (
    RequisitionCreate, RequisitionUpdate, RequisitionItem,
    DocumentStatus, ProcurementType
)
from models.material import (
    MaterialCreate, MaterialType, MaterialStatus
)
from services.p2p_service import P2PService
from services.material_service import MaterialService
from services.state_manager import StateManager
from utils.error_utils import NotFoundError, ValidationError, ConflictError

class TestP2PRequisitionService:
    """Tests for requisition operations in the P2P service."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create a clean state manager
        self.state_manager = StateManager()
        
        # Create a material service instance
        self.material_service = MaterialService(self.state_manager)
        
        # Create some test materials
        self.material_service.create_material(
            MaterialCreate(
                material_number="MAT001",
                name="Test Material 1",
                type=MaterialType.RAW
            )
        )
        self.material_service.create_material(
            MaterialCreate(
                material_number="MAT002",
                name="Test Material 2",
                type=MaterialType.FINISHED
            )
        )
        
        # Create the P2P service with the test state manager
        self.p2p_service = P2PService(self.state_manager, self.material_service)
    
    def test_create_requisition_minimal(self):
        """Test creating a requisition with minimal required fields."""
        # Create a requisition with minimal fields
        req_data = RequisitionCreate(
            description="Minimal Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        
        # Verify basic properties
        assert requisition.description == "Minimal Requisition"
        assert requisition.requester == "Test User"
        assert requisition.status == DocumentStatus.DRAFT
        assert len(requisition.items) == 1
        assert requisition.items[0].item_number == 1
        assert requisition.items[0].description == "Test Item"
        assert requisition.items[0].quantity == 10
        assert requisition.items[0].price == 100
        
        # Material number should be automatically generated
        assert requisition.document_number is not None
        assert requisition.document_number.startswith("PR")
    
    def test_create_requisition_full(self):
        """Test creating a requisition with all fields provided."""
        # Create a requisition with all fields
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Full Requisition",
            requester="Test User",
            department="IT",
            type=ProcurementType.SERVICE,
            notes="Test notes",
            urgent=True,
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="MAT001",
                    description="Material Item",
                    quantity=10,
                    unit="KG",
                    price=50
                ),
                RequisitionItem(
                    item_number=2,
                    description="Non-Material Item",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        
        # Verify all fields
        assert requisition.document_number == "PR001"
        assert requisition.description == "Full Requisition"
        assert requisition.requester == "Test User"
        assert requisition.department == "IT"
        assert requisition.type == ProcurementType.SERVICE
        assert requisition.notes == "Test notes"
        assert requisition.urgent is True
        assert requisition.status == DocumentStatus.DRAFT
        assert len(requisition.items) == 2
        assert requisition.items[0].material_number == "MAT001"
        assert requisition.items[1].material_number is None
    
    def test_create_requisition_duplicate_number(self):
        """Test creating a requisition with a duplicate document number."""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="First Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        self.p2p_service.create_requisition(req_data)
        
        # Try to create another with the same number
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Duplicate Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        with pytest.raises(ConflictError) as excinfo:
            self.p2p_service.create_requisition(req_data)
        
        # Check error details
        assert "already exists" in str(excinfo.value.message)
        assert "PR001" in str(excinfo.value.message)
        if hasattr(excinfo.value, 'details'):
            assert excinfo.value.details.get("document_number") == "PR001"
            assert excinfo.value.details.get("conflict_reason") == "document_number_exists"
    
    def test_create_requisition_invalid_material(self):
        """Test creating a requisition with an invalid material reference."""
        # Try to create a requisition with a non-existent material
        req_data = RequisitionCreate(
            description="Invalid Material Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="NONEXISTENT",
                    description="Invalid Material Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.create_requisition(req_data)
        
        # Check error details
        assert "Invalid material" in str(excinfo.value.message)
        assert "NONEXISTENT" in str(excinfo.value.message)
    
    def test_update_requisition_description(self):
        """Test updating a requisition's description."""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Original Description",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        
        # Update the description
        update_data = RequisitionUpdate(description="Updated Description")
        updated = self.p2p_service.update_requisition("PR001", update_data)
        
        # Verify update
        assert updated.description == "Updated Description"
        assert updated.requester == "Test User"  # Unchanged
        assert updated.status == DocumentStatus.DRAFT  # Unchanged
    
    def test_update_requisition_items_in_draft(self):
        """Test updating a requisition's items while in DRAFT status."""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Original Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Original Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        
        # Update the items
        update_data = RequisitionUpdate(
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Updated Item",
                    quantity=20,
                    unit="EA",
                    price=90
                ),
                RequisitionItem(
                    item_number=2,
                    description="New Item",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        updated = self.p2p_service.update_requisition("PR001", update_data)
        
        # Verify update
        assert len(updated.items) == 2
        assert updated.items[0].description == "Updated Item"
        assert updated.items[0].quantity == 20
        assert updated.items[0].price == 90
        assert updated.items[1].description == "New Item"
    
    def test_update_requisition_items_after_submission(self):
        """Test that requisition items cannot be updated after submission."""
        # Create and submit a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Submitted Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Original Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        self.p2p_service.submit_requisition("PR001")
        
        # Try to update the items
        update_data = RequisitionUpdate(
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Updated Item",
                    quantity=20,
                    unit="EA",
                    price=90
                )
            ]
        )
        
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.update_requisition("PR001", update_data)
        
        # Check error details
        assert "Cannot update items" in str(excinfo.value.message)
        if hasattr(excinfo.value, 'details'):
            assert excinfo.value.details.get("reason") == "items_locked_after_submission"
    
    def test_submit_requisition(self):
        """Test submitting a requisition."""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Draft Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        
        # Submit the requisition
        submitted = self.p2p_service.submit_requisition("PR001")
        
        # Verify status change
        assert submitted.status == DocumentStatus.SUBMITTED
    
    def test_approve_requisition(self):
        """Test approving a requisition."""
        # Create and submit a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Submitted Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        self.p2p_service.submit_requisition("PR001")
        
        # Approve the requisition
        approved = self.p2p_service.approve_requisition("PR001")
        
        # Verify status change
        assert approved.status == DocumentStatus.APPROVED
    
    def test_reject_requisition(self):
        """Test rejecting a requisition."""
        # Create and submit a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Submitted Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        self.p2p_service.submit_requisition("PR001")
        
        # Reject the requisition
        rejected = self.p2p_service.reject_requisition("PR001", "Budget exceeded")
        
        # Verify status change and notes
        assert rejected.status == DocumentStatus.REJECTED
        assert "REJECTED: Budget exceeded" in rejected.notes
    
    def test_invalid_requisition_status_transitions(self):
        """Test invalid requisition status transitions."""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Draft Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        
        # Try to approve from DRAFT (should fail)
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.approve_requisition("PR001")
        
        assert "Cannot approve requisition" in str(excinfo.value.message)
        
        # Try to reject from DRAFT (should fail)
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.reject_requisition("PR001", "Not allowed")
        
        assert "Cannot reject requisition" in str(excinfo.value.message)
        
        # Submit the requisition
        self.p2p_service.submit_requisition("PR001")
        
        # Try to submit again (should fail)
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.submit_requisition("PR001")
        
        assert "Cannot submit requisition" in str(excinfo.value.message)
    
    def test_delete_requisition(self):
        """Test deleting a requisition."""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Draft Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        
        # Delete the requisition
        result = self.p2p_service.delete_requisition("PR001")
        
        # Verify deletion
        assert result is True
        
        # Verify it's gone
        with pytest.raises(NotFoundError):
            self.p2p_service.get_requisition("PR001")
    
    def test_delete_submitted_requisition(self):
        """Test that submitted requisitions cannot be deleted."""
        # Create and submit a requisition
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Submitted Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        requisition = self.p2p_service.create_requisition(req_data)
        self.p2p_service.submit_requisition("PR001")
        
        # Try to delete the requisition
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.delete_requisition("PR001")
        
        # Check error details
        assert "Cannot delete requisition" in str(excinfo.value.message)
        if hasattr(excinfo.value, 'details'):
            assert excinfo.value.details.get("current_status") == DocumentStatus.SUBMITTED.value
            assert DocumentStatus.DRAFT.value in excinfo.value.details.get("allowed_statuses", [])
    
    def test_filter_requisitions(self):
        """Test filtering requisitions with various criteria."""
        # Create some requisitions with different attributes
        for i in range(5):
            req_data = RequisitionCreate(
                document_number=f"PR00{i+1}",
                description=f"Test Requisition {i+1}",
                requester="User A" if i % 2 == 0 else "User B",
                department="IT" if i % 3 == 0 else "Finance",
                items=[
                    RequisitionItem(
                        item_number=1,
                        description=f"Test Item {i+1}",
                        quantity=10,
                        unit="EA",
                        price=100
                    )
                ]
            )
            self.p2p_service.create_requisition(req_data)
        
        # Submit some requisitions
        self.p2p_service.submit_requisition("PR001")
        self.p2p_service.submit_requisition("PR002")
        
        # Approve one requisition
        self.p2p_service.approve_requisition("PR001")
        
        # Filter by status
        draft_reqs = self.p2p_service.list_requisitions(status=DocumentStatus.DRAFT)
        assert len(draft_reqs) == 3
        
        submitted_reqs = self.p2p_service.list_requisitions(status=DocumentStatus.SUBMITTED)
        assert len(submitted_reqs) == 1
        
        approved_reqs = self.p2p_service.list_requisitions(status=DocumentStatus.APPROVED)
        assert len(approved_reqs) == 1
        
        # Filter by requester
        user_a_reqs = self.p2p_service.list_requisitions(requester="User A")
        assert len(user_a_reqs) == 3
        
        # Filter by department
        it_reqs = self.p2p_service.list_requisitions(department="IT")
        assert len(it_reqs) == 2
        
        # Filter by search term
        search_reqs = self.p2p_service.list_requisitions(search_term="Test Requisition 3")
        assert len(search_reqs) == 1
        assert search_reqs[0].document_number == "PR003"
