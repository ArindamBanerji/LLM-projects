# tests/test_p2p_order_service.py
"""
Tests specifically for order operations in the P2P service.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from models.p2p import (
    RequisitionCreate, RequisitionItem,
    OrderCreate, OrderUpdate, OrderItem,
    DocumentStatus, ProcurementType
)
from models.material import (
    MaterialCreate, MaterialType, MaterialStatus
)
from services.p2p_service import P2PService
from services.material_service import MaterialService
from services.state_manager import StateManager
from utils.error_utils import NotFoundError, ValidationError, ConflictError, BadRequestError

class TestP2POrderService:
    """Tests for order operations in the P2P service."""
    
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
        
        # Create a test requisition
        self._create_test_requisition()
    
    def _create_test_requisition(self):
        """Helper to create a test requisition that can be used for order tests."""
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Test Requisition",
            requester="Test User",
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
        self.p2p_service.submit_requisition("PR001")
        self.p2p_service.approve_requisition("PR001")
    
    def test_create_order_minimal(self):
        """Test creating an order with minimal required fields."""
        # Create an order with minimal fields
        order_data = OrderCreate(
            description="Minimal Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        
        # Verify basic properties
        assert order.description == "Minimal Order"
        assert order.requester == "Test User"
        assert order.vendor == "Test Vendor"
        assert order.status == DocumentStatus.DRAFT
        assert len(order.items) == 1
        assert order.items[0].item_number == 1
        assert order.items[0].description == "Test Item"
        assert order.items[0].quantity == 10
        assert order.items[0].price == 100
        
        # Order number should be automatically generated
        assert order.document_number is not None
        assert order.document_number.startswith("PO")
    
    def test_create_order_full(self):
        """Test creating an order with all fields provided."""
        # Create an order with all fields
        order_data = OrderCreate(
            document_number="PO001",
            description="Full Order",
            requester="Test User",
            department="IT",
            vendor="Test Vendor",
            payment_terms="Net 30",
            type=ProcurementType.SERVICE,
            notes="Test notes",
            urgent=True,
            items=[
                OrderItem(
                    item_number=1,
                    material_number="MAT001",
                    description="Material Item",
                    quantity=10,
                    unit="KG",
                    price=50
                ),
                OrderItem(
                    item_number=2,
                    description="Non-Material Item",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        
        # Verify all fields
        assert order.document_number == "PO001"
        assert order.description == "Full Order"
        assert order.requester == "Test User"
        assert order.department == "IT"
        assert order.vendor == "Test Vendor"
        assert order.payment_terms == "Net 30"
        assert order.type == ProcurementType.SERVICE
        assert order.notes == "Test notes"
        assert order.urgent is True
        assert order.status == DocumentStatus.DRAFT
        assert len(order.items) == 2
        assert order.items[0].material_number == "MAT001"
        assert order.items[1].material_number is None
    
    def test_create_order_duplicate_number(self):
        """Test creating an order with a duplicate document number."""
        # Create an order
        order_data = OrderCreate(
            document_number="PO001",
            description="First Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        self.p2p_service.create_order(order_data)
        
        # Try to create another with the same number
        order_data = OrderCreate(
            document_number="PO001",
            description="Duplicate Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        with pytest.raises(ConflictError) as excinfo:
            self.p2p_service.create_order(order_data)
        
        # Check error details
        assert "already exists" in str(excinfo.value.message)
        assert "PO001" in str(excinfo.value.message)
        if hasattr(excinfo.value, 'details'):
            assert excinfo.value.details.get("document_number") == "PO001"
            assert excinfo.value.details.get("conflict_reason") == "document_number_exists"
    
    def test_create_order_invalid_material(self):
        """Test creating an order with an invalid material reference."""
        # Try to create an order with a non-existent material
        order_data = OrderCreate(
            description="Invalid Material Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
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
            self.p2p_service.create_order(order_data)
        
        # Check error details
        assert "Invalid material" in str(excinfo.value.message)
        assert "NONEXISTENT" in str(excinfo.value.message)
    
    def test_create_order_from_requisition(self):
        """Test creating an order from a requisition."""
        # Create an order from the test requisition
        order = self.p2p_service.create_order_from_requisition(
            requisition_number="PR001",
            vendor="Test Vendor",
            payment_terms="Net 30"
        )
        
        # Verify order properties
        assert order.vendor == "Test Vendor"
        assert order.payment_terms == "Net 30"
        assert order.requisition_reference == "PR001"
        assert order.status == DocumentStatus.DRAFT
        assert len(order.items) == 2
        
        # Check items were properly transferred from requisition
        assert order.items[0].material_number == "MAT001"
        assert order.items[0].quantity == 10
        assert order.items[0].price == 50
        assert order.items[0].requisition_reference == "PR001"
        assert order.items[0].requisition_item == 1
        
        # Check requisition status was updated
        requisition = self.p2p_service.get_requisition("PR001")
        assert requisition.status == DocumentStatus.ORDERED
        assert requisition.items[0].assigned_to_order == order.document_number
    
    def test_create_order_from_nonexistent_requisition(self):
        """Test creating an order from a non-existent requisition."""
        with pytest.raises(NotFoundError) as excinfo:
            self.p2p_service.create_order_from_requisition(
                requisition_number="NONEXISTENT",
                vendor="Test Vendor"
            )
        
        # Check error details
        assert "not found" in str(excinfo.value.message)
        assert "NONEXISTENT" in str(excinfo.value.message)
    
    def test_create_order_from_non_approved_requisition(self):
        """Test creating an order from a requisition that is not approved."""
        # Create a new draft requisition
        req_data = RequisitionCreate(
            document_number="PR002",
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
        
        self.p2p_service.create_requisition(req_data)
        
        # Try to create an order from it
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.create_order_from_requisition(
                requisition_number="PR002",
                vendor="Test Vendor"
            )
        
        # Check error details
        assert "Cannot create order from requisition" in str(excinfo.value.message)
        assert "Must be APPROVED" in str(excinfo.value.message)
    
    def test_update_order_description(self):
        """Test updating an order's description."""
        # Create an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Original Description",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        
        # Update the description
        update_data = OrderUpdate(description="Updated Description")
        updated = self.p2p_service.update_order("PO001", update_data)
        
        # Verify update
        assert updated.description == "Updated Description"
        assert updated.vendor == "Test Vendor"  # Unchanged
        assert updated.status == DocumentStatus.DRAFT  # Unchanged
    
    def test_update_order_items_in_draft(self):
        """Test updating an order's items while in DRAFT status."""
        # Create an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Original Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Original Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        
        # Update the items
        update_data = OrderUpdate(
            items=[
                OrderItem(
                    item_number=1,
                    description="Updated Item",
                    quantity=20,
                    unit="EA",
                    price=90
                ),
                OrderItem(
                    item_number=2,
                    description="New Item",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        updated = self.p2p_service.update_order("PO001", update_data)
        
        # Verify update
        assert len(updated.items) == 2
        assert updated.items[0].description == "Updated Item"
        assert updated.items[0].quantity == 20
        assert updated.items[0].price == 90
        assert updated.items[1].description == "New Item"
    
    def test_update_order_items_after_submission(self):
        """Test that order items cannot be updated after submission."""
        # Create and submit an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Submitted Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Original Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        self.p2p_service.submit_order("PO001")
        
        # Try to update the items
        update_data = OrderUpdate(
            items=[
                OrderItem(
                    item_number=1,
                    description="Updated Item",
                    quantity=20,
                    unit="EA",
                    price=90
                )
            ]
        )
        
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.update_order("PO001", update_data)
        
        # Check error details
        assert "Cannot update items" in str(excinfo.value.message)
        if hasattr(excinfo.value, 'details'):
            assert excinfo.value.details.get("reason") == "items_locked_after_submission"
    
    def test_submit_order(self):
        """Test submitting an order."""
        # Create an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Draft Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        
        # Submit the order
        submitted = self.p2p_service.submit_order("PO001")
        
        # Verify status change
        assert submitted.status == DocumentStatus.SUBMITTED
    
    def test_approve_order(self):
        """Test approving an order."""
        # Create and submit an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Submitted Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        self.p2p_service.submit_order("PO001")
        
        # Approve the order
        approved = self.p2p_service.approve_order("PO001")
        
        # Verify status change
        assert approved.status == DocumentStatus.APPROVED
    
    def test_receive_order_full(self):
        """Test receiving an order in full."""
        # Create, submit, and approve an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Order to Receive",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Item 1",
                    quantity=10,
                    unit="EA",
                    price=100
                ),
                OrderItem(
                    item_number=2,
                    description="Item 2",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        self.p2p_service.submit_order("PO001")
        self.p2p_service.approve_order("PO001")
        
        # Receive the order in full (no items specified = receive all)
        received = self.p2p_service.receive_order("PO001")
        
        # Verify status change and received quantities
        assert received.status == DocumentStatus.RECEIVED
        assert received.items[0].status == DocumentStatus.RECEIVED
        assert received.items[0].received_quantity == 10
        assert received.items[1].status == DocumentStatus.RECEIVED
        assert received.items[1].received_quantity == 5
    
    def test_receive_order_partial(self):
        """Test receiving an order partially."""
        # Create, submit, and approve an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Order to Receive",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Item 1",
                    quantity=10,
                    unit="EA",
                    price=100
                ),
                OrderItem(
                    item_number=2,
                    description="Item 2",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        self.p2p_service.submit_order("PO001")
        self.p2p_service.approve_order("PO001")
        
        # Receive the order partially
        received_items = {
            1: 5,  # Receive 5 of item 1
            2: 3   # Receive 3 of item 2
        }
        
        received = self.p2p_service.receive_order("PO001", received_items)
        
        # Verify status change and received quantities
        assert received.status == DocumentStatus.PARTIALLY_RECEIVED
        assert received.items[0].status == DocumentStatus.PARTIALLY_RECEIVED
        assert received.items[0].received_quantity == 5
        assert received.items[1].status == DocumentStatus.PARTIALLY_RECEIVED
        assert received.items[1].received_quantity == 3
    
    def test_receive_order_invalid_quantities(self):
        """Test receiving an order with invalid quantities."""
        # Create, submit, and approve an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Order to Receive",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Item 1",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        self.p2p_service.submit_order("PO001")
        self.p2p_service.approve_order("PO001")
        
        # Try to receive negative quantity
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.receive_order("PO001", {1: -5})
        
        assert "Received quantities cannot be negative" in str(excinfo.value.message)
        
        # Try to receive more than ordered
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.receive_order("PO001", {1: 15})
        
        assert "Received quantity exceeds" in str(excinfo.value.message)
    
    def test_complete_order(self):
        """Test completing an order."""
        # Create, submit, approve, and receive an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Order to Complete",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        self.p2p_service.submit_order("PO001")
        self.p2p_service.approve_order("PO001")
        self.p2p_service.receive_order("PO001")
        
        # Complete the order
        completed = self.p2p_service.complete_order("PO001")
        
        # Verify status change
        assert completed.status == DocumentStatus.COMPLETED
    
    def test_cancel_order(self):
        """Test canceling an order."""
        # Create an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Order to Cancel",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        
        # Cancel the order
        canceled = self.p2p_service.cancel_order("PO001", "Budget freeze")
        
        # Verify status change and notes
        assert canceled.status == DocumentStatus.CANCELED
        assert "CANCELED: Budget freeze" in canceled.notes
    
    def test_invalid_order_status_transitions(self):
        """Test invalid order status transitions."""
        # Create an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Draft Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        
        # Try to approve from DRAFT (should fail)
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.approve_order("PO001")
        
        assert "Cannot approve order" in str(excinfo.value.message)
        
        # Try to receive from DRAFT (should fail)
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.receive_order("PO001")
        
        assert "Cannot receive order" in str(excinfo.value.message)
        
        # Try to complete from DRAFT (should fail)
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.complete_order("PO001")
        
        assert "Cannot complete order" in str(excinfo.value.message)
        
        # Submit the order
        self.p2p_service.submit_order("PO001")
        
        # Try to submit again (should fail)
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.submit_order("PO001")
        
        assert "Cannot submit order" in str(excinfo.value.message)
    
    def test_delete_order(self):
        """Test deleting an order."""
        # Create an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Draft Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        
        # Delete the order
        result = self.p2p_service.delete_order("PO001")
        
        # Verify deletion
        assert result is True
        
        # Verify it's gone
        with pytest.raises(NotFoundError):
            self.p2p_service.get_order("PO001")
    
    def test_delete_submitted_order(self):
        """Test that submitted orders cannot be deleted."""
        # Create and submit an order
        order_data = OrderCreate(
            document_number="PO001",
            description="Submitted Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        self.p2p_service.submit_order("PO001")
        
        # Try to delete the order
        with pytest.raises(ValidationError) as excinfo:
            self.p2p_service.delete_order("PO001")
        
        # Check error details
        assert "Cannot delete order" in str(excinfo.value.message)
        if hasattr(excinfo.value, 'details'):
            assert excinfo.value.details.get("current_status") == DocumentStatus.SUBMITTED.value
            assert excinfo.value.details.get("allowed_status") == DocumentStatus.DRAFT.value
    
    def test_filter_orders(self):
        """Test filtering orders with various criteria."""
        # Create some orders with different attributes
        for i in range(5):
            order_data = OrderCreate(
                document_number=f"PO00{i+1}",
                description=f"Test Order {i+1}",
                requester="User A" if i % 2 == 0 else "User B",
                vendor="Vendor X" if i % 3 == 0 else "Vendor Y",
                items=[
                    OrderItem(
                        item_number=1,
                        description=f"Test Item {i+1}",
                        quantity=10,
                        unit="EA",
                        price=100
                    )
                ]
            )
            self.p2p_service.create_order(order_data)
        
        # Submit some orders
        self.p2p_service.submit_order("PO001")
        self.p2p_service.submit_order("PO002")
        
        # Approve one order
        self.p2p_service.approve_order("PO001")
        
        # Filter by status
        draft_orders = self.p2p_service.list_orders(status=DocumentStatus.DRAFT)
        assert len(draft_orders) == 3
        
        submitted_orders = self.p2p_service.list_orders(status=DocumentStatus.SUBMITTED)
        assert len(submitted_orders) == 1
        
        approved_orders = self.p2p_service.list_orders(status=DocumentStatus.APPROVED)
        assert len(approved_orders) == 1
        
        # Filter by vendor
        vendor_x_orders = self.p2p_service.list_orders(vendor="Vendor X")
        assert len(vendor_x_orders) == 2
        
        # Filter by search term
        search_orders = self.p2p_service.list_orders(search_term="Test Order 3")
        assert len(search_orders) == 1
        assert search_orders[0].document_number == "PO003"
