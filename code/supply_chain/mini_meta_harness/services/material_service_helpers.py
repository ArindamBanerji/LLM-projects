# services/material_service_helpers.py
"""
Helper module for material-related operations in the Material service.
Contains implementation details for material processing logic.
"""
import uuid
from typing import Optional, Dict, Any, List
from models.material import MaterialType, MaterialStatus
from utils.error_utils import ValidationError

def generate_material_number(material_type: MaterialType) -> str:
    """
    Generate a unique material number based on material type.
    
    Args:
        material_type: The material type
        
    Returns:
        A unique material number
    """
    # Generate a unique ID based on UUID
    unique_id = uuid.uuid4().hex[:12].upper()
    
    # Prefix based on material type
    prefix = "MAT"  # Default prefix
    if material_type == MaterialType.RAW:
        prefix = "RAW"
    elif material_type == MaterialType.SEMIFINISHED:
        prefix = "SEMI"
    elif material_type == MaterialType.FINISHED:
        prefix = "FIN"
    elif material_type == MaterialType.SERVICE:
        prefix = "SRV"
    elif material_type == MaterialType.TRADING:
        prefix = "TRD"
    
    return f"{prefix}{unique_id}"

def validate_material_status_transition(
    current_status: MaterialStatus,
    new_status: MaterialStatus
) -> bool:
    """
    Validate if a material status transition is valid.
    
    Args:
        current_status: Current material status
        new_status: New material status
        
    Returns:
        True if the transition is valid, False otherwise
    """
    # Define valid transitions
    valid_transitions = {
        MaterialStatus.ACTIVE: [MaterialStatus.INACTIVE, MaterialStatus.DEPRECATED],
        MaterialStatus.INACTIVE: [MaterialStatus.ACTIVE, MaterialStatus.DEPRECATED],
        MaterialStatus.DEPRECATED: [],  # Cannot transition from deprecated
        MaterialStatus.PLANNED: [MaterialStatus.ACTIVE, MaterialStatus.INACTIVE, MaterialStatus.DEPRECATED]
    }
    
    return new_status in valid_transitions.get(current_status, [])

def validate_material_can_be_deleted(material_status: MaterialStatus) -> bool:
    """
    Determine if a material can be deleted based on its status.
    
    Args:
        material_status: Current status of the material
        
    Returns:
        True if the material can be deleted, False otherwise
    """
    # Only inactive or deprecated materials can be deleted
    return material_status != MaterialStatus.ACTIVE

def validate_material_can_be_deprecated(material_status: MaterialStatus) -> bool:
    """
    Determine if a material can be deprecated.
    
    Args:
        material_status: Current status of the material
        
    Returns:
        True if the material can be deprecated, False otherwise
    """
    # Cannot deprecate an already deprecated material
    return material_status != MaterialStatus.DEPRECATED

def filter_materials(materials: List[Dict[str, Any]], **filters) -> List[Dict[str, Any]]:
    """
    Filter a list of materials based on given criteria.
    
    Args:
        materials: List of material objects
        **filters: Keyword arguments for filtering
        
    Returns:
        Filtered list of materials
    """
    results = []
    
    for material in materials:
        matches = True
        for field, value in filters.items():
            # Handle list filters (e.g., status=[ACTIVE, INACTIVE])
            if isinstance(value, list):
                if not hasattr(material, field) or getattr(material, field) not in value:
                    matches = False
                    break
            # Handle scalar filters
            elif not hasattr(material, field) or getattr(material, field) != value:
                matches = False
                break
        
        if matches:
            results.append(material)
    
    return results
