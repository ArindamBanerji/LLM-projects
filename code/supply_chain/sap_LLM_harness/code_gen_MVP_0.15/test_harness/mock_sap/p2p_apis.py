"""
P2P (Procure-to-Pay) process API implementations for SAP simulator.
Provides basic P2P operations for test harness MVP 0.1.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import uuid

# Import with full paths to avoid any import issues
from test_harness.mock_sap.sap_types import SAPResponse, SAPError
from test_harness.mock_sap.api_operations import MockMaterialManagement

class P2PSimulator:
    """
    SAP P2P process simulator implementing core P2P operations.
    
    Features:
    - Purchase Requisition creation and management
    - Purchase Order creation and management
    - Document status tracking
    - Basic state management
    """
    
    def __init__(
        self,
        material_management: Optional[MockMaterialManagement] = None
    ):
        """
        Initialize P2P simulator with optional material management
        
        Args:
            material_management: Material management instance for stock checks
        """
        # Configure logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize material management
        self.material_management = material_management or MockMaterialManagement()
        
        # Initialize document storage
        self._state = {
            'purchase_requisitions': {},
            'purchase_orders': {}
        }

        # Initialize valid vendors and plants for MVP 0.1
        self._valid_vendors = {'VENDOR001'}
        self._valid_plants = {'PLANT_1'}
    
    async def create_purchase_requisition(
        self, 
        pr_data: Dict[str, Any]
    ) -> SAPResponse:
        """
        Create a purchase requisition
        
        Args:
            pr_data: Dictionary containing:
                - material_id: Material to order
                - quantity: Required quantity
                - delivery_date: Required delivery date
                - plant: Requesting plant
        
        Returns:
            SAPResponse with PR details
        """
        try:
            # Validate required fields
            required_fields = ['material_id', 'quantity', 'delivery_date', 'plant']
            missing_fields = [
                field for field in required_fields 
                if field not in pr_data
            ]
            
            if missing_fields:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='PR001',
                        message='Missing required fields',
                        details={'missing_fields': missing_fields}
                    )
                )

            # Validate quantity
            if pr_data['quantity'] <= 0:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='PR004',
                        message='Quantity must be greater than zero'
                    )
                )

            # Validate plant before material check
            if pr_data['plant'] not in self._valid_plants:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='PR003',
                        message=f'Plant {pr_data["plant"]} not found'
                    )
                )
            
            # Check material availability
            material_check = await self.material_management.check_material_availability(
                pr_data['material_id'],
                pr_data['plant']
            )
            
            if not material_check.success:
                error_code = 'PR002'  # Default to material error
                error_msg = material_check.error.message
                
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code=error_code,
                        message=error_msg
                    )
                )
            
            # Generate PR number
            pr_number = f"PR{len(self._state['purchase_requisitions']) + 1:010d}"
            
            # Create PR record
            pr_record = {
                'pr_number': pr_number,
                'material_id': pr_data['material_id'],
                'quantity': pr_data['quantity'],
                'delivery_date': pr_data['delivery_date'],
                'plant': pr_data['plant'],
                'status': 'CREATED',
                'created_at': datetime.utcnow().isoformat(),
                'material_data': material_check.data
            }
            
            # Store PR in state
            self._state['purchase_requisitions'][pr_number] = pr_record
            
            self.logger.info(f"Purchase Requisition created: {pr_number}")
            
            return SAPResponse(
                success=True,
                data={
                    'pr_number': pr_number,
                    'status': 'CREATED'
                }
            )
        
        except Exception as e:
            error_msg = f"PR creation failed: {str(e)}"
            self.logger.error(error_msg)
            return SAPResponse(
                success=False,
                error=SAPError(
                    code='PR999',
                    message=error_msg
                )
            )
    
    async def create_purchase_order(
        self, 
        po_data: Dict[str, Any]
    ) -> SAPResponse:
        """
        Create a purchase order from a purchase requisition
        
        Args:
            po_data: Dictionary containing:
                - pr_number: Reference PR number
                - vendor_id: Supplier ID
                - delivery_date: Optional expected delivery date
        
        Returns:
            SAPResponse with PO details
        """
        try:
            # Validate required fields
            required_fields = ['pr_number', 'vendor_id']
            missing_fields = [
                field for field in required_fields 
                if field not in po_data
            ]
            
            if missing_fields:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='PO001',
                        message='Missing required fields',
                        details={'missing_fields': missing_fields}
                    )
                )

            # Check PR existence before vendor validation
            pr_number = po_data['pr_number']
            if pr_number not in self._state['purchase_requisitions']:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='PO002',
                        message=f'PR {pr_number} not found'
                    )
                )

            # Validate vendor
            if po_data['vendor_id'] not in self._valid_vendors:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='PO004',
                        message=f'Vendor {po_data["vendor_id"]} not found'
                    )
                )
            
            pr_record = self._state['purchase_requisitions'][pr_number]
            
            # Check if PR is already ordered
            if pr_record['status'] == 'ORDERED':
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='PO003',
                        message=f'PR {pr_number} is already ordered'
                    )
                )
            
            # Generate PO number
            po_number = f"PO{len(self._state['purchase_orders']) + 1:010d}"
            
            # Create PO record
            po_record = {
                'po_number': po_number,
                'pr_number': pr_number,
                'vendor_id': po_data['vendor_id'],
                'material_id': pr_record['material_id'],
                'quantity': pr_record['quantity'],
                'delivery_date': po_data.get('delivery_date', pr_record['delivery_date']),
                'plant': pr_record['plant'],
                'status': 'CREATED',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Update PR status
            pr_record['status'] = 'ORDERED'
            
            # Store PO in state
            self._state['purchase_orders'][po_number] = po_record
            
            self.logger.info(f"Purchase Order created: {po_number}")
            
            return SAPResponse(
                success=True,
                data={
                    'po_number': po_number,
                    'status': 'CREATED'
                }
            )
        
        except Exception as e:
            error_msg = f"PO creation failed: {str(e)}"
            self.logger.error(error_msg)
            return SAPResponse(
                success=False,
                error=SAPError(
                    code='PO999',
                    message=error_msg
                )
            )
    
    async def check_document_status(
        self, 
        document_number: str,
        document_type: str
    ) -> SAPResponse:
        """
        Check status of a P2P document
        
        Args:
            document_number: PR or PO number
            document_type: Type of document ('PR' or 'PO')
        
        Returns:
            SAPResponse with document status
        """
        try:
            doc_type = document_type.upper()
            
            # Determine document collection
            if doc_type == 'PR':
                collection = self._state['purchase_requisitions']
            elif doc_type == 'PO':
                collection = self._state['purchase_orders']
            else:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='DOC001',
                        message=f'Invalid document type: {document_type}'
                    )
                )
            
            # Check if document exists
            if document_number not in collection:
                return SAPResponse(
                    success=False,
                    error=SAPError(
                        code='DOC002',
                        message=f'Document {document_number} not found'
                    )
                )
            
            document = collection[document_number]
            
            return SAPResponse(
                success=True,
                data={
                    'document_number': document_number,
                    'document_type': doc_type,
                    'status': document['status'],
                    'created_at': document['created_at']
                }
            )
        
        except Exception as e:
            error_msg = f"Status check failed: {str(e)}"
            self.logger.error(error_msg)
            return SAPResponse(
                success=False,
                error=SAPError(
                    code='DOC999',
                    message=error_msg
                )
            )
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current P2P state
        
        Returns:
            Dictionary with current state
        """
        return self._state.copy()
    
    def reset_state(self) -> None:
        """Reset P2P state to initial values"""
        self._state = {
            'purchase_requisitions': {},
            'purchase_orders': {}
        }
        self.logger.info("P2P state reset")