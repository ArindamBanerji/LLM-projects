# models/common.py
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator

class BaseDataModel(BaseModel):
    """
    Base model for all data models in the application.
    Provides common attributes and functionality.
    """
    id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)  # Changed from Optional[datetime] to init with current time
    
    @field_validator('updated_at', mode='before')
    def set_updated_at(cls, v):
        """Set updated_at to current time when the model is updated"""
        return datetime.now()

    def update(self, data: Dict[str, Any]) -> None:
        """
        Update the model with the provided data.
        Will only update fields that exist in the model.
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

class EntityCollection(BaseModel):
    """
    A collection of entities of the same type.
    Used to store and retrieve entities from the state manager.
    """
    name: str
    entities: Dict[str, Any] = Field(default_factory=dict)
    
    def add(self, entity_id: str, entity: Any) -> None:
        """Add an entity to the collection"""
        self.entities[entity_id] = entity
    
    def get(self, entity_id: str) -> Optional[Any]:
        """Get an entity from the collection by ID"""
        return self.entities.get(entity_id)
    
    def get_all(self) -> List[Any]:
        """Get all entities in the collection"""
        return list(self.entities.values())
    
    def remove(self, entity_id: str) -> bool:
        """Remove an entity from the collection by ID"""
        if entity_id in self.entities:
            del self.entities[entity_id]
            return True
        return False
    
    def count(self) -> int:
        """Get the number of entities in the collection"""
        return len(self.entities)
