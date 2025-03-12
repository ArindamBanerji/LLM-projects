# services/p2p_service.py
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date

from models.p2p import (
    Requisition, RequisitionCreate, RequisitionUpdate, RequisitionItem,
    Order, OrderCreate, OrderUpdate, OrderItem,
    DocumentStatus, DocumentItemStatus, ProcurementType,
    P2PDataLayer
)
from models.material import MaterialStatus
from services.state_manager import state_manager
from services.material_service import material_service
from services.p2p_service_helpers import (
    validate_material_active, prepare_received_items, 
    determine_order_status_from_items, append_note
)
from services.p2p_service_order import (
    validate_order_for_submission, validate_order_for_approval,
    validate_order_for_receipt, validate_order_for_completion,
    validate_order_for_cancellation, validate_order_for_deletion,
    prepare_order_update_with_received_items, filter_orders
)
from services.p2p_service_requisition import (
    validate_requisition_for_submission, validate_requisition_for_approval,
    validate_requisition_for_rejection, validate_requisition_for_deletion,
    validate_requisition_for_update, validate_requisition_for_order_creation,
    prepare_rejection_update, filter_requisitions
)
from utils.error_utils import NotFoundError, ValidationError, ConflictError, BadRequestError

class P2PService:
    """
    Service class for Procure-to-Pay (P2P) business logic.
    Provides a facade over the P2P data layer with additional
    validations and business logic for requisitions and orders.
    """
    
    def __init__(self, state_manager_instance=None, material_service_instance=None):
        """
        Initialize the service with a state manager instance.
        
        Args:
            state_manager_instance: Optional state manager instance for dependency injection
            material_service_instance: Optional material service instance for dependency injection
        """
        self.state_manager = state_manager_instance or state_manager
        self.material_service = material_service_instance or material_service
        self.data_layer = P2PDataLayer(self.state_manager)
    
    # ===== Requisition Core Methods (CRUD) =====
    
    def get_requisition(self, document_number: str) -> Requisition:
        """
        Get a requisition by document number.
        
        Args:
            document_number: The requisition document number
            
        Returns:
            The requisition object
            
        Raises:
            NotFoundError: If the requisition is not found
        """
        requisition = self.data_layer.get_requisition(document_number)
        if not requisition:
            raise NotFoundError(
                message=f"Requisition {document_number} not found",
                details={
                    "document_number": document_number,
                    "entity_type": "Requisition"
                }
            )
        return requisition
    
    def list_requisitions(self, 
                          status: Optional[Union[DocumentStatus, List[DocumentStatus]]] = None,
                          requester: Optional[str] = None,
                          department: Optional[str] = None,
                          search_term: Optional[str] = None,
                          date_from: Optional[datetime] = None,
                          date_to: Optional[datetime] = None) -> List[Requisition]:
        """
        List requisitions with optional filtering.
        
        Args:
            status: Optional status(es) to filter by
            requester: Optional requester to filter by
            department: Optional department to filter by
            search_term: Optional search term to filter by
            date_from: Optional start date for creation date range
            date_to: Optional end date for creation date range
            
        Returns:
            List of requisitions matching the criteria
        """
        # Get all requisitions and use the filter helper
        all_requisitions = self.data_layer.list_requisitions()
        return filter_requisitions(
            all_requisitions,
            status=status,
            requester=requester,
            department=department,
            search_term=search_term,
            date_from=date_from,
            date_to=date_to
        )
    
    def create_requisition(self, requisition_data: RequisitionCreate) -> Requisition:
        """
        Create a new requisition with business logic validations.
        
        Args:
            requisition_data: The requisition creation data
            
        Returns:
            The created requisition
            
        Raises:
            ValidationError: If the requisition data is invalid
            ConflictError: If a requisition with the same number already exists
        """
        # Validate material references in items if provided
        for item in requisition_data.items:
            if item.material_number:
                try:
                    validate_material_active(self.material_service, item.material_number)
                except ValidationError as e:
                    # Enhance error with item context
                    raise ValidationError(
                        message=f"Invalid material in item {item.item_number}: {e.message}",
                        details={
                            "item_number": item.item_number,
                            "material_number": item.material_number,
                            "original_error": e.details if hasattr(e, 'details') else {}
                        }
                    )
        
        # Create the requisition
        try:
            return self.data_layer.create_requisition(requisition_data)
        except ConflictError as e:
            # Enhance conflict error with more context
            raise ConflictError(
                message=e.message,
                details={
                    "document_number": requisition_data.document_number,
                    "entity_type": "Requisition",
                    "conflict_reason": "document_number_exists" 
                }
            )
    
    def update_requisition(self, document_number: str, update_data: RequisitionUpdate) -> Requisition:
        """
        Update a requisition with business logic validations.
        
        Args:
            document_number: The requisition document number
            update_data: The requisition update data
            
        Returns:
            The updated requisition
            
        Raises:
            NotFoundError: If the requisition is not found
            ValidationError: If the update data is invalid
        """
        # Check if requisition exists
        requisition = self.get_requisition(document_number)
        
        # Validate the update
        try:
            validate_requisition_for_update(requisition, update_data)
        except ValidationError as e:
            # Re-raise the validation error
            raise ValidationError(
                message=f"Cannot update requisition {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Update the requisition
        updated_requisition = self.data_layer.update_requisition(document_number, update_data)
        if not updated_requisition:
            raise NotFoundError(
                message=f"Requisition {document_number} not found",
                details={
                    "document_number": document_number,
                    "entity_type": "Requisition",
                    "operation": "update"
                }
            )
        
        return updated_requisition
    
    def delete_requisition(self, document_number: str) -> bool:
        """
        Delete a requisition with business logic validations.
        
        Args:
            document_number: The requisition document number
            
        Returns:
            True if the requisition was deleted, False otherwise
            
        Raises:
            NotFoundError: If the requisition is not found
            ValidationError: If the requisition cannot be deleted
        """
        # Check if requisition exists
        requisition = self.get_requisition(document_number)
        
        # Validate the requisition can be deleted
        try:
            validate_requisition_for_deletion(requisition)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot delete requisition {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Delete the requisition
        result = self.data_layer.delete_requisition(document_number)
        if not result:
            raise NotFoundError(
                message=f"Requisition {document_number} not found",
                details={
                    "document_number": document_number,
                    "entity_type": "Requisition",
                    "operation": "delete"
                }
            )
        
        return result
    
    # ===== Requisition Workflow Operations =====
    
    def submit_requisition(self, document_number: str) -> Requisition:
        """
        Submit a requisition for approval.
        
        Args:
            document_number: The requisition document number
            
        Returns:
            The updated requisition
            
        Raises:
            NotFoundError: If the requisition is not found
            ValidationError: If the requisition cannot be submitted
        """
        # Check if requisition exists
        requisition = self.get_requisition(document_number)
        
        # Validate the requisition can be submitted
        try:
            validate_requisition_for_submission(requisition)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot submit requisition {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Update status to SUBMITTED
        update_data = RequisitionUpdate(status=DocumentStatus.SUBMITTED)
        return self.update_requisition(document_number, update_data)
    
    def approve_requisition(self, document_number: str) -> Requisition:
        """
        Approve a requisition.
        
        Args:
            document_number: The requisition document number
            
        Returns:
            The updated requisition
            
        Raises:
            NotFoundError: If the requisition is not found
            ValidationError: If the requisition cannot be approved
        """
        # Check if requisition exists
        requisition = self.get_requisition(document_number)
        
        # Validate the requisition can be approved
        try:
            validate_requisition_for_approval(requisition)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot approve requisition {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Update status to APPROVED
        update_data = RequisitionUpdate(status=DocumentStatus.APPROVED)
        return self.update_requisition(document_number, update_data)
    
    def reject_requisition(self, document_number: str, reason: str) -> Requisition:
        """
        Reject a requisition.
        
        Args:
            document_number: The requisition document number
            reason: The reason for rejection
            
        Returns:
            The updated requisition
            
        Raises:
            NotFoundError: If the requisition is not found
            ValidationError: If the requisition cannot be rejected
        """
        # Check if requisition exists
        requisition = self.get_requisition(document_number)
        
        # Validate the requisition can be rejected
        try:
            validate_requisition_for_rejection(requisition, reason)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot reject requisition {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Prepare and apply the update
        update_data = prepare_rejection_update(requisition, reason)
        return self.update_requisition(document_number, update_data)
    
    # ===== Order Core Methods (CRUD) =====
    
    def get_order(self, document_number: str) -> Order:
        """
        Get an order by document number.
        
        Args:
            document_number: The order document number
            
        Returns:
            The order object
            
        Raises:
            NotFoundError: If the order is not found
        """
        order = self.data_layer.get_order(document_number)
        if not order:
            raise NotFoundError(
                message=f"Order {document_number} not found",
                details={
                    "document_number": document_number,
                    "entity_type": "Order"
                }
            )
        return order
    
    def list_orders(self, 
                    status: Optional[Union[DocumentStatus, List[DocumentStatus]]] = None,
                    vendor: Optional[str] = None,
                    requisition_reference: Optional[str] = None,
                    search_term: Optional[str] = None,
                    date_from: Optional[datetime] = None,
                    date_to: Optional[datetime] = None) -> List[Order]:
        """
        List orders with optional filtering.
        
        Args:
            status: Optional status(es) to filter by
            vendor: Optional vendor to filter by
            requisition_reference: Optional requisition reference to filter by
            search_term: Optional search term to filter by
            date_from: Optional start date for creation date range
            date_to: Optional end date for creation date range
            
        Returns:
            List of orders matching the criteria
        """
        # Get all orders and use the filter helper
        all_orders = self.data_layer.list_orders()
        return filter_orders(
            all_orders,
            status=status,
            vendor=vendor,
            requisition_reference=requisition_reference,
            search_term=search_term,
            date_from=date_from,
            date_to=date_to
        )
    
    def create_order(self, order_data: OrderCreate) -> Order:
        """
        Create a new order with business logic validations.
        
        Args:
            order_data: The order creation data
            
        Returns:
            The created order
            
        Raises:
            ValidationError: If the order data is invalid
            ConflictError: If an order with the same number already exists
        """
        # Validate materials in items
        for item in order_data.items:
            if item.material_number:
                try:
                    validate_material_active(self.material_service, item.material_number)
                except ValidationError as e:
                    # Enhance error with item context
                    raise ValidationError(
                        message=f"Invalid material in item {item.item_number}: {e.message}",
                        details={
                            "item_number": item.item_number,
                            "material_number": item.material_number,
                            "original_error": e.details if hasattr(e, 'details') else {}
                        }
                    )
        
        # Create the order
        try:
            return self.data_layer.create_order(order_data)
        except ConflictError as e:
            # Enhance conflict error with more context
            raise ConflictError(
                message=e.message,
                details={
                    "document_number": order_data.document_number,
                    "entity_type": "Order",
                    "conflict_reason": "document_number_exists" 
                }
            )
    
    def update_order(self, document_number: str, update_data: OrderUpdate) -> Order:
        """
        Update an order with business logic validations.
        
        Args:
            document_number: The order document number
            update_data: The order update data
            
        Returns:
            The updated order
            
        Raises:
            NotFoundError: If the order is not found
            ValidationError: If the update data is invalid
        """
        # Get the order
        order = self.get_order(document_number)
        
        # Check if we're updating items after submission
        if (order.status != DocumentStatus.DRAFT and 
            update_data.items is not None and 
            update_data.status is None):  # Allow status updates
            raise ValidationError(
                message="Cannot update items after order is submitted",
                details={
                    "document_number": document_number,
                    "current_status": order.status.value,
                    "attempted_update": "items",
                    "reason": "items_locked_after_submission"
                }
            )
        
        # Update the order
        updated_order = self.data_layer.update_order(document_number, update_data)
        if not updated_order:
            raise NotFoundError(
                message=f"Order {document_number} not found",
                details={
                    "document_number": document_number,
                    "entity_type": "Order",
                    "operation": "update"
                }
            )
        
        return updated_order
    
    def delete_order(self, document_number: str) -> bool:
        """
        Delete an order with business logic validations.
        
        Args:
            document_number: The order document number
            
        Returns:
            True if the order was deleted, False otherwise
            
        Raises:
            NotFoundError: If the order is not found
            ValidationError: If the order cannot be deleted
        """
        # Check if order exists
        order = self.get_order(document_number)
        
        # Validate the order can be deleted
        try:
            validate_order_for_deletion(order)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot delete order {document_number}: {e.message}",
                details={
                    "document_number": document_number,
                    "current_status": order.status.value,
                    "allowed_status": DocumentStatus.DRAFT.value,
                    "operation": "delete",
                    "reason": "invalid_status_for_deletion",
                    "validation_errors": e.details if hasattr(e, 'details') else {}
                }
            )
        
        # Delete the order
        result = self.data_layer.delete_order(document_number)
        if not result:
            raise NotFoundError(
                message=f"Order {document_number} not found",
                details={
                    "document_number": document_number,
                    "entity_type": "Order",
                    "operation": "delete"
                }
            )
        
        return result
    
    # ===== Order Workflow Operations =====
    
    def create_order_from_requisition(self, requisition_number: str, vendor: str, 
                                      payment_terms: Optional[str] = None) -> Order:
        """
        Create an order from a requisition.
        
        Args:
            requisition_number: The requisition document number
            vendor: The vendor for the order
            payment_terms: Optional payment terms
            
        Returns:
            The created order
            
        Raises:
            NotFoundError: If the requisition is not found
            ValidationError: If the requisition cannot be converted to an order
        """
        # Check if requisition exists
        requisition = self.get_requisition(requisition_number)
        
        # Validate the requisition can be used to create an order
        try:
            validate_requisition_for_order_creation(requisition)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot create order from requisition {requisition_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Create the order
        try:
            return self.data_layer.create_order_from_requisition(
                requisition_number, vendor, payment_terms
            )
        except Exception as e:
            # Handle any other exceptions
            raise BadRequestError(
                message=f"Failed to create order from requisition {requisition_number}: {str(e)}",
                details={
                    "requisition_number": requisition_number,
                    "vendor": vendor,
                    "error": str(e)
                }
            )
    
    def submit_order(self, document_number: str) -> Order:
        """
        Submit an order for approval.
        
        Args:
            document_number: The order document number
            
        Returns:
            The updated order
            
        Raises:
            NotFoundError: If the order is not found
            ValidationError: If the order cannot be submitted
        """
        # Check if order exists
        order = self.get_order(document_number)
        
        # Validate the order for submission
        try:
            validate_order_for_submission(order)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot submit order {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Update status to SUBMITTED
        update_data = OrderUpdate(status=DocumentStatus.SUBMITTED)
        return self.update_order(document_number, update_data)
    
    def approve_order(self, document_number: str) -> Order:
        """
        Approve an order.
        
        Args:
            document_number: The order document number
            
        Returns:
            The updated order
            
        Raises:
            NotFoundError: If the order is not found
            ValidationError: If the order cannot be approved
        """
        # Check if order exists
        order = self.get_order(document_number)
        
        # Validate the order for approval
        try:
            validate_order_for_approval(order)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot approve order {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Update status to APPROVED
        update_data = OrderUpdate(status=DocumentStatus.APPROVED)
        return self.update_order(document_number, update_data)
    
    def receive_order(self, document_number: str, 
                      received_items: Dict[int, float] = None) -> Order:
        """
        Receive an order (partially or completely).
        
        Args:
            document_number: The order document number
            received_items: Dictionary mapping item numbers to received quantities
                            If None, receive all items in full
            
        Returns:
            The updated order
            
        Raises:
            NotFoundError: If the order is not found
            ValidationError: If the order cannot be received
        """
        # Check if order exists
        order = self.get_order(document_number)
        
        # Validate the order for receipt
        try:
            validate_order_for_receipt(order)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot receive order {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Validate received quantities if provided
        if received_items:
            # Verify all items exist in the order
            order_item_numbers = [item.item_number for item in order.items]
            unknown_items = [item_num for item_num in received_items.keys() if item_num not in order_item_numbers]
            
            if unknown_items:
                raise ValidationError(
                    message=f"Order {document_number} contains unknown item numbers",
                    details={
                        "document_number": document_number,
                        "unknown_items": unknown_items,
                        "valid_items": order_item_numbers,
                        "reason": "unknown_item_numbers"
                    }
                )
            
            # Verify received quantities are not negative
            negative_quantities = {item_num: qty for item_num, qty in received_items.items() if qty < 0}
            if negative_quantities:
                raise ValidationError(
                    message="Received quantities cannot be negative",
                    details={
                        "document_number": document_number,
                        "negative_quantities": negative_quantities,
                        "reason": "negative_quantities"
                    }
                )
            
            # Verify received quantities do not exceed ordered quantities
            for item in order.items:
                if item.item_number in received_items:
                    if received_items[item.item_number] > item.quantity - item.received_quantity:
                        raise ValidationError(
                            message=f"Received quantity exceeds remaining quantity for item {item.item_number}",
                            details={
                                "document_number": document_number,
                                "item_number": item.item_number,
                                "ordered_quantity": item.quantity,
                                "already_received": item.received_quantity,
                                "attempted_receive": received_items[item.item_number],
                                "max_allowed": item.quantity - item.received_quantity,
                                "reason": "quantity_exceeds_remaining"
                            }
                        )
        
        # Prepare and apply the update
        update_data = prepare_order_update_with_received_items(order, received_items)
        return self.update_order(document_number, update_data)
    
    def complete_order(self, document_number: str) -> Order:
        """
        Mark an order as completed.
        
        Args:
            document_number: The order document number
            
        Returns:
            The updated order
            
        Raises:
            NotFoundError: If the order is not found
            ValidationError: If the order cannot be completed
        """
        # Check if order exists
        order = self.get_order(document_number)
        
        # Validate the order for completion
        try:
            validate_order_for_completion(order)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot complete order {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Update status to COMPLETED
        update_data = OrderUpdate(status=DocumentStatus.COMPLETED)
        return self.update_order(document_number, update_data)
    
    def cancel_order(self, document_number: str, reason: str) -> Order:
        """
        Cancel an order.
        
        Args:
            document_number: The order document number
            reason: The reason for cancellation
            
        Returns:
            The updated order
            
        Raises:
            NotFoundError: If the order is not found
            ValidationError: If the order cannot be canceled
        """
        # Check if order exists
        order = self.get_order(document_number)
        
        # Validate the order for cancellation
        try:
            validate_order_for_cancellation(order)
        except ValidationError as e:
            raise ValidationError(
                message=f"Cannot cancel order {document_number}: {e.message}",
                details=e.details if hasattr(e, 'details') else {}
            )
        
        # Validate reason is provided
        if not reason or not reason.strip():
            raise ValidationError(
                message="Cancellation reason must be provided",
                details={
                    "document_number": document_number,
                    "error": "missing_cancellation_reason",
                    "operation": "cancel"
                }
            )
        
        # Update status to CANCELED and add cancellation reason to notes
        new_notes = append_note(order.notes, f"CANCELED: {reason}")
        
        update_data = OrderUpdate(
            status=DocumentStatus.CANCELED,
            notes=new_notes
        )
        return self.update_order(document_number, update_data)

# Create a singleton instance
p2p_service = P2PService()
