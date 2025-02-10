# SAP Test Harness Documentation - Core Components

## Overview
This test harness simulates SAP API behavior for P2P (Procure-to-Pay) operations, focusing on material management and procurement processes. Built for MVP 0.1, it provides basic functionality for testing without requiring an actual SAP system.

## Core Architecture

### Directory Structure
```
test_harness/
  mock_sap/
    __init__.py
    sap_types.py         # Core type definitions
    api_operations.py    # Material management
    api_simulator.py     # Core simulator engine
    p2p_apis.py         # P2P operations
  tests/
    __init__.py
    test_config.py      # Test configuration
    test_material_ops.py # Material tests
    test_p2p_flow.py    # P2P flow tests
    test_runner.py      # Test execution
```

## The above directory structure has been flattened into the below map to accomodate Claude project restrictions.

| Original Path | Flattened Name |
|--------------|----------------|
| __init__.py | __init__.py |
| mock_sap\__init__.py | mock_sap___init__.py |
| mock_sap\api_operations.py | mock_sap_api_operations.py |
| mock_sap\api_simulator.py | mock_sap_api_simulator.py |
| mock_sap\p2p_apis.py | mock_sap_p2p_apis.py |
| mock_sap\sap_types.py | mock_sap_sap_types.py |
| requirements.txt | requirements.txt |
| tests\__init__.py | tests___init__.py |
| tests\test_config.py | tests_test_config.py |
| tests\test_material_ops.py | tests_test_material_ops.py |
| tests\test_p2p_flow.py | tests_test_p2p_flow.py |
| tests\test_runner.py | tests_test_runner.py |




### Component Dependencies
```
sap_types.py <-- api_operations.py <-- api_simulator.py <-- p2p_apis.py
                                                      ^
                                                      |
                                        test files use these components
```

## Core Components

### 1. Type System (`sap_types.py`)

#### Purpose
- Defines standard response and error types
- Ensures consistent API behavior
- Provides type validation
- Supports error handling

#### Key Classes
```python
@dataclass
class SAPError:
    """
    Standard error structure.
    - code: Error identifier (e.g., AUTH001, MAT001)
    - message: Human-readable description
    - details: Additional error context
    """
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class SAPResponse:
    """
    Standard response wrapper.
    - success: Operation status
    - data: Response payload (for success)
    - error: Error details (for failure)
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[SAPError] = None
```

#### Usage Notes
- Always use SAPResponse for API returns
- Include appropriate error codes
- Provide detailed error messages
- Use details field for debugging

### 2. Material Management (`api_operations.py`)

#### Purpose
- Handles material-related operations
- Manages stock levels
- Provides material validation
- Tracks material master data

#### Core Class
```python
class MockMaterialManagement:
    """
    Simulates SAP material operations.
    Key features:
    - Material availability checks
    - Material master creation
    - Stock management
    - Basic validation
    """
```

#### Key Methods
```python
async def check_material_availability(
    self, 
    material_id: str, 
    plant: str
) -> SAPResponse:
    """
    Checks material stock levels.
    Used by: P2P process for PR creation
    """

async def create_material_master(
    self, 
    material_data: Dict[str, Any]
) -> SAPResponse:
    """
    Creates new materials.
    Used by: Test setup and data initialization
    """
```

#### State Management
- Uses in-memory dictionary for material data
- Maintains stock levels per plant
- Tracks material master records
- Handles basic validation

### 3. API Simulator (`api_simulator.py`)

#### Purpose
- Provides core simulation engine
- Handles authentication
- Routes API requests
- Manages global state

#### Core Class
```python
class SAPSimulator:
    """
    Core simulation engine.
    Features:
    - Authentication handling
    - Request routing
    - Operation execution
    - State management
    """
```

#### Key Methods
```python
async def authenticate(
    self, 
    credentials: Dict[str, str]
) -> SAPResponse:
    """
    Handles user authentication.
    Used by: All operations requiring auth
    """

async def execute_request(
    self, 
    operation: str, 
    parameters: Dict[str, Any],
    auth_token: Optional[str] = None
) -> SAPResponse:
    """
    Routes and executes operations.
    Used by: All API operations
    """
```

#### Authentication Flow
1. Client provides credentials
2. System generates token
3. Token required for operations
4. Token expiration handled

### 4. P2P Operations (`p2p_apis.py`)

#### Purpose
- Implements P2P process flow
- Manages document creation
- Handles document relationships
- Tracks process state

#### Core Class
```python
class P2PSimulator:
    """
    P2P process simulator.
    Features:
    - PR creation and management
    - PO creation and management
    - Document status tracking
    - Basic state management
    """
```

#### Key Methods
```python
async def create_purchase_requisition(
    self, 
    pr_data: Dict[str, Any]
) -> SAPResponse:
    """
    Creates purchase requisitions.
    Requirements:
    - Valid material
    - Valid plant
    - Sufficient stock
    """

async def create_purchase_order(
    self, 
    po_data: Dict[str, Any]
) -> SAPResponse:
    """
    Creates purchase orders.
    Requirements:
    - Valid PR reference
    - PR not already ordered
    - Valid vendor
    """
```

#### Document Flow
```
PR Creation → PR Approval → PO Creation → PO Processing
     ↓            ↓             ↓              ↓
  Validation   State Update  PR Update    State Update
```

## Testing Components

### 1. Test Configuration (`test_config.py`)
- Defines test settings
- Provides test data
- Configures test behavior
- Manages test state

### 2. Material Tests (`test_material_ops.py`)
- Tests material operations
- Validates stock checks
- Verifies material creation
- Tests error cases

### 3. P2P Tests (`test_p2p_flow.py`)
- Tests complete P2P flow
- Validates document states
- Checks error handling
- Tests relationships

### 4. Test Runner (`test_runner.py`)
- Manages test execution
- Provides test reporting
- Handles async tests
- Supports test filtering

## Common Debugging Areas

### Authentication Issues
1. Check credentials format
2. Verify token generation
3. Check token expiration
4. Validate token usage

### State Management Issues
1. Check initial state
2. Verify state transitions
3. Check document relationships
4. Validate final state

### Document Flow Issues
1. Verify document creation
2. Check status updates
3. Validate relationships
4. Check error handling

### Material Issues
1. Check material existence
2. Verify stock levels
3. Validate plant data
4. Check material master

[Part 2 will cover testing details, error handling, and advanced usage...]

# SAP Test Harness Documentation - Testing and Advanced Usage

## Testing Framework

### Test Organization

#### 1. Configuration Management (`test_config.py`)
```python
class TestConfig:
    """
    Test configuration class.
    Used for: Managing test data and settings
    Location: test_harness/tests/test_config.py
    """
    
    # Default test material for availability checks
    DEFAULT_MATERIAL = {
        'material_id': 'MAT001',
        'description': 'Test Material',
        'type': 'RAW',
        'base_unit': 'KG',
        'plant_data': {
            'PLANT_1': {
                'storage_location': 'A01',
                'unrestricted_stock': 1000.0
            }
        }
    }
```

#### Test Data Management
- Default test data provided
- Test data isolation
- Data cleanup between tests
- State reset capabilities

### Test Implementation Patterns

#### 1. Material Operation Tests
```python
class TestMaterialOperations(unittest.TestCase):
    """
    Tests material management functionality.
    File: test_harness/tests/test_material_ops.py
    """
    
    def setUp(self):
        """Creates fresh test environment"""
        self.material_mgmt = MockMaterialManagement()
    
    async def test_check_material_availability(self):
        """
        Tests material availability check.
        Success path: Valid material and plant
        """
        response = await self.material_mgmt.check_material_availability(
            'MAT001', 
            'PLANT_1'
        )
        self.assertTrue(response.success)
        self.assertIsNotNone(response.data['unrestricted_stock'])
    
    async def test_invalid_material(self):
        """
        Tests invalid material handling.
        Error path: Non-existent material
        """
        response = await self.material_mgmt.check_material_availability(
            'INVALID', 
            'PLANT_1'
        )
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, 'MAT_AVAIL_002')
```

#### 2. P2P Process Tests
```python
class TestP2PFlow(unittest.TestCase):
    """
    Tests P2P process flow.
    File: test_harness/tests/test_p2p_flow.py
    """
    
    def setUp(self):
        """Initialize P2P simulator"""
        self.material_mgmt = MockMaterialManagement()
        self.p2p_simulator = P2PSimulator(
            material_management=self.material_mgmt
        )
    
    async def test_complete_p2p_flow(self):
        """
        Tests complete PR to PO flow.
        Validates: Document creation and relationships
        """
        # Create PR
        pr_response = await self.p2p_simulator.create_purchase_requisition({
            'material_id': 'MAT001',
            'quantity': 100,
            'plant': 'PLANT_1'
        })
        self.assertTrue(pr_response.success)
        
        # Create PO
        po_response = await self.p2p_simulator.create_purchase_order({
            'pr_number': pr_response.data['pr_number'],
            'vendor_id': 'VENDOR001'
        })
        self.assertTrue(po_response.success)
```

## Error Handling Patterns

### 1. Error Types and Codes
```python
# Authentication Errors
AUTH001 = "Invalid credentials"
AUTH002 = "Token expired"

# Material Errors
MAT_AVAIL_001 = "Invalid material ID or plant"
MAT_AVAIL_002 = "Material not found"
MAT_CREATE_001 = "Missing required fields"

# P2P Errors
PR001 = "Invalid PR data"
PO001 = "Invalid PO data"
PO002 = "PR not found"
PO003 = "PR already ordered"
```

### 2. Error Response Creation
```python
def create_error_response(code: str, message: str, details: Dict = None) -> SAPResponse:
    """
    Creates standardized error response.
    Used by: All API operations
    """
    return SAPResponse(
        success=False,
        error=SAPError(
            code=code,
            message=message,
            details=details
        )
    )
```

### 3. Error Handling in Operations
```python
async def check_material_availability(
    self, 
    material_id: str, 
    plant: str
) -> SAPResponse:
    """Example of operation error handling"""
    try:
        # Input validation
        if not material_id or not plant:
            return SAPResponse.error_response(
                'MAT_AVAIL_001',
                'Invalid material ID or plant'
            )
        
        # Business logic validation
        if material_id not in self._material_master:
            return SAPResponse.error_response(
                'MAT_AVAIL_002',
                f'Material {material_id} not found'
            )
        
        # Process request...
        
    except Exception as e:
        return SAPResponse.error_response(
            'MAT_AVAIL_999',
            f'Unexpected error: {str(e)}'
        )
```

## Advanced Usage Patterns

### 1. Custom Material Management
```python
# Create custom material management with seed data
material_mgmt = MockMaterialManagement(
    seed_data={
        'CUSTOM001': {
            'material_id': 'CUSTOM001',
            'description': 'Custom Material',
            'type': 'RAW',
            'base_unit': 'KG',
            'plant_data': {
                'PLANT_1': {
                    'storage_location': 'A01',
                    'unrestricted_stock': 500.0
                }
            }
        }
    }
)
```

### 2. State Management
```python
# Track and verify state changes
initial_state = p2p_simulator.get_state()
response = await p2p_simulator.create_purchase_requisition(pr_data)
final_state = p2p_simulator.get_state()

# Verify state changes
assert response.data['pr_number'] in final_state['purchase_requisitions']
assert final_state['purchase_requisitions'][response.data['pr_number']]['status'] == 'CREATED'
```

### 3. Complex Testing Scenarios
```python
async def test_multiple_documents():
    """Test multiple document creation and relationships"""
    # Create multiple PRs
    pr_numbers = []
    for i in range(3):
        pr_data = {
            'material_id': 'MAT001',
            'quantity': 100 * (i + 1),
            'plant': 'PLANT_1'
        }
        response = await p2p_simulator.create_purchase_requisition(pr_data)
        pr_numbers.append(response.data['pr_number'])
    
    # Create POs for each PR
    for pr_number in pr_numbers:
        po_data = {
            'pr_number': pr_number,
            'vendor_id': 'VENDOR001'
        }
        response = await p2p_simulator.create_purchase_order(po_data)
        assert response.success
```

## Debugging Techniques

### 1. State Inspection
```python
def inspect_state(p2p_simulator: P2PSimulator):
    """Debug state inspection"""
    state = p2p_simulator.get_state()
    print("Current State:")
    print(f"PRs: {json.dumps(state['purchase_requisitions'], indent=2)}")
    print(f"POs: {json.dumps(state['purchase_orders'], indent=2)}")
```

### 2. Response Validation
```python
def validate_response(response: SAPResponse):
    """Debug response validation"""
    if response.success:
        print(f"Success Response: {json.dumps(response.data, indent=2)}")
    else:
        print(f"Error Response:")
        print(f"Code: {response.error.code}")
        print(f"Message: {response.error.message}")
        print(f"Details: {json.dumps(response.error.details, indent=2)}")
```

### 3. Operation Tracing
```python
async def trace_operation(operation_func, *args, **kwargs):
    """Debug operation execution"""
    print(f"Operation Start: {operation_func.__name__}")
    print(f"Args: {args}")
    print(f"Kwargs: {kwargs}")
    
    response = await operation_func(*args, **kwargs)
    
    print(f"Operation Result:")
    validate_response(response)
    return response
```

## Common Issues and Solutions

### 1. Authentication Issues
- Problem: Token validation failing
- Check: Token expiration and format
- Solution: Reset authentication state

### 2. State Inconsistencies
- Problem: Unexpected document states
- Check: State transitions and validation
- Solution: Reset simulator state

### 3. Material Issues
- Problem: Material not found
- Check: Material master data
- Solution: Verify seed data

### 4. Document Flow Issues
- Problem: Document creation failing
- Check: Required fields and references
- Solution: Verify input data

## Performance Considerations

### 1. Memory Management
- Clear state between tests
- Reset simulators when needed
- Clean up test data
- Monitor memory usage

### 2. Async Operations
- Use proper await syntax
- Handle concurrent operations
- Manage operation timeouts
- Track operation completion

### 3. Resource Cleanup
- Reset state after tests
- Clear authentication tokens
- Clean up test data
- Release resources

## Extension Points

### 1. Custom Operations
- Add new material operations
- Extend P2P functionality
- Implement custom validation
- Add new document types

### 2. Enhanced Validation
- Add business rules
- Implement complex validation
- Add data consistency checks
- Extend error handling

### 3. State Extensions
- Add persistent storage
- Implement state recovery
- Add state history
- Extend state validation