# models/material.py
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from models.common import BaseDataModel

class MaterialType(str, Enum):
    """
    Types of materials in the system.
    
    Based on SAP material types:
    - RAW: Raw materials used in production
    - SEMIFINISHED: Partially manufactured products
    - FINISHED: Completed products ready for sale
    - SERVICE: Non-physical service items
    - TRADING: Products purchased for resale
    """
    RAW = "RAW"
    SEMIFINISHED = "SEMIFINISHED"
    FINISHED = "FINISHED"
    SERVICE = "SERVICE"
    TRADING = "TRADING"

class UnitOfMeasure(str, Enum):
    """
    Standard units of measure.
    """
    EACH = "EA"
    KILOGRAM = "KG"
    LITER = "L"
    METER = "M"
    HOUR = "HR"
    PIECE = "PC"

class MaterialStatus(str, Enum):
    """
    Status of a material in the system.
    """
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DEPRECATED = "DEPRECATED"
    PLANNED = "PLANNED"

class MaterialCreate(BaseModel):
    """
    Data model for creating a new material.
    """
    material_number: Optional[str] = None  # Optional, system can generate
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    type: MaterialType = MaterialType.FINISHED
    base_unit: UnitOfMeasure = UnitOfMeasure.EACH
    status: MaterialStatus = MaterialStatus.ACTIVE
    
    # Additional properties
    weight: Optional[float] = Field(None, ge=0)
    volume: Optional[float] = Field(None, ge=0)
    dimensions: Optional[Dict[str, float]] = None  # e.g. {"length": 10, "width": 5, "height": 2}
    
    @field_validator('material_number')
    @classmethod
    def validate_material_number(cls, v):
        """Validate material number format if provided"""
        if v is not None:
            if not v.isalnum():
                raise ValueError("Material number must be alphanumeric")
            if len(v) < 4 or len(v) > 18:
                raise ValueError("Material number must be between 4 and 18 characters")
        return v

class MaterialUpdate(BaseModel):
    """
    Data model for updating an existing material.
    Only include fields that can be updated.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    type: Optional[MaterialType] = None
    base_unit: Optional[UnitOfMeasure] = None
    status: Optional[MaterialStatus] = None
    weight: Optional[float] = Field(None, ge=0)
    volume: Optional[float] = Field(None, ge=0)
    dimensions: Optional[Dict[str, float]] = None

class Material(BaseDataModel):
    """
    Material model representing material master data.
    """
    material_number: str
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    type: MaterialType = MaterialType.FINISHED
    base_unit: UnitOfMeasure = UnitOfMeasure.EACH
    status: MaterialStatus = MaterialStatus.ACTIVE
    
    # Additional properties
    weight: Optional[float] = Field(None, ge=0)
    volume: Optional[float] = Field(None, ge=0)
    dimensions: Optional[Dict[str, float]] = None
    
    @classmethod
    def create_from_dict(cls, data: Dict[str, Any]) -> 'Material':
        """Create a Material instance from a dictionary"""
        if 'id' not in data:
            data['id'] = data.get('material_number')
        return cls(**data)
    
    @classmethod
    def create_from_create_model(cls, create_data: MaterialCreate, material_number: Optional[str] = None) -> 'Material':
        """Create a Material instance from a MaterialCreate model"""
        data = create_data.model_dump()
        if material_number:
            data['material_number'] = material_number
        elif not data.get('material_number'):
            # Generate a material number if not provided
            import uuid
            data['material_number'] = f"MAT{uuid.uuid4().hex[:12].upper()}"
        
        data['id'] = data['material_number']
        return cls(**data)
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update material with data from a dictionary"""
        # material_number should not be updated
        if 'material_number' in data:
            data.pop('material_number')
        super().update(data)
        
        # Ensure updated_at is always newer than created_at
        if self.updated_at <= self.created_at:
            self.updated_at = self.created_at + timedelta(milliseconds=1)
    
    def update_from_update_model(self, update_data: MaterialUpdate) -> None:
        """Update material with data from an update model"""
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        self.update_from_dict(update_dict)
        
        # Force updated_at to be newer than created_at
        now = datetime.now()
        if now <= self.created_at:
            now = self.created_at + timedelta(milliseconds=1)
        self.updated_at = now

class MaterialDataLayer:
    """
    Data access layer for Material entities.
    Handles CRUD operations and persistence via the state manager.
    """
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.state_key = "materials"
        
        # Initialize materials collection if it doesn't exist
        if not self.state_manager.get(self.state_key):
            from models.common import EntityCollection
            self.state_manager.set(self.state_key, EntityCollection(name="Materials"))
    
    def _get_collection(self):
        """Get the materials collection from state"""
        from models.common import EntityCollection
        collection = self.state_manager.get_model(self.state_key, EntityCollection)
        if not collection:
            collection = EntityCollection(name="Materials")
            self.state_manager.set_model(self.state_key, collection)
        return collection
    
    def get_by_id(self, material_id: str) -> Optional[Material]:
        """Get a material by ID"""
        collection = self._get_collection()
        material_data = collection.get(material_id)
        if material_data:
            return Material.create_from_dict(material_data) if isinstance(material_data, dict) else material_data
        return None
    
    def get_by_material_number(self, material_number: str) -> Optional[Material]:
        """Get a material by material number"""
        return self.get_by_id(material_number)
    
    def list_all(self) -> List[Material]:
        """List all materials"""
        collection = self._get_collection()
        materials = collection.get_all()
        return [
            Material.create_from_dict(material) if isinstance(material, dict) else material
            for material in materials
        ]
    
    def create(self, material_data: MaterialCreate) -> Material:
        """Create a new material"""
        collection = self._get_collection()
        
        # Create material object
        material = Material.create_from_create_model(material_data)
        
        # Check if material number already exists
        if collection.get(material.material_number):
            from utils.error_utils import ConflictError
            raise ConflictError(f"Material with number {material.material_number} already exists")
        
        # Add to collection
        collection.add(material.material_number, material)
        self.state_manager.set_model(self.state_key, collection)
        
        return material
    
    def update(self, material_number: str, update_data: MaterialUpdate) -> Optional[Material]:
        """Update an existing material"""
        material = self.get_by_material_number(material_number)
        if not material:
            return None
        
        # Update material
        material.update_from_update_model(update_data)
        material.updated_at = datetime.now()  # Explicitly update the timestamp here as well
        
        # Update in collection
        collection = self._get_collection()
        collection.add(material.material_number, material)
        self.state_manager.set_model(self.state_key, collection)
        
        return material
    
    def delete(self, material_number: str) -> bool:
        """Delete a material"""
        collection = self._get_collection()
        if collection.remove(material_number):
            self.state_manager.set_model(self.state_key, collection)
            return True
        return False
    
    def count(self) -> int:
        """Count the number of materials"""
        collection = self._get_collection()
        return collection.count()
    
    def filter(self, **filters) -> List[Material]:
        """Filter materials based on criteria"""
        all_materials = self.list_all()
        results = []
        
        for material in all_materials:
            matches = True
            for field, value in filters.items():
                if not hasattr(material, field) or getattr(material, field) != value:
                    matches = False
                    break
            if matches:
                results.append(material)
        
        return results
