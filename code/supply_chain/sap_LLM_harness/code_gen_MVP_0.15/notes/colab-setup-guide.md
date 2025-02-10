# Google Colab Setup and Execution Guide for SAP Test Harness MVP 0.1

## Environment Requirements

### Required Pip Installations
Create a `requirements.txt` with:
```
pytest==7.4.3
pytest-asyncio==0.21.1
typing-extensions>=4.8.0
python-dateutil>=2.8.2
```

Install in Colab using:
```python
!pip install -r requirements.txt
```

### File Structure
Required directory structure in Colab:
```
/content
  /test_harness/
    __init__.py
    /mock_sap/
      __init__.py
      sap_types.py
      api_operations.py
      api_simulator.py
      p2p_apis.py
    /tests/
      __init__.py
      test_config.py  
      test_material_ops.py
      test_p2p_flow.py
      test_runner.py
```

### Module Imports

#### Core Library Imports
```python
# Standard library imports
import unittest
import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid
```

#### Import Sequence (Order Matters)
```python
# First level: Core types
from test_harness.mock_sap.sap_types import SAPResponse, SAPError

# Second level: Operations
from test_harness.mock_sap.api_operations import MockMaterialManagement

# Third level: Simulator
from test_harness.mock_sap.api_simulator import SAPSimulator

# Fourth level: P2P
from test_harness.mock_sap.p2p_apis import P2PSimulator

# Test imports
from test_harness.tests.test_config import TestConfig
```

## Test Execution in Colab

### Setup Cell
Create an initial setup cell in your Colab notebook:

```python
# Install requirements
!pip install pytest==7.4.3 pytest-asyncio==0.21.1 typing-extensions>=4.8.0 python-dateutil>=2.8.2

# Create directory structure
!mkdir -p /content/test_harness/mock_sap
!mkdir -p /content/test_harness/tests

# Add __init__.py files
!touch /content/test_harness/__init__.py
!touch /content/test_harness/mock_sap/__init__.py
!touch /content/test_harness/tests/__init__.py
```

### File Creation Cells
Create separate cells for each source file:

```python
%%writefile /content/test_harness/mock_sap/sap_types.py
# Paste sap_types.py content here
```

Repeat for each file in the structure.

### Test Execution Cell
Create a cell for running tests:

```python
# Option 1: Run all tests
!python -m pytest /content/test_harness/tests -v

# Option 2: Run specific test file
!python -m pytest /content/test_harness/tests/test_material_ops.py -v

# Option 3: Run using test runner
!python /content/test_harness/tests/test_runner.py
```

### Debugging Cell
Create a cell for debugging:

```python
# Import modules for interactive testing
from test_harness.mock_sap.sap_types import SAPResponse, SAPError
from test_harness.mock_sap.api_operations import MockMaterialManagement
from test_harness.mock_sap.p2p_apis import P2PSimulator

# Create test instances
material_mgmt = MockMaterialManagement()
p2p_simulator = P2PSimulator(material_management=material_mgmt)

# Run async test function
async def test_pr_creation():
    response = await p2p_simulator.create_purchase_requisition({
        'material_id': 'MAT001',
        'quantity': 100,
        'delivery_date': '2024-03-01',
        'plant': 'PLANT_1'
    })
    print(response)

# Execute test
await test_pr_creation()
```

## Best Practices for Colab Execution

1. **Cell Organization**:
   - Keep setup cells at the top
   - Group related code files together
   - Place test execution cells last
   - Add markdown cells for documentation

2. **Error Handling**:
   - Add try-except blocks in test cells
   - Print detailed error messages
   - Check cell execution order

3. **State Management**:
   - Reset test state between runs
   - Clear variables if needed
   - Restart runtime for clean state

4. **Debugging Tips**:
   - Use print statements for visibility
   - Check file paths carefully
   - Verify import statements
   - Run tests individually first

## Common Issues and Solutions

1. **Import Errors**:
   - Verify directory structure
   - Check file paths
   - Ensure __init__.py files exist
   - Restart runtime after file creation

2. **Async Execution**:
   - Use await for async functions
   - Wrap in asyncio.run() if needed
   - Check for event loop errors

3. **File Access**:
   - Use absolute paths in Colab
   - Verify file permissions
   - Check file creation success

4. **Test Discovery**:
   - Ensure test files start with "test_"
   - Verify test class inheritance
   - Check test method names

## Test Case Examples

### Basic Material Operations

1. **Check Material Availability**
```python
async def test_material_availability():
    material_mgmt = MockMaterialManagement()
    
    # Test default material
    response = await material_mgmt.check_material_availability(
        material_id='MAT001',
        plant='PLANT_1'
    )
    
    # Assertions
    assert response.success
    assert response.data['material_id'] == 'MAT001'
    assert response.data['unrestricted_stock'] == 1000.0
    
    # Example output:
    # {
    #     'success': True,
    #     'data': {
    #         'material_id': 'MAT001',
    #         'plant': 'PLANT_1',
    #         'unrestricted_stock': 1000.0,
    #         'storage_location': 'A01'
    #     }
    # }
```

2. **Create Material Master**
```python
async def test_create_material():
    material_mgmt = MockMaterialManagement()
    
    # Test data
    new_material = {
        'material_id': 'TEST001',
        'description': 'Test Material',
        'type': 'RAW',
        'base_unit': 'KG',
        'plant_data': {
            'PLANT_1': {
                'storage_location': 'A01',
                'unrestricted_stock': 500.0
            }
        }
    }
    
    response = await material_mgmt.create_material_master(new_material)
    assert response.success
    assert response.data['material_id'] == 'TEST001'
```

### P2P Process Flow

1. **Create Purchase Requisition**
```python
async def test_create_pr():
    p2p = P2PSimulator()
    
    # Test data
    pr_data = {
        'material_id': 'MAT001',
        'quantity': 100,
        'delivery_date': '2024-03-01',
        'plant': 'PLANT_1'
    }
    
    response = await p2p.create_purchase_requisition(pr_data)
    assert response.success
    assert response.data['status'] == 'CREATED'
    
    # Example output:
    # {
    #     'success': True,
    #     'data': {
    #         'pr_number': 'PR0000000001',
    #         'status': 'CREATED'
    #     }
    # }
```

2. **Complete PR to PO Flow**
```python
async def test_pr_to_po_flow():
    p2p = P2PSimulator()
    
    # Create PR
    pr_data = {
        'material_id': 'MAT001',
        'quantity': 100,
        'delivery_date': '2024-03-01',
        'plant': 'PLANT_1'
    }
    pr_response = await p2p.create_purchase_requisition(pr_data)
    assert pr_response.success
    
    # Create PO
    po_data = {
        'pr_number': pr_response.data['pr_number'],
        'vendor_id': 'VENDOR001'
    }
    po_response = await p2p.create_purchase_order(po_data)
    assert po_response.success
    
    # Check PR status
    pr_status = await p2p.check_document_status(
        pr_response.data['pr_number'],
        'PR'
    )
    assert pr_status.data['status'] == 'ORDERED'
```

### Error Case Examples

1. **Invalid Material Check**
```python
async def test_invalid_material():
    material_mgmt = MockMaterialManagement()
    
    response = await material_mgmt.check_material_availability(
        material_id='INVALID',
        plant='PLANT_1'
    )
    
    assert not response.success
    assert response.error.code == 'MAT_AVAIL_002'
    
    # Example error output:
    # {
    #     'success': False,
    #     'error': {
    #         'code': 'MAT_AVAIL_002',
    #         'message': 'Material INVALID not found'
    #     }
    # }
```

2. **Duplicate PO Creation**
```python
async def test_duplicate_po():
    p2p = P2PSimulator()
    
    # Create initial PR and PO
    pr_data = {
        'material_id': 'MAT001',
        'quantity': 100,
        'delivery_date': '2024-03-01',
        'plant': 'PLANT_1'
    }
    pr_response = await p2p.create_purchase_requisition(pr_data)
    
    po_data = {
        'pr_number': pr_response.data['pr_number'],
        'vendor_id': 'VENDOR001'
    }
    
    # First PO creation
    first_po = await p2p.create_purchase_order(po_data)
    assert first_po.success
    
    # Attempt duplicate PO
    second_po = await p2p.create_purchase_order(po_data)
    assert not second_po.success
    assert second_po.error.code == 'PO003'
```

### Advanced Testing Scenarios

1. **Complex State Verification**
```python
async def test_state_management():
    p2p = P2PSimulator()
    
    # Create PR
    pr_data = {
        'material_id': 'MAT001',
        'quantity': 100,
        'delivery_date': '2024-03-01',
        'plant': 'PLANT_1'
    }
    pr_response = await p2p.create_purchase_requisition(pr_data)
    
    # Verify initial state
    state = p2p.get_state()
    pr_number = pr_response.data['pr_number']
    
    assert pr_number in state['purchase_requisitions']
    assert state['purchase_requisitions'][pr_number]['status'] == 'CREATED'
    
    # Create PO and verify state changes
    po_data = {
        'pr_number': pr_number,
        'vendor_id': 'VENDOR001'
    }
    po_response = await p2p.create_purchase_order(po_data)
    
    # Verify updated state
    new_state = p2p.get_state()
    assert new_state['purchase_requisitions'][pr_number]['status'] == 'ORDERED'
    assert po_response.data['po_number'] in new_state['purchase_orders']
```

2. **Multiple Document Flow**
```python
async def test_multiple_documents():
    p2p = P2PSimulator()
    
    # Create multiple PRs
    pr_responses = []
    for i in range(3):
        pr_data = {
            'material_id': 'MAT001',
            'quantity': 100 * (i + 1),
            'delivery_date': '2024-03-01',
            'plant': 'PLANT_1'
        }
        response = await p2p.create_purchase_requisition(pr_data)
        assert response.success
        pr_responses.append(response)
    
    # Create POs for each PR
    for pr_response in pr_responses:
        po_data = {
            'pr_number': pr_response.data['pr_number'],
            'vendor_id': 'VENDOR001'
        }
        po_response = await p2p.create_purchase_order(po_data)
        assert po_response.success
    
    # Verify final state
    state = p2p.get_state()
    assert len(state['purchase_orders']) == 3
    for pr_response in pr_responses:
        pr_number = pr_response.data['pr_number']
        assert state['purchase_requisitions'][pr_number]['status'] == 'ORDERED'
```

### Running Test Cases in Colab

To run these test cases in Colab:

1. **Create Test File**
```python
%%writefile /content/test_harness/tests/test_examples.py
# Paste any of the above test cases here
```

2. **Run Specific Test**
```python
!python -m pytest /content/test_harness/tests/test_examples.py -v -k "test_create_pr"
```

3. **Run with Output**
```python
!python -m pytest /content/test_harness/tests/test_examples.py -v --capture=no
```

## Next Steps

After successful setup:
1. Run basic tests to verify environment
2. Add your test cases
3. Implement additional features
4. Extend test coverage