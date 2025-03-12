# services/p2p_service_requisition.py
"""
Helper module for requisition-related operations in the P2P service.
Contains implementation details for requisition processing logic.
"""
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from models.p2p import (
    Requisition, RequisitionCreate, RequisitionUpdate, RequisitionItem,
    DocumentStatus, DocumentItemStatus
)
from utils.error_utils import ValidationError, NotFoundError
from services.p2p_service_helpers import (
    validate_requisition_status_transition,
    validate_requisition_items,
    append_note
)

def validate_requisition_for_submission(requisition: Requisition) -> None:
    """
    Validate that a requisition can be submitted.
    
    Args:
        requisition: The requisition to validate
        
    Raises:
        ValidationError: If the requisition cannot be submitted
    """
    if requisition.status != DocumentStatus.DRAFT:
        raise ValidationError(
            message=f"Cannot submit requisition with status {requisition.status}. Must be DRAFT.",
            details={
                "document_number": requisition.document_number,
                "current_status": requisition.status.value,
                "required_status": DocumentStatus.DRAFT.value,
                "operation": "submit",
                "entity_type": "Requisition"
            }
        )
    
    validate_requisition_items(requisition.items)

def validate_requisition_for_approval(requisition: Requisition) -> None:
    """
    Validate that a requisition can be approved.
    
    Args:
        requisition: The requisition to validate
        
    Raises:
        ValidationError: If the requisition cannot be approved
    """
    if requisition.status != DocumentStatus.SUBMITTED:
        raise ValidationError(
            message=f"Cannot approve requisition with status {requisition.status}. Must be SUBMITTED.",
            details={
                "document_number": requisition.document_number,
                "current_status": requisition.status.value,
                "required_status": DocumentStatus.SUBMITTED.value,
                "operation": "approve",
                "entity_type": "Requisition"
            }
        )

def validate_requisition_for_rejection(requisition: Requisition, reason: str) -> None:
    """
    Validate that a requisition can be rejected.
    
    Args:
        requisition: The requisition to validate
        reason: The rejection reason
        
    Raises:
        ValidationError: If the requisition cannot be rejected or if the reason is invalid
    """
    if requisition.status != DocumentStatus.SUBMITTED:
        raise ValidationError(
            message=f"Cannot reject requisition with status {requisition.status}. Must be SUBMITTED.",
            details={
                "document_number": requisition.document_number,
                "current_status": requisition.status.value,
                "required_status": DocumentStatus.SUBMITTED.value,
                "operation": "reject",
                "entity_type": "Requisition"
            }
        )
    
    # Validate reason is provided
    if not reason or not reason.strip():
        raise ValidationError(
            message="Rejection reason must be provided",
            details={
                "document_number": requisition.document_number,
                "error": "missing_rejection_reason",
                "operation": "reject"
            }
        )

def validate_requisition_for_deletion(requisition: Requisition) -> None:
    """
    Validate that a requisition can be deleted.
    
    Args:
        requisition: The requisition to validate
        
    Raises:
        ValidationError: If the requisition cannot be deleted
    """
    if requisition.status not in [DocumentStatus.DRAFT, DocumentStatus.REJECTED]:
        raise ValidationError(
            message=f"Cannot delete requisition with status {requisition.status}. Only DRAFT or REJECTED requisitions can be deleted.",
            details={
                "document_number": requisition.document_number,
                "current_status": requisition.status.value,
                "allowed_statuses": [DocumentStatus.DRAFT.value, DocumentStatus.REJECTED.value],
                "operation": "delete",
                "reason": "invalid_status_for_deletion"
            }
        )

def validate_requisition_for_update(requisition: Requisition, update_data: RequisitionUpdate) -> None:
    """
    Validate that a requisition can be updated with the provided data.
    
    Args:
        requisition: The requisition to validate
        update_data: The update data
        
    Raises:
        ValidationError: If the update is not allowed
    """
    # Don't allow updating items after requisition is submitted
    if (requisition.status != DocumentStatus.DRAFT and 
        update_data.items is not None and 
        update_data.status is None):  # Allow status updates
        raise ValidationError(
            message="Cannot update items after requisition is submitted",
            details={
                "document_number": requisition.document_number,
                "current_status": requisition.status.value,
                "attempted_update": "items",
                "reason": "items_locked_after_submission"
            }
        )
    
    # If status changes, validate the transition
    if update_data.status is not None and update_data.status != requisition.status:
        if not validate_requisition_status_transition(requisition.status, update_data.status):
            raise ValidationError(
                message=f"Invalid status transition from {requisition.status} to {update_data.status}",
                details={
                    "document_number": requisition.document_number,
                    "current_status": requisition.status.value,
                    "requested_status": update_data.status.value,
                    "entity_type": "Requisition"
                }
            )
        
        # If changing to SUBMITTED, validate items
        if update_data.status == DocumentStatus.SUBMITTED:
            validate_requisition_items(requisition.items)

def validate_requisition_for_order_creation(requisition: Requisition) -> None:
    """
    Validate that a requisition can be used to create an order.
    
    Args:
        requisition: The requisition to validate
        
    Raises:
        ValidationError: If an order cannot be created from the requisition
    """
    if requisition.status != DocumentStatus.APPROVED:
        raise ValidationError(
            message=f"Cannot create order from requisition with status {requisition.status}. Must be APPROVED.",
            details={
                "requisition_number": requisition.document_number,
                "current_status": requisition.status.value,
                "required_status": DocumentStatus.APPROVED.value,
                "operation": "create_order_from_requisition"
            }
        )

def prepare_rejection_update(requisition: Requisition, reason: str) -> RequisitionUpdate:
    """
    Prepare a requisition update for rejection.
    
    Args:
        requisition: The requisition being rejected
        reason: The rejection reason
        
    Returns:
        RequisitionUpdate object with rejected status and updated notes
    """
    # Add rejection reason to notes
    new_notes = append_note(requisition.notes, f"REJECTED: {reason}")
    
    return RequisitionUpdate(
        status=DocumentStatus.REJECTED,
        notes=new_notes
    )

def filter_requisitions(
    requisitions: List[Requisition],
    status: Optional[Union[DocumentStatus, List[DocumentStatus]]] = None,
    requester: Optional[str] = None,
    department: Optional[str] = None,
    search_term: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[Requisition]:
    """
    Filter requisitions based on criteria.
    
    Args:
        requisitions: List of requisitions to filter
        status: Optional status(es) to filter by
        requester: Optional requester to filter by
        department: Optional department to filter by
        search_term: Optional search term to filter by
        date_from: Optional start date for creation date range
        date_to: Optional end date for creation date range
        
    Returns:
        Filtered list of requisitions
    """
    filtered_requisitions = requisitions
    
    # Filter by status if provided
    if status:
        if isinstance(status, list):
            filtered_requisitions = [r for r in filtered_requisitions if r.status in status]
        else:
            filtered_requisitions = [r for r in filtered_requisitions if r.status == status]
    
    # Filter by requester if provided
    if requester:
        filtered_requisitions = [r for r in filtered_requisitions if r.requester == requester]
    
    # Filter by department if provided
    if department:
        filtered_requisitions = [r for r in filtered_requisitions if r.department == department]
    
    # Filter by search term if provided
    if search_term:
        search_term = search_term.lower()
        result = []
        for req in filtered_requisitions:
            if (
                search_term in req.description.lower() or
                search_term in req.document_number.lower() or
                any(search_term in item.description.lower() for item in req.items)
            ):
                result.append(req)
        filtered_requisitions = result
    
    # Filter by date range if provided
    if date_from:
        filtered_requisitions = [r for r in filtered_requisitions if r.created_at >= date_from]
    if date_to:
        filtered_requisitions = [r for r in filtered_requisitions if r.created_at <= date_to]
    
    return filtered_requisitions
