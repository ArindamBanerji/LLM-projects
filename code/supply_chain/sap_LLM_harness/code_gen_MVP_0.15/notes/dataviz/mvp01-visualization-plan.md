# MVP 0.1 Visualization Assessment

## Current Capabilities Analysis

### 1. Core Features Available
- Material Management Operations
  - Material availability checks
  - Material master creation
  - Stock level tracking
- P2P Process Flow
  - PR creation and management
  - PO creation and management
  - Document status tracking
- State Management
  - Document state tracking
  - Basic validation
  - Status updates

### 2. Visualizable Workflows

#### Material Management View
- Stock levels by material
- Material availability status
- Recent material operations
- Basic material master data

#### Document Flow View
- PR → PO flow visualization
- Document status indicators
- Relationship tracking
- Basic timeline view

#### Operations Monitor
- Recent SAP calls summary
- Success/failure metrics
- Basic operation timeline
- Status distribution

### 3. Required Enhancements

#### Core Enhancements
```python
# Add timestamp tracking to state manager
class StateManager:
    def __init__(self):
        self.state_history = []
    
    async def update_state(self, operation: str, data: dict):
        self.state_history.append({
            'timestamp': datetime.now(),
            'operation': operation,
            'data': data
        })
```

#### Data Transformation
```python
# Add data formatting for visualization
class VisualizationFormatter:
    def format_material_data(self, data: dict) -> dict:
        return {
            'materials': self._format_materials(data),
            'stock_levels': self._format_stock_levels(data),
            'operations': self._format_operations(data)
        }
    
    def format_document_flow(self, data: dict) -> dict:
        return {
            'nodes': self._create_nodes(data),
            'edges': self._create_edges(data),
            'timeline': self._create_timeline(data)
        }
```

#### FastAPI Integration
```python
# Add WebSocket support for updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(json.loads(data))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### 4. Implementation Plan

#### Phase 1: Setup (1-2 days)
- Configure Google Colab environment
- Setup ngrok tunneling
- Initialize Streamlit application
- Basic state management integration

#### Phase 2: Core Visualization (2-3 days)
- Implement material dashboard
- Create document flow view
- Add operations monitor
- Basic styling and layout

#### Phase 3: Integration (1-2 days)
- Add WebSocket connections
- Implement state updates
- Add data transformations
- Basic error handling

### 5. Technical Components

#### Streamlit Configuration
```python
import streamlit as st

st.set_page_config(
    page_title="SAP Test Harness",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Session state initialization
if 'history' not in st.session_state:
    st.session_state.history = []
if 'active_view' not in st.session_state:
    st.session_state.active_view = 'material'
```

#### Data Refresh Mechanism
```python
def get_updated_data():
    # Fetch current state
    current_state = api.get_current_state()
    
    # Transform for visualization
    formatter = VisualizationFormatter()
    return {
        'material_view': formatter.format_material_data(current_state),
        'document_view': formatter.format_document_flow(current_state),
        'operations_view': formatter.format_operations(current_state)
    }
```

#### WebSocket Handler
```python
async def handle_updates():
    uri = f"ws://{ngrok_url}/ws"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                data = await websocket.recv()
                st.session_state.history.append(json.loads(data))
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Connection error: {e}")
                await asyncio.sleep(1)
```

### 6. Success Metrics

#### Visualization Goals
- Real-time state updates < 2s
- Clear workflow visualization
- Intuitive material status display
- Efficient operation monitoring

#### Technical Goals
- Stable WebSocket connection
- Efficient state management
- Clean error handling
- Responsive interface