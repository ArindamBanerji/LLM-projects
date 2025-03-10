# manual_tests/test_p2p.py
import os
import sys

# Add the parent directory to the path so Python can find the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.p2p import (
    Requisition, RequisitionCreate, RequisitionUpdate, RequisitionItem,
    Order, OrderCreate, OrderUpdate, OrderItem,
    DocumentStatus, DocumentItemStatus, ProcurementType,
    P2PDataLayer
)
from services.state_manager import state_manager
from utils.error_utils import BadRequestError, ConflictError, NotFoundError

def run_p2p_tests():
    """Run manual tests for P2P data models"""
    
    # Create an instance of the data layer
    p2p_layer = P2PDataLayer(state_manager)
    
    print("\n=== P2P DATA MODEL MANUAL TESTS ===\n")

    try:
        # 1. Create a purchase requisition
        print("\n--- Test 1: Creating a purchase requisition ---")
        req_create = RequisitionCreate(
            document_number="PR001",
            description="Test Requisition",
            requester="John Doe",
            department="IT",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Laptop Computer",
                    quantity=2,
                    unit="EA",
                    price=1200.00
                ),
                RequisitionItem(
                    item_number=2,
                    description="Monitor",
                    quantity=2,
                    unit="EA",
                    price=300.00
                )
            ]
        )

        requisition = p2p_layer.create_requisition(req_create)
        print(f"Created requisition: {requisition.document_number}")
        print(f"Requester: {requisition.requester}, Department: {requisition.department}")
        print(f"Status: {requisition.status}")
        print(f"Items: {len(requisition.items)}")
        print(f"Total value: ${requisition.total_value}")

        # 2. Update requisition status to SUBMITTED
        print("\n--- Test 2: Submitting the requisition ---")
        req_update = RequisitionUpdate(status=DocumentStatus.SUBMITTED)
        updated_req = p2p_layer.update_requisition("PR001", req_update)
        print(f"Updated status: {updated_req.status}")

        # 3. Approve the requisition
        print("\n--- Test 3: Approving the requisition ---")
        req_update = RequisitionUpdate(status=DocumentStatus.APPROVED)
        updated_req = p2p_layer.update_requisition("PR001", req_update)
        print(f"Updated status: {updated_req.status}")

        # 4. Create a purchase order from the requisition
        print("\n--- Test 4: Creating a purchase order from the requisition ---")
        order = p2p_layer.create_order_from_requisition(
            requisition_number="PR001",
            vendor="ABC Computers",
            payment_terms="Net 30"
        )
        print(f"Created order: {order.document_number}")
        print(f"Vendor: {order.vendor}")
        print(f"Created from requisition: {order.requisition_reference}")
        print(f"Status: {order.status}")
        print(f"Items: {len(order.items)}")
        for item in order.items:
            print(f"- {item.item_number}: {item.description}, Qty: {item.quantity}, Unit: {item.unit}, Price: ${item.price}")
            print(f"  From requisition: {item.requisition_reference}, Item: {item.requisition_item}")

        # 5. Check requisition status after order creation
        print("\n--- Test 5: Checking requisition after order creation ---")
        req = p2p_layer.get_requisition("PR001")
        print(f"Requisition status: {req.status}")
        for item in req.items:
            print(f"- Item {item.item_number} assigned to order: {item.assigned_to_order}")

        # 6. Test document status transitions
        print("\n--- Test 6: Testing document status transitions ---")
        
        # Create a fresh order that we can control the status of
        order_create = OrderCreate(
            document_number="PO002",
            description="Direct Order for Testing",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=1,
                    unit="EA",
                    price=50.00
                )
            ]
        )
        test_order = p2p_layer.create_order(order_create)
        print(f"Created test order: {test_order.document_number}")
        print(f"Initial status: {test_order.status}")
        
        # Test status transitions systematically
        print("\nTesting possible transitions from DRAFT:")
        
        # Try DRAFT → SUBMITTED (Should work)
        try:
            order_update = OrderUpdate(status=DocumentStatus.SUBMITTED)
            updated_order = p2p_layer.update_order("PO002", order_update)
            print(f"✓ DRAFT → SUBMITTED: Success, new status: {updated_order.status}")
        except BadRequestError as e:
            print(f"✗ DRAFT → SUBMITTED: Failed: {str(e)}")
        
        # Try SUBMITTED → APPROVED (Should work)
        try:
            order_update = OrderUpdate(status=DocumentStatus.APPROVED)
            updated_order = p2p_layer.update_order("PO002", order_update)
            print(f"✓ SUBMITTED → APPROVED: Success, new status: {updated_order.status}")
        except BadRequestError as e:
            print(f"✗ SUBMITTED → APPROVED: Failed: {str(e)}")
            
        # Create another order for different status tests
        order_create = OrderCreate(
            document_number="PO003",
            description="Order for Cancel Test",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=1,
                    unit="EA",
                    price=50.00
                )
            ]
        )
        cancel_order = p2p_layer.create_order(order_create)
        print(f"\nCreated another test order: {cancel_order.document_number}")
        
        # Try DRAFT → CANCELED (Should work)
        try:
            order_update = OrderUpdate(status=DocumentStatus.CANCELED)
            updated_order = p2p_layer.update_order("PO003", order_update)
            print(f"✓ DRAFT → CANCELED: Success, new status: {updated_order.status}")
        except BadRequestError as e:
            print(f"✗ DRAFT → CANCELED: Failed: {str(e)}")
            
        # Create another order for testing invalid transitions
        order_create = OrderCreate(
            document_number="PO004",
            description="Order for Invalid Transition Test",
            requester="Test User",
            vendor="Test Vendor",
            items=[
                OrderItem(
                    item_number=1,
                    description="Test Item",
                    quantity=1,
                    unit="EA",
                    price=50.00
                )
            ]
        )
        invalid_test_order = p2p_layer.create_order(order_create)
        print(f"\nCreated test order for invalid transitions: {invalid_test_order.document_number}")
        
        # Try DRAFT → APPROVED (Should fail)
        try:
            order_update = OrderUpdate(status=DocumentStatus.APPROVED)
            updated_order = p2p_layer.update_order("PO004", order_update)
            print(f"! DRAFT → APPROVED: Unexpectedly worked, new status: {updated_order.status}")
        except BadRequestError as e:
            print(f"✓ DRAFT → APPROVED: Correctly rejected: {str(e)}")
            
        # Try DRAFT → COMPLETED (Should fail)
        try:
            order_update = OrderUpdate(status=DocumentStatus.COMPLETED)
            updated_order = p2p_layer.update_order("PO004", order_update)
            print(f"! DRAFT → COMPLETED: Unexpectedly worked, new status: {updated_order.status}")
        except BadRequestError as e:
            print(f"✓ DRAFT → COMPLETED: Correctly rejected: {str(e)}")

        # 7. List all procurement documents
        print("\n--- Test 7: Listing all requisitions ---")
        all_reqs = p2p_layer.list_requisitions()
        print(f"Total requisitions: {len(all_reqs)}")
        for req in all_reqs:
            print(f"- {req.document_number}: {req.description} (Status: {req.status})")

        print("\n--- Test 8: Listing all orders ---")
        all_orders = p2p_layer.list_orders()
        print(f"Total orders: {len(all_orders)}")
        for order in all_orders:
            print(f"- {order.document_number}: {order.description} (Status: {order.status})")

        # 8. Filter documents by status
        print("\n--- Test 9: Filtering orders by status ---")
        approved_orders = p2p_layer.filter_orders(status=DocumentStatus.APPROVED)
        print(f"Orders with APPROVED status: {len(approved_orders)}")
        for order in approved_orders:
            print(f"- {order.document_number}: {order.description} (Vendor: {order.vendor})")
        
        # 9. Test invalid status transitions
        print("\n--- Test 10: Testing invalid status transitions ---")
        
        # Create a new requisition for testing
        req_create = RequisitionCreate(
            document_number="PR002",
            description="Test Invalid Transitions",
            requester="Jane Smith",
            items=[
                RequisitionItem(
                    item_number=1,
                    description="Test Item",
                    quantity=1,
                    unit="EA",
                    price=100.00
                )
            ]
        )
        test_req = p2p_layer.create_requisition(req_create)
        
        # Try to skip from DRAFT to APPROVED
        try:
            req_update = RequisitionUpdate(status=DocumentStatus.APPROVED)
            p2p_layer.update_requisition("PR002", req_update)
            print("ERROR: Should not allow DRAFT to APPROVED transition")
        except BadRequestError as e:
            print(f"Correctly rejected invalid transition: {str(e)}")
        
        # Try to create order from DRAFT requisition
        try:
            p2p_layer.create_order_from_requisition(
                requisition_number="PR002",
                vendor="Test Vendor"
            )
            print("ERROR: Should not allow creating order from DRAFT requisition")
        except BadRequestError as e:
            print(f"Correctly rejected order creation: {str(e)}")
        
        # 10. Test duplicate document numbers
        print("\n--- Test 11: Testing duplicate document numbers ---")
        try:
            req_create = RequisitionCreate(
                document_number="PR001",  # Already exists
                description="Duplicate Requisition",
                requester="Test User",
                items=[
                    RequisitionItem(
                        item_number=1,
                        description="Test Item",
                        quantity=1,
                        unit="EA",
                        price=100.00
                    )
                ]
            )
            p2p_layer.create_requisition(req_create)
            print("ERROR: Should not allow duplicate document number")
        except ConflictError as e:
            print(f"Correctly rejected duplicate: {str(e)}")
        
        print("\n=== P2P TEST SUMMARY ===")
        print(f"Total requisitions in system: {p2p_layer.count_requisitions()}")
        print(f"Total orders in system: {p2p_layer.count_orders()}")
        print("P2P tests completed successfully!")
        
    except Exception as e:
        print(f"\nERROR: Test failed with exception: {str(e)}")
        raise

if __name__ == "__main__":
    run_p2p_tests()
