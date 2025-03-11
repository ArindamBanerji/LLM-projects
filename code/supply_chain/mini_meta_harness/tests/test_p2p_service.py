# tests/test_p2p_service.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from models.p2p import (
    Requisition, RequisitionCreate, RequisitionUpdate, RequisitionItem,
    Order, OrderCreate, OrderUpdate, OrderItem,
    DocumentStatus, DocumentItemStatus, ProcurementType,
    P2PDataLayer
)
from models.material import (
    Material, MaterialCreate, MaterialStatus, MaterialType
)
from services.p2p_service import P2PService
from services.material_service import MaterialService
from services.state_manager import StateManager
from utils.error_utils import NotFoundError, ValidationError, ConflictError, BadRequestError

class TestP2PService:
    def setup_method(self):
        """Set up test environment before each test"""
        # Create a state manager just for testing
        self.state_manager = StateManager()
        
        # Create a material service for testing
        self.material_service = MaterialService(self.state_manager)
        
        # Create test materials
        self.material_service.create_material(
            MaterialCreate(material_number="MAT001", name="Test Material 1")
        )
        self.material_service.create_material(
            MaterialCreate(material_number="MAT002", name="Test Material 2")
        )
        
        # Create the service with our test state manager and material service
        self.p2p_service = P2PService(self.state_manager, self.material_service)
    
    def test_get_requisition(self):
        """Test getting a requisition by document number"""
        # Create a test requisition
        req_data = RequisitionCreate(
            document_number="REQ001",
            description="Test Requisition",
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
        created_req = self.p2p_service.create_requisition(req_data)
        
        # Get the requisition
        req = self.p2p_service.get_requisition("REQ001")
        
        assert req is not None
        assert req.document_number == "REQ001"
        assert req.description == "Test Requisition"
        assert req.requester == "Test User"
        assert len(req.items) == 1
    
    def test_get_requisition_not_found(self):
        """Test getting a non-existent requisition"""
        with pytest.raises(NotFoundError):
            self.p2p_service.get_requisition("NONEXISTENT")
    
    def test_list_requisitions(self):
        """Test listing requisitions with filtering"""
        # Create test requisitions
        self.p2p_service.create_requisition(
            RequisitionCreate(
                document_number="REQ001",
                description="First Requisition",
                requester="User A",
                department="IT",
                items=[
                    RequisitionItem(
                        item_number=1,
                        description="Item 1",
                        quantity=5,
                        unit="EA",
                        price=100
                    )
                ]
            )
        )
        
        self.p2p_service.create_requisition(
            RequisitionCreate(
                document_number="REQ002",
                description="Second Requisition",
                requester="User B",
                department="Finance",
                items=[
                    RequisitionItem(
                        item_number=1,
                        description="Item A",
                        quantity=10,
                        unit="EA",
                        price=50
                    )
                ]
            )
        )
        
        # List all requisitions
        all_reqs = self.p2p_service.list_requisitions()
        assert len(all_reqs) == 2
        
        # Filter by requester
        user_a_reqs = self.p2p_service.list_requisitions(requester="User A")
        assert len(user_a_reqs) == 1
        assert user_a_reqs[0].document_number == "REQ001"
        
        # Filter by department
        finance_reqs = self.p2p_service.list_requisitions(department="Finance")
        assert len(finance_reqs) == 1
        assert finance_reqs[0].document_number == "REQ002"
    
    def test_create_requisition(self):
        """Test creating a requisition"""
        # Create a requisition with minimal data
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
        
        req = self.p2p_service.create_requisition(req_data)
        
        assert req is not None
        assert req.description == "Minimal Requisition"
        assert req.requester == "Test User"
        assert len(req.items) == 1
        assert req.status == DocumentStatus.DRAFT
        
        # Create a requisition with material references
        req_data = RequisitionCreate(
            document_number="REQMAT",
            description="Material Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="MAT001",
                    description="Material Item",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        req = self.p2p_service.create_requisition(req_data)
        
        assert req.document_number == "REQMAT"
        assert req.items[0].material_number == "MAT001"
    
    def test_create_requisition_invalid_material(self):
        """Test creating a requisition with an invalid material reference"""
        # Create a requisition with non-existent material
        req_data = RequisitionCreate(
            description="Invalid Material",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="NONEXISTENT",
                    description="Invalid Material Item",
                    quantity=5,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        with pytest.raises(ValidationError):
            self.p2p_service.create_requisition(req_data)
        
        # Create a material and deprecate it
        mat = self.material_service.create_material(
            MaterialCreate(
                material_number="DEPRECATED",
                name="Deprecated Material"
            )
        )
        self.material_service.deprecate_material("DEPRECATED")
        
        # Try to reference the deprecated material
        req_data = RequisitionCreate(
            description="Deprecated Material",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="DEPRECATED",
                    description="Deprecated Material Item",
                    quantity=5,
                    unit="EA",
                    price=100
                )
            ]
        )
        
        with pytest.raises(ValidationError):
            self.p2p_service.create_requisition(req_data)
    
    def test_update_requisition(self):
        """Test updating a requisition"""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="UPDATE001",
            description="Original Description",
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
        original = self.p2p_service.create_requisition(req_data)
        
        # Update the requisition (still in DRAFT status)
        update_data = RequisitionUpdate(
            description="Updated Description"
        )
        
        updated = self.p2p_service.update_requisition("UPDATE001", update_data)
        
        assert updated.description == "Updated Description"
    
    def test_submit_requisition(self):
        """Test submitting a requisition"""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="SUBMIT001",
            description="Requisition to Submit",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Valid Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        req = self.p2p_service.create_requisition(req_data)
        
        # Submit the requisition
        submitted = self.p2p_service.submit_requisition("SUBMIT001")
        
        assert submitted.status == DocumentStatus.SUBMITTED
    
    def test_approve_requisition(self):
        """Test approving a requisition"""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="APPROVE001",
            description="Requisition to Approve",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Valid Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        req = self.p2p_service.create_requisition(req_data)
        
        # Submit the requisition
        self.p2p_service.submit_requisition("APPROVE001")
        
        # Approve the requisition
        approved = self.p2p_service.approve_requisition("APPROVE001")
        
        assert approved.status == DocumentStatus.APPROVED

    def test_reject_requisition(self):
        """Test rejecting a requisition"""
        # Create a requisition
        req_data = RequisitionCreate(
            document_number="REJECT001",
            description="Requisition to Reject",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Valid Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        req = self.p2p_service.create_requisition(req_data)
        
        # Submit the requisition
        self.p2p_service.submit_requisition("REJECT001")
        
        # Reject the requisition
        rejected = self.p2p_service.reject_requisition("REJECT001", "Budget exceeded")
        
        assert rejected.status == DocumentStatus.REJECTED
        assert "REJECTED: Budget exceeded" in rejected.notes
    
    def test_get_order(self):
        """Test getting an order by document number"""
        # Create a test order
        order_data = OrderCreate(
            document_number="ORD001",
            description="Test Order",
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
        created_order = self.p2p_service.create_order(order_data)
        
        # Get the order
        order = self.p2p_service.get_order("ORD001")
        
        assert order is not None
        assert order.document_number == "ORD001"
        assert order.description == "Test Order"
        assert order.requester == "Test User"
        assert order.vendor == "Test Vendor"
        assert len(order.items) == 1

    def test_list_orders(self):
        """Test listing orders with filtering"""
        # Create test orders
        self.p2p_service.create_order(
            OrderCreate(
                document_number="ORD001",
                description="First Order",
                requester="User A",
                vendor="Vendor X",
                items=[
                    OrderItem(
                        item_number=1,
                        description="Item 1",
                        quantity=5,
                        unit="EA",
                        price=100
                    )
                ]
            )
        )
        
        self.p2p_service.create_order(
            OrderCreate(
                document_number="ORD002",
                description="Second Order",
                requester="User B",
                vendor="Vendor Y",
                items=[
                    OrderItem(
                        item_number=1,
                        description="Item A",
                        quantity=10,
                        unit="EA",
                        price=50
                    )
                ]
            )
        )
        
        # List all orders
        all_orders = self.p2p_service.list_orders()
        assert len(all_orders) == 2
        
        # Filter by vendor
        vendor_x_orders = self.p2p_service.list_orders(vendor="Vendor X")
        assert len(vendor_x_orders) == 1
        assert vendor_x_orders[0].document_number == "ORD001"
    
    def test_create_order(self):
        """Test creating an order"""
        # Create an order with minimal data
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
        
        assert order is not None
        assert order.description == "Minimal Order"
        assert order.requester == "Test User"
        assert order.vendor == "Test Vendor"
        assert len(order.items) == 1
        assert order.status == DocumentStatus.DRAFT
        
        # Create an order with material references
        order_data = OrderCreate(
            document_number="ORDMAT",
            description="Material Order",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    material_number="MAT001",
                    description="Material Item",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        
        order = self.p2p_service.create_order(order_data)
        
        assert order.document_number == "ORDMAT"
        assert order.items[0].material_number == "MAT001"
    
    def test_update_order(self):
        """Test updating an order"""
        # Create an order
        order_data = OrderCreate(
            document_number="UPDATEORDER",
            description="Original Description",
            requester="Test User",
            vendor="Original Vendor",
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
        original = self.p2p_service.create_order(order_data)
        
        # Update the order (still in DRAFT status)
        update_data = OrderUpdate(
            description="Updated Description",
            vendor="Updated Vendor"
        )
        
        updated = self.p2p_service.update_order("UPDATEORDER", update_data)
        
        assert updated.description == "Updated Description"
        assert updated.vendor == "Updated Vendor"
    
    def test_submit_order(self):
        """Test submitting an order"""
        # Create an order
        order_data = OrderCreate(
            document_number="SUBMITORDER",
            description="Order to Submit",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Valid Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        order = self.p2p_service.create_order(order_data)
        
        # Submit the order
        submitted = self.p2p_service.submit_order("SUBMITORDER")
        
        assert submitted.status == DocumentStatus.SUBMITTED
    
    def test_approve_order(self):
        """Test approving an order"""
        # Create an order
        order_data = OrderCreate(
            document_number="APPROVEORDER",
            description="Order to Approve",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Valid Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        order = self.p2p_service.create_order(order_data)
        
        # Submit the order
        self.p2p_service.submit_order("APPROVEORDER")
        
        # Approve the order
        approved = self.p2p_service.approve_order("APPROVEORDER")
        
        assert approved.status == DocumentStatus.APPROVED
    
    def test_create_order_from_requisition(self):
        """Test creating an order from a requisition"""
        # Create and approve a requisition
        req_data = RequisitionCreate(
            document_number="REQTOORDER",
            description="Requisition to Order",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Item 1",
                    quantity=10,
                    unit="EA",
                    price=100
                ),
                RequisitionItem(
                    item_number=2,
                    description="Item 2",
                    quantity=5,
                    unit="EA",
                    price=200
                )
            ]
        )
        req = self.p2p_service.create_requisition(req_data)
        self.p2p_service.submit_requisition("REQTOORDER")
        self.p2p_service.approve_requisition("REQTOORDER")
        
        # Create order from requisition
        order = self.p2p_service.create_order_from_requisition(
            requisition_number="REQTOORDER",
            vendor="Test Vendor",
            payment_terms="Net 30"
        )
        
        assert order is not None
        assert order.vendor == "Test Vendor"
        assert order.payment_terms == "Net 30"
        assert order.requisition_reference == "REQTOORDER"
        assert len(order.items) == 2
        
        # Check that requisition status was updated
        req = self.p2p_service.get_requisition("REQTOORDER")
        assert req.status == DocumentStatus.ORDERED
    
    def test_receive_order(self):
        """Test receiving an order"""
        # Create and approve an order
        order_data = OrderCreate(
            document_number="RECEIVEORDER",
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
        self.p2p_service.submit_order("RECEIVEORDER")
        self.p2p_service.approve_order("RECEIVEORDER")
        
        # Receive the order (all items)
        received = self.p2p_service.receive_order("RECEIVEORDER")
        
        assert received.status == DocumentStatus.RECEIVED
        assert received.items[0].status == DocumentItemStatus.RECEIVED
        assert received.items[0].received_quantity == 10
        assert received.items[1].status == DocumentItemStatus.RECEIVED
        assert received.items[1].received_quantity == 5

    def test_receive_order_partial(self):
        """Test receiving an order partially"""
        # Create and approve an order
        order_data = OrderCreate(
            document_number="PARTIALRECEIVE",
            description="Order to Partially Receive",
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
        self.p2p_service.submit_order("PARTIALRECEIVE")
        self.p2p_service.approve_order("PARTIALRECEIVE")
        
        # Receive the order partially
        received_items = {
            1: 5,  # Receive 5 of Item 1 (out of 10)
            2: 5   # Receive all 5 of Item 2
        }
        received = self.p2p_service.receive_order("PARTIALRECEIVE", received_items)
        
        assert received.status == DocumentStatus.PARTIALLY_RECEIVED
        assert received.items[0].status == DocumentItemStatus.PARTIALLY_RECEIVED
        assert received.items[0].received_quantity == 5
        assert received.items[1].status == DocumentItemStatus.RECEIVED
        assert received.items[1].received_quantity == 5
    
    def test_complete_order(self):
        """Test completing an order"""
        # Create, approve and receive an order
        order_data = OrderCreate(
            document_number="COMPLETEORDER",
            description="Order to Complete",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        order = self.p2p_service.create_order(order_data)
        self.p2p_service.submit_order("COMPLETEORDER")
        self.p2p_service.approve_order("COMPLETEORDER")
        self.p2p_service.receive_order("COMPLETEORDER")
        
        # Complete the order
        completed = self.p2p_service.complete_order("COMPLETEORDER")
        
        assert completed.status == DocumentStatus.COMPLETED
    
    def test_cancel_order(self):
        """Test canceling an order"""
        # Create an order
        order_data = OrderCreate(
            document_number="CANCELORDER",
            description="Order to Cancel",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Item",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        order = self.p2p_service.create_order(order_data)
        
        # Cancel the order
        canceled = self.p2p_service.cancel_order(
            document_number="CANCELORDER",
            reason="No longer needed"
        )
        
        assert canceled.status == DocumentStatus.CANCELED
        assert "CANCELED: No longer needed" in canceled.notes
    
    def test_end_to_end_procurement_flow(self):
        """Test the end-to-end procurement flow"""
        # Create requisition
        req_data = RequisitionCreate(
            document_number="FLOW001",
            description="Flow Test Requisition",
            requester="Test User",
            items=[
                RequisitionItem(
                    item_number=1,
                    material_number="MAT001",
                    description="Test Item 1",
                    quantity=10,
                    unit="EA",
                    price=100
                )
            ]
        )
        req = self.p2p_service.create_requisition(req_data)
        
        # Submit and approve requisition
        self.p2p_service.submit_requisition("FLOW001")
        self.p2p_service.approve_requisition("FLOW001")
        
        # Create order from requisition
        order = self.p2p_service.create_order_from_requisition(
            requisition_number="FLOW001",
            vendor="Test Vendor"
        )
        
        # Submit and approve order
        self.p2p_service.submit_order(order.document_number)
        self.p2p_service.approve_order(order.document_number)
        
        # Receive and complete order
        self.p2p_service.receive_order(order.document_number)
        completed = self.p2p_service.complete_order(order.document_number)
        
        # Verify final state
        assert completed.status == DocumentStatus.COMPLETED
        
        # Verify requisition state
        final_req = self.p2p_service.get_requisition("FLOW001")
        assert final_req.status == DocumentStatus.ORDERED