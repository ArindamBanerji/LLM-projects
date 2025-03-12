# services/p2p_service_helpers.py
"""
Helper functions for the P2P service to handle common operations like validation,
status checking, and document state transitions.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from models.p2p import (
    Requisition, RequisitionItem, Order, OrderItem,
    DocumentStatus, DocumentItemStatus, RequisitionUpdate, OrderUpdate
)
from models.material import MaterialStatus
from utils.error_utils import ValidationError, NotFoundError

def validate_requisition_status_transition(
    current_status: DocumentStatus, 
    new_status: DocumentStatus
) -> bool:
    """
    Validate a requisition status transition.
    
    Args:
        current_status: Current status of the requisition
        new_status: Proposed new status
        
    Returns:
        True if the transition is valid, False otherwise
    """
    # Define valid transitions for each status
    valid_transitions = {
        DocumentStatus.DRAFT: [DocumentStatus.SUBMITTED, DocumentStatus.CANCELED],
        DocumentStatus.SUBMITTED: [DocumentStatus.APPROVED, DocumentStatus.REJECTED, DocumentStatus.CANCELED],
        DocumentStatus.APPROVED: [DocumentStatus.ORDERED, DocumentStatus.CANCELED],
        DocumentStatus.REJECTED: [DocumentStatus.DRAFT, DocumentStatus.CANCELED],
        DocumentStatus.ORDERED: [DocumentStatus.CANCELED],
        DocumentStatus.CANCELED: [DocumentStatus.DRAFT]
    }
    
    return new_status in valid_transitions.get(current_status, [])

def validate_order_status_transition(
    current_status: DocumentStatus, 
    new_status: DocumentStatus
) -> bool:
    """
    Validate an order status transition.
    
    Args:
        current_status: Current status of the order
        new_status: Proposed new status
        
    Returns:
        True if the transition is valid, False otherwise
    """
    # Define valid transitions for each status
    valid_transitions = {
        DocumentStatus.DRAFT: [DocumentStatus.SUBMITTED, DocumentStatus.CANCELED],
        DocumentStatus.SUBMITTED: [DocumentStatus.APPROVED, DocumentStatus.REJECTED, DocumentStatus.CANCELED],
        DocumentStatus.APPROVED: [DocumentStatus.RECEIVED, DocumentStatus.PARTIALLY_RECEIVED, DocumentStatus.CANCELED],
        DocumentStatus.REJECTED: [DocumentStatus.DRAFT, DocumentStatus.CANCELED],
        DocumentStatus.RECEIVED: [DocumentStatus.COMPLETED, DocumentStatus.CANCELED],
        DocumentStatus.PARTIALLY_RECEIVED: [DocumentStatus.RECEIVED, DocumentStatus.COMPLETED, DocumentStatus.CANCELED],
        DocumentStatus.COMPLETED: [],  # Terminal state
        DocumentStatus.CANCELED: [DocumentStatus.DRAFT]  # Can reopen to draft
    }
    
    return new_status in valid_transitions.get(current_status, [])

def validate_material_active(
    material_service,
    material_number: str
) -> None:
    """
    Validate that a material exists and is not deprecated.
    
    Args:
        material_service: The material service to use for validation
        material_number: The material number to validate
        
    Raises:
        ValidationError: If the material doesn't exist or is deprecated
    """
    try:
        # Check if material exists and is not deprecated
        material = material_service.get_material(material_number)
        # Only reject DEPRECATED materials, allow INACTIVE
        if material.status == MaterialStatus.DEPRECATED:
            raise ValidationError(
                f"Material {material_number} cannot be used (status: {material.status})"
            )
    except NotFoundError as e:
        # Convert NotFoundError to ValidationError
        raise ValidationError(
            message=f"Invalid material {material_number}: not found",
            details={
                "material_number": material_number,
                "reason": "not_found",
                "original_error": e.details if hasattr(e, 'details') else {}
            }
        )
    except Exception as e:
        # For any other exceptions, provide a clear error message
        raise ValidationError(
            message=f"Error validating material {material_number}: {str(e)}",
            details={
                "material_number": material_number,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )

def validate_requisition_items(items: List[RequisitionItem]) -> None:
    """
    Validate that requisition items are valid.
    
    Args:
        items: The items to validate
        
    Raises:
        ValidationError: If any item is invalid
    """
    if not items:
        raise ValidationError("Cannot process requisition with no items")
    
    for item in items:
        if not item.description or item.quantity <= 0:
            raise ValidationError(f"Item {item.item_number} has invalid data")

def validate_order_items(items: List[OrderItem]) -> None:
    """
    Validate that order items are valid.
    
    Args:
        items: The items to validate
        
    Raises:
        ValidationError: If any item is invalid
    """
    if not items:
        raise ValidationError("Cannot process order with no items")
    
    for item in items:
        if not item.description or item.quantity <= 0:
            raise ValidationError(f"Item {item.item_number} has invalid data")

def validate_vendor(vendor: str) -> None:
    """
    Validate that a vendor is specified.
    
    Args:
        vendor: The vendor to validate
        
    Raises:
        ValidationError: If the vendor is not specified
    """
    if not vendor or len(vendor.strip()) == 0:
        raise ValidationError("Vendor is required")

def prepare_received_items(
    order: Order, 
    received_items: Optional[Dict[int, float]] = None
) -> List[OrderItem]:
    """
    Prepare updated order items based on received quantities.
    
    Args:
        order: The order being received
        received_items: Dictionary mapping item numbers to received quantities.
                        If None, receive all items in full.
    
    Returns:
        Updated list of order items with received quantities
        
    Raises:
        ValidationError: If any received quantity is invalid
    """
    updated_items = []
    
    for item in order.items:
        received_qty = 0
        
        if received_items:
            # If specific items provided, use those
            received_qty = received_items.get(item.item_number, 0)
        else:
            # Otherwise, receive full quantity
            received_qty = item.quantity
        
        # Validate received quantity
        if received_qty < 0:
            raise ValidationError(f"Received quantity cannot be negative for item {item.item_number}")
        
        if received_qty > item.quantity:
            raise ValidationError(
                f"Received quantity ({received_qty}) cannot exceed ordered quantity "
                f"({item.quantity}) for item {item.item_number}"
            )
        
        # Create a copy of the item data and update the received_quantity
        # Ensure we're working with the proper OrderItem object, not a dict
        if isinstance(item, dict):
            # Convert dict to OrderItem if needed
            item_data = item.copy()
            item_data['received_quantity'] = item_data.get('received_quantity', 0) + received_qty
            
            # Update status based on received quantity
            if item_data['received_quantity'] == item_data['quantity']:
                item_data['status'] = DocumentItemStatus.RECEIVED.value
            elif item_data['received_quantity'] > 0:
                item_data['status'] = DocumentItemStatus.PARTIALLY_RECEIVED.value
                
            # Create OrderItem from dict
            new_item = OrderItem(**item_data)
        else:
            # We have an OrderItem object
            # Create a copy of the item data
            item_data = item.model_dump()
            # Update received quantity
            item_data['received_quantity'] = item.received_quantity + received_qty
            
            # Update status based on received quantity
            if item_data['received_quantity'] == item_data['quantity']:
                item_data['status'] = DocumentItemStatus.RECEIVED
            elif item_data['received_quantity'] > 0:
                item_data['status'] = DocumentItemStatus.PARTIALLY_RECEIVED
                
            # Create a new OrderItem with the updated data
            new_item = OrderItem(**item_data)
        
        updated_items.append(new_item)
    
    return updated_items

def determine_order_status_from_items(items: List[OrderItem]) -> DocumentStatus:
    """
    Determine the order status based on item statuses.
    
    Args:
        items: The order items to check
        
    Returns:
        The appropriate order status
    """
    # Default to RECEIVED (all items received)
    new_status = DocumentStatus.RECEIVED
    
    # Check if any items are not fully received
    for item in items:
        if isinstance(item, dict):
            # Handle dict item
            if item.get('status') != DocumentItemStatus.RECEIVED.value:
                new_status = DocumentStatus.PARTIALLY_RECEIVED
                break
        else:
            # Handle OrderItem object
            if item.status != DocumentItemStatus.RECEIVED:
                new_status = DocumentStatus.PARTIALLY_RECEIVED
                break
    
    return new_status

def append_note(current_notes: Optional[str], new_note: str) -> str:
    """
    Append a note to existing notes.
    
    Args:
        current_notes: Existing notes, if any
        new_note: New note to append
        
    Returns:
        Updated notes string
    """
    current = current_notes or ""
    if current and not current.endswith("\n"):
        current += "\n"
    return f"{current}{new_note}".strip()
