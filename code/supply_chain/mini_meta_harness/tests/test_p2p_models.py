# tests/test_p2p_models.py
import pytest
from datetime import datetime, date
from pydantic import ValidationError as PydanticValidationError
from models.p2p import (
    DocumentStatus, ProcurementType, DocumentItemStatus,
    DocumentItem, RequisitionItem, OrderItem,
    RequisitionCreate, OrderCreate,
    RequisitionUpdate, OrderUpdate,
    Requisition, Order, P2PDataLayer
)
from models.common import EntityCollection
from services.state_manager import StateManager

class TestDocumentItemModels:
    def test_requisition_item_create(self):
        """Test creating a requisition item"""
        req_item = RequisitionItem(
            item_number=1,
            description="Test Item",
            quantity=10,
            unit="EA",
            price=100.0
        )
        
        assert req_item.item_number == 1
        assert req_item.description == "Test Item"
        assert req_item.quantity == 10
        assert req_item.unit == "EA"
        assert req_item.price == 100.0
        assert req_item.currency == "USD"
        assert req_item.status == DocumentItemStatus.OPEN
        assert req_item.assigned_to_order is None
        
        # Test value property
        assert req_item.value == 1000.0
    
    def test_order_item_create(self):
        """Test creating an order item"""
        order_item = OrderItem(
            item_number=1,
            description="Test Item",
            quantity=10,
            unit="EA",
            price=100.0,
            requisition_reference="PR123",
            requisition_item=1
        )
        
        assert order_item.item_number == 1
        assert order_item.description == "Test Item"
        assert order_item.quantity == 10
        assert order_item.unit == "EA"
        assert order_item.price == 100.0
        assert order_item.currency == "USD"
        assert order_item.status == DocumentItemStatus.OPEN
        assert order_item.requisition_reference == "PR123"
        assert order_item.requisition_item == 1
        assert order_item.received_quantity == 0
    
    def test_order_item_received_quantity_validation(self):
        """Test validation of received quantity in order item"""
        # Valid: received quantity <= ordered quantity
        valid_item = OrderItem(
            item_number=1,
            description="Test Item",
            quantity=10,
            unit="EA",
            price=100.0,
            received_quantity=5.0
        )
        assert valid_item.received_quantity == 5.0
        
        # Invalid: received quantity > ordered quantity
        with pytest.raises(ValueError):
            OrderItem(
                item_number=1,
                description="Test Item",
                quantity=10,
                unit="EA",
                price=100.0,
                received_quantity=15.0
            )

class TestDocumentCreateModels:
    def test_requisition_create_minimal(self):
        """Test creating a requisition with minimal fields"""
        items = [
            RequisitionItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            )
        ]
        
        req_create = RequisitionCreate(
            description="Test Requisition",
            requester="Test User",
            items=items
        )
        
        assert req_create.description == "Test Requisition"
        assert req_create.requester == "Test User"
        assert req_create.document_number is None
        assert req_create.type == ProcurementType.STANDARD
        assert req_create.urgent is False
        assert len(req_create.items) == 1
    
    def test_requisition_create_full(self):
        """Test creating a requisition with all fields"""
        items = [
            RequisitionItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            ),
            RequisitionItem(
                item_number=2,
                description="Item 2",
                quantity=5,
                unit="KG",
                price=50.0
            )
        ]
        
        req_create = RequisitionCreate(
            document_number="PR123",
            description="Test Requisition",
            requester="Test User",
            department="IT",
            type=ProcurementType.SERVICE,
            notes="Test notes",
            urgent=True,
            items=items
        )
        
        assert req_create.document_number == "PR123"
        assert req_create.description == "Test Requisition"
        assert req_create.requester == "Test User"
        assert req_create.department == "IT"
        assert req_create.type == ProcurementType.SERVICE
        assert req_create.notes == "Test notes"
        assert req_create.urgent is True
        assert len(req_create.items) == 2
    
    def test_order_create(self):
        """Test creating an order"""
        items = [
            OrderItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            )
        ]
        
        order_create = OrderCreate(
            description="Test Order",
            requester="Test User",
            vendor="Test Vendor",
            items=items
        )
        
        assert order_create.description == "Test Order"
        assert order_create.requester == "Test User"
        assert order_create.vendor == "Test Vendor"
        assert order_create.document_number is None
        assert order_create.type == ProcurementType.STANDARD
        assert order_create.urgent is False
        assert len(order_create.items) == 1

class TestDocumentModels:
    def test_requisition_model(self):
        """Test the Requisition model"""
        items = [
            RequisitionItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            ),
            RequisitionItem(
                item_number=2,
                description="Item 2",
                quantity=5,
                unit="KG",
                price=50.0
            )
        ]
        
        requisition = Requisition(
            id="PR123",
            document_number="PR123",
            description="Test Requisition",
            requester="Test User",
            department="IT",
            items=items,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert requisition.id == "PR123"
        assert requisition.document_number == "PR123"
        assert requisition.description == "Test Requisition"
        assert requisition.requester == "Test User"
        assert requisition.department == "IT"
        assert requisition.status == DocumentStatus.DRAFT
        assert len(requisition.items) == 2
        
        # Test total_value property
        assert requisition.total_value == 1250.0  # 10*100 + 5*50
    
    def test_order_model(self):
        """Test the Order model"""
        items = [
            OrderItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            )
        ]
        
        order = Order(
            id="PO123",
            document_number="PO123",
            description="Test Order",
            requester="Test User",
            vendor="Test Vendor",
            items=items,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert order.id == "PO123"
        assert order.document_number == "PO123"
        assert order.description == "Test Order"
        assert order.requester == "Test User"
        assert order.vendor == "Test Vendor"
        assert order.status == DocumentStatus.DRAFT
        assert len(order.items) == 1
        assert order.total_value == 1000.0

class TestP2PDataLayer:
    def setup_method(self):
        """Set up a fresh state manager and data layer for each test"""
        self.state_manager = StateManager()
        self.data_layer = P2PDataLayer(self.state_manager)
    
    def test_create_requisition(self):
        """Test creating a requisition through the data layer"""
        items = [
            RequisitionItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            )
        ]
        
        create_data = RequisitionCreate(
            document_number="PR001",
            description="Test Requisition",
            requester="Test User",
            items=items
        )
        
        requisition = self.data_layer.create_requisition(create_data)
        
        assert requisition.document_number == "PR001"
        assert requisition.description == "Test Requisition"
        assert requisition.requester == "Test User"
        assert len(requisition.items) == 1
        
        # Check it was added to state
        collection = self.state_manager.get_model(self.data_layer.requisitions_key, EntityCollection)
        assert collection is not None
        assert collection.count() == 1
        assert collection.get("PR001") is not None
    
    def test_create_order(self):
        """Test creating an order through the data layer"""
        items = [
            OrderItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            )
        ]
        
        create_data = OrderCreate(
            document_number="PO001",
            description="Test Order",
            requester="Test User",
            vendor="Test Vendor",
            items=items
        )
        
        order = self.data_layer.create_order(create_data)
        
        assert order.document_number == "PO001"
        assert order.description == "Test Order"
        assert order.requester == "Test User"
        assert order.vendor == "Test Vendor"
        assert len(order.items) == 1
        
        # Check it was added to state
        collection = self.state_manager.get_model(self.data_layer.orders_key, EntityCollection)
        assert collection is not None
        assert collection.count() == 1
        assert collection.get("PO001") is not None
    
    def test_get_requisition(self):
        """Test getting a requisition by ID"""
        # Create a requisition first
        items = [
            RequisitionItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            )
        ]
        
        create_data = RequisitionCreate(
            document_number="PR001",
            description="Test Requisition",
            requester="Test User",
            items=items
        )
        
        self.data_layer.create_requisition(create_data)
        
        # Get it back
        requisition = self.data_layer.get_requisition("PR001")
        
        assert requisition is not None
        assert requisition.document_number == "PR001"
        assert requisition.description == "Test Requisition"
        assert len(requisition.items) == 1
    
    def test_status_transitions(self):
        """Test document status transitions"""
        # Create a requisition
        items = [
            RequisitionItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            )
        ]
        
        create_data = RequisitionCreate(
            document_number="PR001",
            description="Test Requisition",
            requester="Test User",
            items=items
        )
        
        requisition = self.data_layer.create_requisition(create_data)
        assert requisition.status == DocumentStatus.DRAFT
        
        # Submit the requisition
        update_data = RequisitionUpdate(status=DocumentStatus.SUBMITTED)
        updated_req = self.data_layer.update_requisition("PR001", update_data)
        assert updated_req.status == DocumentStatus.SUBMITTED
        
        # Try to skip to ORDERED (should fail)
        with pytest.raises(Exception):
            update_data = RequisitionUpdate(status=DocumentStatus.ORDERED)
            self.data_layer.update_requisition("PR001", update_data)
        
        # Approve properly
        update_data = RequisitionUpdate(status=DocumentStatus.APPROVED)
        updated_req = self.data_layer.update_requisition("PR001", update_data)
        assert updated_req.status == DocumentStatus.APPROVED
    
    def test_create_order_from_requisition(self):
        """Test creating an order from a requisition"""
        # Create a requisition first
        items = [
            RequisitionItem(
                item_number=1,
                description="Item 1",
                quantity=10,
                unit="EA",
                price=100.0
            )
        ]
        
        req_data = RequisitionCreate(
            document_number="PR001",
            description="Test Requisition",
            requester="Test User",
            items=items
        )
        
        requisition = self.data_layer.create_requisition(req_data)
        
        # Approve the requisition
        update_data = RequisitionUpdate(status=DocumentStatus.SUBMITTED)
        self.data_layer.update_requisition("PR001", update_data)
        update_data = RequisitionUpdate(status=DocumentStatus.APPROVED)
        self.data_layer.update_requisition("PR001", update_data)
        
        # Create order from requisition
        order = self.data_layer.create_order_from_requisition(
            requisition_number="PR001",
            vendor="Test Vendor",
            payment_terms="Net 30"
        )
        
        # Check order
        assert order.document_number is not None
        assert order.document_number.startswith("PO")
        assert order.requisition_reference == "PR001"
        assert order.vendor == "Test Vendor"
        assert order.payment_terms == "Net 30"
        assert len(order.items) == 1
        assert order.items[0].requisition_reference == "PR001"
        assert order.items[0].requisition_item == 1
        assert order.items[0].quantity == 10
        assert order.items[0].price == 100.0
        
        # Check requisition status updated
        requisition = self.data_layer.get_requisition("PR001")
        assert requisition.status == DocumentStatus.ORDERED
