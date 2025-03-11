# models/p2p_helper.py
"""
Helper module for P2P (Procure-to-Pay) functionality.
Provides utility functions and common operations used by the main P2P models.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum

# Status validation mappings
# These define valid status transitions for different document types
REQUISITION_STATUS_TRANSITIONS = {
    "DRAFT": ["SUBMITTED", "CANCELED"],
    "SUBMITTED": ["APPROVED", "REJECTED", "CANCELED"],
    "APPROVED": ["ORDERED", "CANCELED"],
    "REJECTED": ["DRAFT", "CANCELED"],
    "ORDERED": ["CANCELED"],
    "CANCELED": ["DRAFT"]
}

ORDER_STATUS_TRANSITIONS = {
    "DRAFT": ["SUBMITTED", "CANCELED"],
    "SUBMITTED": ["APPROVED", "REJECTED", "CANCELED"],
    "APPROVED": ["RECEIVED", "PARTIALLY_RECEIVED", "CANCELED"],
    "REJECTED": ["DRAFT", "CANCELED"],
    "RECEIVED": ["COMPLETED", "CANCELED"],
    "PARTIALLY_RECEIVED": ["RECEIVED", "COMPLETED", "CANCELED"],
    "COMPLETED": [],  # Terminal state
    "CANCELED": ["DRAFT"]  # Can reopen to draft
}

def validate_status_transition(current_status: str, new_status: str, transitions_map: Dict[str, List[str]]) -> bool:
    """
    Validate if a status transition is valid based on a transitions map.
    
    Args:
        current_status: Current status
        new_status: Proposed new status
        transitions_map: Map of valid transitions for each status
        
    Returns:
        True if the transition is valid, False otherwise
    """
    if current_status not in transitions_map:
        return False
    
    return new_status in transitions_map.get(current_status, [])

def generate_document_number(prefix: str, length: int = 8) -> str:
    """
    Generate a unique document number with the given prefix.
    
    Args:
        prefix: Prefix for the document number (e.g., "PR" for purchase requisition)
        length: Length of the random part (default: 8 characters)
        
    Returns:
        A unique document number with format {prefix}{random_hex}
    """
    unique_id = uuid.uuid4().hex[:length].upper()
    return f"{prefix}{unique_id}"

def calculate_total_value(items: List[Any]) -> float:
    """
    Calculate the total value of a list of document items.
    
    Args:
        items: List of items with a 'value' property or method
        
    Returns:
        Total value of all items
    """
    return sum(getattr(item, 'value', 0) for item in items)

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

def determine_item_status_from_received_quantity(item_quantity: float, received_quantity: float) -> str:
    """
    Determine the status of an item based on received quantity.
    
    Args:
        item_quantity: The ordered quantity
        received_quantity: The received quantity
        
    Returns:
        The appropriate item status
    """
    if received_quantity == 0:
        return "OPEN"
    elif received_quantity < item_quantity:
        return "PARTIALLY_RECEIVED"
    else:
        return "RECEIVED"

def determine_document_status_from_items(items: List[Any]) -> str:
    """
    Determine the status of a document based on its items.
    
    Args:
        items: List of document items
        
    Returns:
        The appropriate document status
    """
    # If all items are received, document is RECEIVED
    if all(getattr(item, 'status', None) == "RECEIVED" for item in items):
        return "RECEIVED"
    # If any items are partially received, document is PARTIALLY_RECEIVED
    elif any(getattr(item, 'status', None) in ["PARTIALLY_RECEIVED", "RECEIVED"] for item in items):
        return "PARTIALLY_RECEIVED"
    # Otherwise maintain current status
    return "OPEN"

def validate_document_number(document_number: str) -> bool:
    """
    Validate the format of a document number.
    
    Args:
        document_number: Document number to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not document_number:
        return False
    
    # Document number should be alphanumeric
    return document_number.isalnum()
