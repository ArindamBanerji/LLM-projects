# services/state_manager.py
from typing import Dict, Any, Optional, Type, TypeVar, Generic
import json
import os
from datetime import datetime
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class StateManager:
    """
    Service for managing application state.
    Provides in-memory storage with optional persistence.
    """
    def __init__(self, persistence_file: Optional[str] = None):
        self._state: Dict[str, Any] = {}
        self._persistence_file = persistence_file
        
        # Try to load state from file if persistence is enabled
        if self._persistence_file and os.path.exists(self._persistence_file):
            try:
                self._load_state_from_file()
            except Exception as e:
                print(f"Error loading state from file: {e}")
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the state.
        
        Args:
            key: State key
            value: Value to store
        """
        self._state[key] = value
        self._persist_state()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the state.
        
        Args:
            key: State key
            default: Default value if key doesn't exist
            
        Returns:
            The stored value or default
        """
        return self._state.get(key, default)
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from the state.
        
        Args:
            key: State key to delete
            
        Returns:
            True if the key was deleted, False if it didn't exist
        """
        if key in self._state:
            del self._state[key]
            self._persist_state()
            return True
        return False
    
    def get_model(self, key: str, model_class: Type[T]) -> Optional[T]:
        """
        Get a value and convert it to a Pydantic model.
        
        Args:
            key: State key
            model_class: Pydantic model class to convert to
            
        Returns:
            Pydantic model instance or None if key doesn't exist
        """
        data = self.get(key)
        if data is None:
            return None
        
        if isinstance(data, dict):
            return model_class(**data)
        elif isinstance(data, model_class):
            return data
        else:
            raise TypeError(f"Cannot convert data to {model_class.__name__}")
    
    def set_model(self, key: str, model: BaseModel) -> None:
        """
        Set a Pydantic model in the state.
        
        Args:
            key: State key
            model: Pydantic model instance
        """
        self.set(key, model)
    
    def get_all_keys(self) -> list:
        """
        Get all keys in the state.
        
        Returns:
            List of all keys
        """
        return list(self._state.keys())
    
    def clear(self) -> None:
        """Clear all state"""
        self._state = {}
        self._persist_state()
    
    def _persist_state(self) -> None:
        """Persist the state to a file if persistence is enabled"""
        if not self._persistence_file:
            return
        
        # Create a serializable version of the state
        serializable_state = {}
        for key, value in self._state.items():
            if isinstance(value, BaseModel):
                serializable_state[key] = value.model_dump()
            elif isinstance(value, datetime):
                serializable_state[key] = value.isoformat()
            else:
                serializable_state[key] = value
        
        try:
            with open(self._persistence_file, 'w') as f:
                json.dump(serializable_state, f)
        except Exception as e:
            print(f"Error persisting state: {e}")
    
    def _load_state_from_file(self) -> None:
        """Load state from the persistence file"""
        if not self._persistence_file:
            return
        
        with open(self._persistence_file, 'r') as f:
            self._state = json.load(f)

# Create a singleton instance
state_manager = StateManager()
