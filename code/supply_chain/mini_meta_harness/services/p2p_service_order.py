# services/p2p_service_order.py
"""
Helper module for order-related operations in the P2P service.
Contains implementation details for order processing logic.
"""
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from models.p2p import (
    Order, OrderCreate, OrderUpdate, OrderItem,
    DocumentStatus, DocumentItemStatus
)
from utils.error_utils import ValidationError, NotFoundError
from services.p2p_service_helpers import (
    validate_order_status_transition,
    validate_order_items,
    validate_vendor,
    prepare_received_items,
    determine_order_status_from_items,
    append_note
)

def validate_order_for_submission(order: Order) -> None:
    """
    Validate that an order can be submitted.
    
    Args:
        order: The order to validate
        
    Raises:
        ValidationError: If the order cannot be submitted
    """
    if order.status != DocumentStatus.DRAFT:
        raise ValidationError(
            f"Cannot submit order with status {order.status}. Must be DRAFT."
        )
    
    validate_vendor(order.vendor)
    validate_order_items(order.items)

def validate_order_for_approval(order: Order) -> None:
    """
    Validate that an order can be approved.
    
    Args:
        order: The order to validate
        
    Raises:
        ValidationError: If the order cannot be approved
    """
    if order.status != DocumentStatus.SUBMITTED:
        raise ValidationError(
            f"Cannot approve order with status {order.status}. Must be SUBMITTED."
        )

def validate_order_for_receipt(order: Order) -> None:
    """
    Validate that an order can be received.
    
    Args:
        order: The order to validate
        
    Raises:
        ValidationError: If the order cannot be received
    """
    if order.status != DocumentStatus.APPROVED:
        raise ValidationError(
            f"Cannot receive order with status {order.status}. Must be APPROVED."
        )

def validate_order_for_completion(order: Order) -> None:
    """
    Validate that an order can be completed.
    
    Args:
        order: The order to validate
        
    Raises:
        ValidationError: If the order cannot be completed
    """
    if order.status not in [DocumentStatus.RECEIVED, DocumentStatus.PARTIALLY_RECEIVED]:
        raise ValidationError(
            f"Cannot complete order with status {order.status}. "
            f"Must be RECEIVED or PARTIALLY_RECEIVED."
        )

def validate_order_for_cancellation(order: Order) -> None:
    """
    Validate that an order can be canceled.
    
    Args:
        order: The order to validate
        
    Raises:
        ValidationError: If the order cannot be canceled
    """
    if order.status in [DocumentStatus.COMPLETED, DocumentStatus.CANCELED]:
        raise ValidationError(
            f"Cannot cancel order with status {order.status}."
        )

def validate_order_for_deletion(order: Order) -> None:
    """
    Validate that an order can be deleted.
    
    Args:
        order: The order to validate
        
    Raises:
        ValidationError: If the order cannot be deleted
    """
    if order.status != DocumentStatus.DRAFT:
        raise ValidationError(
            f"Cannot delete order with status {order.status}. "
            f"Only DRAFT orders can be deleted."
        )

def prepare_order_update_with_received_items(
    order: Order, 
    received_items: Dict[int, float] = None
) -> OrderUpdate:
    """
    Prepare an order update with received items.
    
    Args:
        order: The order being received
        received_items: Dictionary mapping item numbers to received quantities
                        If None, receive all items in full
                        
    Returns:
        OrderUpdate object with updated items and status
    """
    # Prepare updated items with received quantities
    updated_items = prepare_received_items(order, received_items)
    
    # Determine new order status based on items
    new_status = determine_order_status_from_items(updated_items)
    
    # Create order update data
    return OrderUpdate(
        items=updated_items,
        status=new_status
    )

def filter_orders(
    orders: List[Order],
    status: Optional[Union[DocumentStatus, List[DocumentStatus]]] = None,
    vendor: Optional[str] = None,
    requisition_reference: Optional[str] = None,
    search_term: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[Order]:
    """
    Filter orders based on criteria.
    
    Args:
        orders: List of orders to filter
        status: Optional status(es) to filter by
        vendor: Optional vendor to filter by
        requisition_reference: Optional requisition reference to filter by
        search_term: Optional search term to filter by
        date_from: Optional start date for creation date range
        date_to: Optional end date for creation date range
        
    Returns:
        Filtered list of orders
    """
    filtered_orders = orders
    
    # Filter by status if provided
    if status:
        if isinstance(status, list):
            filtered_orders = [o for o in filtered_orders if o.status in status]
        else:
            filtered_orders = [o for o in filtered_orders if o.status == status]
    
    # Filter by vendor if provided
    if vendor:
        filtered_orders = [o for o in filtered_orders if o.vendor == vendor]
    
    # Filter by requisition reference if provided
    if requisition_reference:
        filtered_orders = [o for o in filtered_orders if o.requisition_reference == requisition_reference]
    
    # Filter by search term if provided
    if search_term:
        search_term = search_term.lower()
        result = []
        for order in filtered_orders:
            if (
                search_term in order.description.lower() or
                search_term in order.document_number.lower() or
                (order.vendor and search_term in order.vendor.lower()) or
                any(search_term in item.description.lower() for item in order.items)
            ):
                result.append(order)
        filtered_orders = result
    
    # Filter by date range if provided
    if date_from:
        filtered_orders = [o for o in filtered_orders if o.created_at >= date_from]
    if date_to:
        filtered_orders = [o for o in filtered_orders if o.created_at <= date_to]
    
    return filtered_orders
