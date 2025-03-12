# tests/test_service_factory_integration.py
import pytest
from unittest.mock import MagicMock, patch

from models.material import (
    Material, MaterialCreate, MaterialType, MaterialStatus
)
from services.material_service import MaterialService
from services.p2p_service import P2PService
from services.state_manager import StateManager, state_manager
from services import (
    get_material_service, get_p2p_service, register_service, get_service,
    clear_service_registry, get_or_create_service, create_service_instance,
    reset_services
)
from utils.error_utils import NotFoundError, ValidationError

class TestServiceFactoryIntegration:
    """
    Tests for the service factory and registry mechanisms.
    """
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Clear the service registry to ensure a clean state
        clear_service_registry()
    
    def test_get_material_service_default(self):
        """Test getting the default material service singleton"""
        # Get the material service
        material_service = get_material_service()
        
        # Get it again
        material_service2 = get_material_service()
        
        # Verify we got the same instance both times
        assert material_service is material_service2
        
        # Verify it's using the default state manager
        assert material_service.state_manager is state_manager
    
    def test_get_material_service_with_custom_state(self):
        """Test getting a material service with a custom state manager"""
        # Create a custom state manager
        custom_state = StateManager()
        
        # Get a material service with the custom state manager
        material_service = get_material_service(custom_state)
        
        # Verify it's using our custom state manager
        assert material_service.state_manager is custom_state
        
        # Verify it's NOT the same as the default service
        assert material_service is not get_material_service()
    
    def test_get_p2p_service_default(self):
        """Test getting the default P2P service singleton"""
        # Get the P2P service
        p2p_service = get_p2p_service()
        
        # Get it again
        p2p_service2 = get_p2p_service()
        
        # Verify we got the same instance both times
        assert p2p_service is p2p_service2
        
        # Verify it's using the default state manager
        assert p2p_service.state_manager is state_manager
        
        # Verify it's using the default material service
        assert p2p_service.material_service is get_material_service()
    
    def test_get_p2p_service_with_deps(self):
        """Test getting a P2P service with custom dependencies"""
        # Create a custom state manager
        custom_state = StateManager()
        
        # Create a mock material service
        mock_material_service = MagicMock()
        
        # Get a P2P service with custom dependencies
        p2p_service = get_p2p_service(custom_state, mock_material_service)
        
        # Verify it's using our custom dependencies
        assert p2p_service.state_manager is custom_state
        assert p2p_service.material_service is mock_material_service
        
        # Verify it's NOT the same as the default service
        assert p2p_service is not get_p2p_service()
    
    def test_get_p2p_service_with_state_only(self):
        """Test getting a P2P service with just a custom state manager"""
        # Create a custom state manager
        custom_state = StateManager()
        
        # Get a P2P service with just the custom state
        p2p_service = get_p2p_service(custom_state)
        
        # Verify it's using our custom state manager
        assert p2p_service.state_manager is custom_state
        
        # Verify it's NOT using the default material service
        assert p2p_service.material_service is not get_material_service()
        
        # Verify the material service is using the same custom state
        assert p2p_service.material_service.state_manager is custom_state
    
    def test_get_p2p_service_with_material_only(self):
        """Test getting a P2P service with just a custom material service"""
        # Create a mock material service
        mock_material_service = MagicMock()
        
        # Get a P2P service with just the custom material service
        p2p_service = get_p2p_service(material_service_instance=mock_material_service)
        
        # Verify it's using our mock material service
        assert p2p_service.material_service is mock_material_service
        
        # Verify it's using the default state manager
        assert p2p_service.state_manager is state_manager
    
    def test_service_registry_operations(self):
        """Test the full service registry operations"""
        # Clear the registry to start fresh
        clear_service_registry()
        
        # Create mock services
        mock_material = MagicMock()
        mock_p2p = MagicMock()
        
        # Register the services
        register_service("material", mock_material)
        register_service("p2p", mock_p2p)
        
        # Get them back
        retrieved_material = get_service("material")
        retrieved_p2p = get_service("p2p")
        
        # Verify we got the right services
        assert retrieved_material is mock_material
        assert retrieved_p2p is mock_p2p
        
        # Try to get a service that doesn't exist
        with pytest.raises(KeyError):
            get_service("nonexistent")
        
        # Try with a default factory
        default_service = MagicMock()
        retrieved = get_service("nonexistent", lambda: default_service)
        assert retrieved is default_service
        
        # Clear the registry
        clear_service_registry()
        
        # Verify services are gone
        with pytest.raises(KeyError):
            get_service("material")
    
    def test_get_or_create_service(self):
        """Test the get_or_create_service function"""
        # Clear the registry
        clear_service_registry()
        
        # Create a test state manager
        test_state = StateManager()
        
        # Get a service instance
        service1 = get_or_create_service(MaterialService, test_state)
        
        # Verify it's a MaterialService with our state manager
        assert isinstance(service1, MaterialService)
        assert service1.state_manager is test_state
        
        # Get it again
        service2 = get_or_create_service(MaterialService, state_manager)  # Different state manager
        
        # Verify we got the same instance despite different args
        assert service2 is service1
        
        # Verify the state manager wasn't changed
        assert service2.state_manager is test_state
    
    def test_create_service_instance(self):
        """Test the create_service_instance function"""
        # Create a test state manager
        test_state = StateManager()
        
        # Create a service instance
        service1 = create_service_instance(MaterialService, test_state)
        
        # Create another instance
        service2 = create_service_instance(MaterialService, test_state)
        
        # Verify they are different instances
        assert service1 is not service2
        
        # Verify they both use our test state manager
        assert service1.state_manager is test_state
        assert service2.state_manager is test_state
    
    def test_reset_services(self):
        """Test the reset_services function"""
        # Get the default services
        material_service = get_material_service()
        p2p_service = get_p2p_service()
        
        # Add something to the state
        material_service.create_material(
            MaterialCreate(
                material_number="RESET001",
                name="Reset Test Material"
            )
        )
        
        # Verify we can retrieve it
        material = material_service.get_material("RESET001")
        assert material.name == "Reset Test Material"
        
        # Reset the services
        reset_services()
        
        # Get services again
        new_material_service = get_material_service()
        new_p2p_service = get_p2p_service()
        
        # Verify the state was cleared
        with pytest.raises(NotFoundError):
            new_material_service.get_material("RESET001")
        
        # The service instances themselves should be different after reset
        with pytest.raises(KeyError):
            get_service("MaterialService")
    
    def test_cross_service_integration(self):
        """Test integration between services using the factory"""
        # Create a clean state
        test_state = StateManager()
        
        # Get a material service with our test state
        material_service = get_material_service(test_state)
        
        # Create a test material
        material_service.create_material(
            MaterialCreate(
                material_number="INT001",
                name="Integration Test Material"
            )
        )
        
        # Get a P2P service that should automatically use the same state
        p2p_service = get_p2p_service(test_state)
        
        # Verify the P2P service can access the material through its material service
        try:
            p2p_service.material_service.get_material("INT001")
        except NotFoundError:
            pytest.fail("P2P service couldn't access material created by material service")
