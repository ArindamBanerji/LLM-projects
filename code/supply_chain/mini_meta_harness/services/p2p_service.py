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
    validate_requisition_status_transition, validate_order_status_transition,
    validate_material_active, validate_requisition_items, validate_order_items,
    validate_vendor, prepare_received_items, determine_order_status_from_items,
    append_note
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
    
    # ===== Requisition Methods =====
    
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
            raise NotFoundError(f"Requisition {document_number} not found")
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
        # Get all requisitions first
        all_requisitions = self.data_layer.list_requisitions()
        
        # Filter by status if provided
        if status:
            if isinstance(status, list):
                all_requisitions = [r for r in all_requisitions if r.status in status]
            else:
                all_requisitions = [r for r in all_requisitions if r.status == status]
        
        # Filter by requester if provided
        if requester:
            all_requisitions = [r for r in all_requisitions if r.requester == requester]
        
        # Filter by department if provided
        if department:
            all_requisitions = [r for r in all_requisitions if r.department == department]
        
        # Filter by search term if provided
        if search_term:
            search_term = search_term.lower()
            filtered_requisitions = []
            for req in all_requisitions:
                if (
                    search_term in req.description.lower() or
                    search_term in req.document_number.lower() or
                    any(search_term in item.description.lower() for item in req.items)
                ):
                    filtered_requisitions.append(req)
            all_requisitions = filtered_requisitions
        
        # Filter by date range if provided
        if date_from:
            all_requisitions = [r for r in all_requisitions if r.created_at >= date_from]
        if date_to:
            all_requisitions = [r for r in all_requisitions if r.created_at <= date_to]
        
        return all_requisitions
    
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
                validate_material_active(self.material_service, item.material_number)
        
        # Create the requisition
        return self.data_layer.create_requisition(requisition_data)
    
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
        
        # Add business validations here
        # For example, don't allow updating items after requisition is submitted
        if (requisition.status != DocumentStatus.DRAFT and 
            update_data.items is not None and 
            update_data.status is None):  # Allow status updates
            raise ValidationError("Cannot update items after requisition is submitted")
        
        # If status changes, validate the transition
        if update_data.status is not None and update_data.status != requisition.status:
            if not validate_requisition_status_transition(requisition.status, update_data.status):
                raise ValidationError(
                    f"Invalid status transition from {requisition.status} to {update_data.status}"
                )
            
            # If changing to SUBMITTED, validate items
            if update_data.status == DocumentStatus.SUBMITTED:
                validate_requisition_items(requisition.items)
        
        # Update the requisition
        updated_requisition = self.data_layer.update_requisition(document_number, update_data)
        if not updated_requisition:
            raise NotFoundError(f"Requisition {document_number} not found")
        
        return updated_requisition
    
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
        
        # Check if requisition can be submitted
        if requisition.status != DocumentStatus.DRAFT:
            raise ValidationError(
                f"Cannot submit requisition with status {requisition.status}. Must be DRAFT."
            )
        
        # Validate requisition items
        validate_requisition_items(requisition.items)
        
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
        
        # Check if requisition can be approved
        if requisition.status != DocumentStatus.SUBMITTED:
            raise ValidationError(
                f"Cannot approve requisition with status {requisition.status}. Must be SUBMITTED."
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
        
        # Check if requisition can be rejected
        if requisition.status != DocumentStatus.SUBMITTED:
            raise ValidationError(
                f"Cannot reject requisition with status {requisition.status}. Must be SUBMITTED."
            )
        
        # Update status to REJECTED and add rejection reason to notes
        new_notes = append_note(requisition.notes, f"REJECTED: {reason}")
        
        update_data = RequisitionUpdate(
            status=DocumentStatus.REJECTED,
            notes=new_notes
        )
        return self.update_requisition(document_number, update_data)
    
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
        
        # Check if requisition can be deleted (only allow deleting DRAFT or REJECTED)
        if requisition.status not in [DocumentStatus.DRAFT, DocumentStatus.REJECTED]:
            raise ValidationError(
                f"Cannot delete requisition with status {requisition.status}. " 
                f"Only DRAFT or REJECTED requisitions can be deleted."
            )
        
        # Delete the requisition
        result = self.data_layer.delete_requisition(document_number)
        if not result:
            raise NotFoundError(f"Requisition {document_number} not found")
        
        return result
    
    # ===== Order Methods =====
    
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
            raise NotFoundError(f"Order {document_number} not found")
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
        # Get all orders first
        all_orders = self.data_layer.list_orders()
        
        # Filter by status if provided
        if status:
            if isinstance(status, list):
                all_orders = [o for o in all_orders if o.status in status]
            else:
                all_orders = [o for o in all_orders if o.status == status]
        
        # Filter by vendor if provided
        if vendor:
            all_orders = [o for o in all_orders if o.vendor == vendor]
        
        # Filter by requisition reference if provided
        if requisition_reference:
            all_orders = [o for o in all_orders if o.requisition_reference == requisition_reference]
        
        # Filter by search term if provided
        if search_term:
            search_term = search_term.lower()
            filtered_orders = []
            for order in all_orders:
                if (
                    search_term in order.description.lower() or
                    search_term in order.document_number.lower() or
                    (order.vendor and search_term in order.vendor.lower()) or
                    any(search_term in item.description.lower() for item in order.items)
                ):
                    filtered_orders.append(order)
            all_orders = filtered_orders
        
        # Filter by date range if provided
        if date_from:
            all_orders = [o for o in all_orders if o.created_at >= date_from]
        if date_to:
            all_orders = [o for o in all_orders if o.created_at <= date_to]
        
        return all_orders
    
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
        # Validate vendor
        validate_vendor(order_data.vendor)
        
        # Validate material references in items if provided
        for item in order_data.items:
            if item.material_number:
                validate_material_active(self.material_service, item.material_number)
        
        # Create the order
        return self.data_layer.create_order(order_data)
    
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
        
        # Check if requisition is approved
        if requisition.status != DocumentStatus.APPROVED:
            raise ValidationError(
                f"Cannot create order from requisition with status {requisition.status}. "
                f"Must be APPROVED."
            )
        
        # Validate vendor
        validate_vendor(vendor)
        
        # Create the order
        return self.data_layer.create_order_from_requisition(
            requisition_number, vendor, payment_terms
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
        # Check if order exists
        order = self.get_order(document_number)
        
        # Add business validations here
        # For example, don't allow updating items after order is submitted
        if (order.status != DocumentStatus.DRAFT and 
            update_data.items is not None and 
            update_data.status is None):  # Allow status updates
            raise ValidationError("Cannot update items after order is submitted")
        
        # If status changes, validate the transition
        if update_data.status is not None and update_data.status != order.status:
            if not validate_order_status_transition(order.status, update_data.status):
                raise ValidationError(
                    f"Invalid status transition from {order.status} to {update_data.status}"
                )
            
            # If changing to SUBMITTED, validate items and vendor
            if update_data.status == DocumentStatus.SUBMITTED:
                validate_vendor(order.vendor)
                validate_order_items(order.items)
        
        # Update the order
        updated_order = self.data_layer.update_order(document_number, update_data)
        if not updated_order:
            raise NotFoundError(f"Order {document_number} not found")
        
        return updated_order
    
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
        
        # Check if order can be submitted
        if order.status != DocumentStatus.DRAFT:
            raise ValidationError(
                f"Cannot submit order with status {order.status}. Must be DRAFT."
            )
        
        # Validate vendor and items
        validate_vendor(order.vendor)
        validate_order_items(order.items)
        
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
        
        # Check if order can be approved
        if order.status != DocumentStatus.SUBMITTED:
            raise ValidationError(
                f"Cannot approve order with status {order.status}. Must be SUBMITTED."
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
        
        # Check if order can be received
        if order.status != DocumentStatus.APPROVED:
            raise ValidationError(
                f"Cannot receive order with status {order.status}. Must be APPROVED."
            )
        
        # Prepare updated items with received quantities
        updated_items = prepare_received_items(order, received_items)
        
        # Determine new order status based on items
        new_status = determine_order_status_from_items(updated_items)
        
        # Update order with new items and status
        update_data = OrderUpdate(
            items=updated_items,
            status=new_status
        )
        
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
        
        # Check if order can be completed
        if order.status not in [DocumentStatus.RECEIVED, DocumentStatus.PARTIALLY_RECEIVED]:
            raise ValidationError(
                f"Cannot complete order with status {order.status}. "
                f"Must be RECEIVED or PARTIALLY_RECEIVED."
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
        
        # Check if order can be canceled (not completed or already canceled)
        if order.status in [DocumentStatus.COMPLETED, DocumentStatus.CANCELED]:
            raise ValidationError(
                f"Cannot cancel order with status {order.status}."
            )
        
        # Update status to CANCELED and add cancellation reason to notes
        new_notes = append_note(order.notes, f"CANCELED: {reason}")
        
        update_data = OrderUpdate(
            status=DocumentStatus.CANCELED,
            notes=new_notes
        )
        return self.update_order(document_number, update_data)
    
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
        
        # Check if order can be deleted (only allow deleting DRAFT)
        if order.status != DocumentStatus.DRAFT:
            raise ValidationError(
                f"Cannot delete order with status {order.status}. "
                f"Only DRAFT orders can be deleted."
            )
        
        # Delete the order
        result = self.data_layer.delete_order(document_number)
        if not result:
            raise NotFoundError(f"Order {document_number} not found")
        
        return result


# Create a singleton instance
p2p_service = P2PService()