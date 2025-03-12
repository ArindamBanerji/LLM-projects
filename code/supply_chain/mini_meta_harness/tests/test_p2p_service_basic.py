# tests/test_p2p_service_basic.py
"""
Basic tests for the P2P service focusing on service initialization, 
data layer interaction, and core functionality.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from models.p2p import (
    P2PDataLayer, DocumentStatus, ProcurementType,
    Requisition, Order
)
from services.p2p_service import P2PService
from services.state_manager import StateManager
from services.material_service import MaterialService
from utils.error_utils import NotFoundError, ValidationError, ConflictError

class TestP2PServiceBasic:
    """Tests for basic P2P service functionality."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create a clean state manager
        self.state_manager = StateManager()
        
        # Create a material service instance
        self.material_service = MaterialService(self.state_manager)
        
        # Create the P2P service with the test state manager
        self.p2p_service = P2PService(self.state_manager, self.material_service)
    
    def test_service_initialization(self):
        """Test proper service initialization with dependencies."""
        # Check state manager dependency
        assert self.p2p_service.state_manager is self.state_manager
        
        # Check material service dependency
        assert self.p2p_service.material_service is self.material_service
        
        # Check data layer initialization
        assert isinstance(self.p2p_service.data_layer, P2PDataLayer)
        assert self.p2p_service.data_layer.state_manager is self.state_manager
    
    def test_service_with_default_deps(self):
        """Test service creation with default dependencies."""
        # Create a service with no explicit dependencies
        service = P2PService()
        
        # Should use the default state manager
        from services.state_manager import state_manager
        assert service.state_manager is state_manager
        
        # Should use the default material service
        from services.material_service import material_service
        assert service.material_service is material_service
    
    def test_get_nonexistent_requisition(self):
        """Test getting a requisition that doesn't exist."""
        # Try to get a non-existent requisition
        with pytest.raises(NotFoundError) as excinfo:
            self.p2p_service.get_requisition("NONEXISTENT")
        
        # Check error details
        assert "not found" in str(excinfo.value.message)
        assert "NONEXISTENT" in str(excinfo.value.message)
        assert excinfo.value.details["document_number"] == "NONEXISTENT"
        assert excinfo.value.details["entity_type"] == "Requisition"
    
    def test_get_nonexistent_order(self):
        """Test getting an order that doesn't exist."""
        # Try to get a non-existent order
        with pytest.raises(NotFoundError) as excinfo:
            self.p2p_service.get_order("NONEXISTENT")
        
        # Check error details
        assert "not found" in str(excinfo.value.message)
        assert "NONEXISTENT" in str(excinfo.value.message)
        assert excinfo.value.details["document_number"] == "NONEXISTENT"
        assert excinfo.value.details["entity_type"] == "Order"
    
    def test_list_empty_requisitions(self):
        """Test listing requisitions when none exist."""
        # List requisitions from empty state
        requisitions = self.p2p_service.list_requisitions()
        
        # Should return empty list
        assert isinstance(requisitions, list)
        assert len(requisitions) == 0
    
    def test_list_empty_orders(self):
        """Test listing orders when none exist."""
        # List orders from empty state
        orders = self.p2p_service.list_orders()
        
        # Should return empty list
        assert isinstance(orders, list)
        assert len(orders) == 0
    
    def test_filter_requisitions_empty(self):
        """Test filtering requisitions with various parameters when none exist."""
        # Filter with various parameters
        filtered = self.p2p_service.list_requisitions(
            status=DocumentStatus.DRAFT,
            requester="Test User",
            department="IT",
            search_term="test",
            date_from=datetime(2025, 1, 1),
            date_to=datetime(2025, 12, 31)
        )
        
        # Should still return empty list
        assert isinstance(filtered, list)
        assert len(filtered) == 0
    
    def test_filter_orders_empty(self):
        """Test filtering orders with various parameters when none exist."""
        # Filter with various parameters
        filtered = self.p2p_service.list_orders(
            status=DocumentStatus.DRAFT,
            vendor="Test Vendor",
            requisition_reference="REQ001",
            search_term="test",
            date_from=datetime(2025, 1, 1),
            date_to=datetime(2025, 12, 31)
        )
        
        # Should still return empty list
        assert isinstance(filtered, list)
        assert len(filtered) == 0
    
    def test_data_layer_initialization(self):
        """Test that the data layer is properly initialized."""
        # Instead of patching P2PDataLayer itself, patch the constructor within P2PService.__init__
        with patch('services.p2p_service.P2PDataLayer') as mock_data_layer_class:
            # Create a new service instance
            service = P2PService(self.state_manager, self.material_service)
            
            # Verify data layer was initialized with state manager
            mock_data_layer_class.assert_called_once_with(self.state_manager)
    
    def test_error_propagation(self):
        """Test that errors from the data layer are properly propagated."""
        # Create a mock data layer that raises an exception
        mock_data_layer = MagicMock()
        mock_data_layer.get_requisition.side_effect = Exception("Data layer error")
        
        # Set the mock data layer on the service
        self.p2p_service.data_layer = mock_data_layer
        
        # Try to get a requisition
        with pytest.raises(Exception) as excinfo:
            self.p2p_service.get_requisition("REQ001")
        
        # Check error message
        assert "Data layer error" in str(excinfo.value)
        
        # Verify data layer was called
        mock_data_layer.get_requisition.assert_called_once_with("REQ001")
