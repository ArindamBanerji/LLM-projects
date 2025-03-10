# tests/test_state_manager.py
import pytest
import os
import tempfile
import json
from services.state_manager import StateManager
from models.common import BaseDataModel

class TestStateManager:
    def setup_method(self):
        """Create a fresh StateManager for each test"""
        self.state_manager = StateManager()
    
    def test_set_and_get(self):
        """Test setting and getting values"""
        # Set a value
        self.state_manager.set("test_key", "test_value")
        
        # Get the value
        value = self.state_manager.get("test_key")
        
        assert value == "test_value"
    
    def test_get_nonexistent(self):
        """Test getting a non-existent key"""
        # Get a non-existent key
        value = self.state_manager.get("nonexistent")
        
        assert value is None
    
    def test_get_with_default(self):
        """Test getting a non-existent key with a default value"""
        # Get a non-existent key with a default value
        value = self.state_manager.get("nonexistent", "default")
        
        assert value == "default"
    
    def test_delete(self):
        """Test deleting a key"""
        # Set a value
        self.state_manager.set("test_key", "test_value")
        
        # Delete the key
        result = self.state_manager.delete("test_key")
        
        assert result is True
        assert self.state_manager.get("test_key") is None
    
    def test_delete_nonexistent(self):
        """Test deleting a non-existent key"""
        # Delete a non-existent key
        result = self.state_manager.delete("nonexistent")
        
        assert result is False
    
    def test_get_all_keys(self):
        """Test getting all keys"""
        # Set some values
        self.state_manager.set("key1", "value1")
        self.state_manager.set("key2", "value2")
        
        # Get all keys
        keys = self.state_manager.get_all_keys()
        
        assert len(keys) == 2
        assert "key1" in keys
        assert "key2" in keys
    
    def test_clear(self):
        """Test clearing all state"""
        # Set some values
        self.state_manager.set("key1", "value1")
        self.state_manager.set("key2", "value2")
        
        # Clear all state
        self.state_manager.clear()
        
        assert len(self.state_manager.get_all_keys()) == 0
    
    def test_pydantic_model_storage(self):
        """Test storing and retrieving Pydantic models"""
        # Create a model
        model = BaseDataModel(id="test-id")
        
        # Store the model
        self.state_manager.set_model("model", model)
        
        # Retrieve the model
        retrieved = self.state_manager.get_model("model", BaseDataModel)
        
        assert retrieved is not None
        assert retrieved.id == "test-id"
    
    def test_persistence(self):
        """Test state persistence to file"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = temp.name
        
        try:
            # Create a StateManager with persistence
            persistent_manager = StateManager(persistence_file=temp_path)
            
            # Set some values
            persistent_manager.set("key1", "value1")
            persistent_manager.set("key2", "value2")
            
            # Create a new StateManager that should load from the file
            loaded_manager = StateManager(persistence_file=temp_path)
            
            # Check that the values were loaded
            assert loaded_manager.get("key1") == "value1"
            assert loaded_manager.get("key2") == "value2"
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
