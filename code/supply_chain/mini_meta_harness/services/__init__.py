# services/__init__.py
"""
Service factory module for the SAP Test Harness.

This module provides factory functions to obtain service instances,
enabling dependency injection for better testability.
"""

from services.state_manager import StateManager


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
        return MaterialService(state_manager_instance)
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
    if state_manager_instance or material_service_instance:
        return P2PService(state_manager_instance, material_service_instance)
    return p2p_service


def reset_services():
    """
    Reset all service singletons to their initial state.
    This is primarily useful for testing.
    
    Note: This should not be used in production code.
    """
    from services.material_service import MaterialService
    from services.p2p_service import P2PService
    from services.state_manager import state_manager
    
    # Reset the state manager
    state_manager.clear()
    
    # Re-initialize the services
    # This approach maintains the singleton instances but resets their state
    from services.material_service import material_service
    from services.p2p_service import p2p_service
    
    # No need to recreate the services as they'll automatically
    # use the cleared state manager