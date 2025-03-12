# services/__init__.py
"""
Service factory module for the SAP Test Harness.

This module provides factory functions to obtain service instances,
enabling dependency injection for better testability.
"""

from typing import Optional, Dict, Any, Type, TypeVar
from services.state_manager import StateManager, state_manager

# Type variable for services
T = TypeVar('T')

# Service registry to keep track of service instances
_service_instances: Dict[str, Any] = {}

def get_material_service(state_manager_instance=None):
    """
    Factory function for Material Service.
    
    Args:
        state_manager_instance: Optional state manager instance for dependency injection
        
    Returns:
        An instance of the MaterialService class
    """
    from services.material_service import material_service, MaterialService
    
    if state_manager_instance:
        # Create a new instance with the provided state manager
        return MaterialService(state_manager_instance)
    
    # Return the singleton instance
    return material_service


def get_p2p_service(state_manager_instance=None, material_service_instance=None):
    """
    Factory function for P2P Service.
    
    Args:
        state_manager_instance: Optional state manager instance for dependency injection
        material_service_instance: Optional material service instance for dependency injection
        
    Returns:
        An instance of the P2PService class
    """
    from services.p2p_service import p2p_service, P2PService
    
    if state_manager_instance is not None or material_service_instance is not None:
        # If state manager is provided but material service isn't
        if state_manager_instance is not None and material_service_instance is None:
            # Create a material service with the same state manager
            material_service_instance = get_material_service(state_manager_instance)
        
        # If only material service is provided, use the default state manager
        sm = state_manager_instance or state_manager
        
        # Create a new instance with the provided dependencies
        return P2PService(sm, material_service_instance)
    
    # Return the singleton instance
    return p2p_service


def get_monitor_service(state_manager_instance=None):
    """
    Factory function for Monitor Service.
    
    Args:
        state_manager_instance: Optional state manager instance for dependency injection
        
    Returns:
        An instance of the MonitorService class
    """
    from services.monitor_service import monitor_service, MonitorService
    
    if state_manager_instance:
        # Create a new instance with the provided state manager
        return MonitorService(state_manager_instance)
    
    # Return the singleton instance
    return monitor_service


def register_service(service_name: str, service_instance: Any) -> None:
    """
    Register a service instance in the registry.
    
    This is useful for testing where you want to replace a service with a mock.
    
    Args:
        service_name: The name of the service (e.g., 'material', 'p2p')
        service_instance: The service instance to register
    """
    _service_instances[service_name] = service_instance


def get_service(service_name: str, default_factory=None):
    """
    Get a service instance from the registry.
    
    Args:
        service_name: The name of the service (e.g., 'material', 'p2p')
        default_factory: Optional function to call if the service is not in the registry
        
    Returns:
        The service instance
        
    Raises:
        KeyError: If the service is not in the registry and no default factory is provided
    """
    if service_name in _service_instances:
        return _service_instances[service_name]
    
    if default_factory:
        return default_factory()
    
    raise KeyError(f"Service '{service_name}' not found in registry")


def get_or_create_service(service_class: Type[T], *args, **kwargs) -> T:
    """
    Get a service instance by class, or create one if it doesn't exist.
    
    This is a more generic version of the specific factory functions.
    
    Args:
        service_class: The service class to instantiate
        *args: Positional arguments to pass to the service constructor
        **kwargs: Keyword arguments to pass to the service constructor
        
    Returns:
        An instance of the specified service class
    """
    service_name = service_class.__name__
    
    if service_name in _service_instances:
        return _service_instances[service_name]
    
    # Create a new instance
    instance = service_class(*args, **kwargs)
    
    # Register the instance
    _service_instances[service_name] = instance
    
    return instance


def create_service_instance(service_class: Type[T], *args, **kwargs) -> T:
    """
    Create a new service instance without registering it.
    
    This is useful for tests where you need a clean instance each time.
    
    Args:
        service_class: The service class to instantiate
        *args: Positional arguments to pass to the service constructor
        **kwargs: Keyword arguments to pass to the service constructor
        
    Returns:
        A new instance of the specified service class
    """
    return service_class(*args, **kwargs)


def clear_service_registry() -> None:
    """
    Clear the service registry.
    
    This is useful for testing to ensure a clean state between tests.
    """
    _service_instances.clear()


def reset_services() -> None:
    """
    Reset all service singletons to their initial state.
    This is primarily useful for testing.
    
    Note: This should not be used in production code.
    """
    from services.material_service import MaterialService
    from services.p2p_service import P2PService
    from services.monitor_service import MonitorService
    
    # Reset the state manager
    state_manager.clear()
    
    # Clear the service registry
    clear_service_registry()
