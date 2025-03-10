# tests/test_material_models.py
import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError
from models.material import (
    MaterialType, UnitOfMeasure, MaterialStatus,
    MaterialCreate, MaterialUpdate, Material, MaterialDataLayer
)
from models.common import EntityCollection
from services.state_manager import StateManager

class TestMaterialModels:
    def test_material_create_minimal(self):
        """Test creating a material with minimal fields"""
        material_data = MaterialCreate(
            name="Test Material"
        )
        
        assert material_data.name == "Test Material"
        assert material_data.material_number is None
        assert material_data.type == MaterialType.FINISHED
        assert material_data.base_unit == UnitOfMeasure.EACH
        assert material_data.status == MaterialStatus.ACTIVE
    
    def test_material_create_full(self):
        """Test creating a material with all fields"""
        material_data = MaterialCreate(
            material_number="MAT123",
            name="Test Material",
            description="A test material",
            type=MaterialType.RAW,
            base_unit=UnitOfMeasure.KILOGRAM,
            status=MaterialStatus.ACTIVE,
            weight=10.5,
            volume=5.2,
            dimensions={"length": 10, "width": 5, "height": 2}
        )
        
        assert material_data.material_number == "MAT123"
        assert material_data.name == "Test Material"
        assert material_data.description == "A test material"
        assert material_data.type == MaterialType.RAW
        assert material_data.base_unit == UnitOfMeasure.KILOGRAM
        assert material_data.status == MaterialStatus.ACTIVE
        assert material_data.weight == 10.5
        assert material_data.volume == 5.2
        assert material_data.dimensions == {"length": 10, "width": 5, "height": 2}
    
    def test_material_create_validation(self):
        """Test validation for material create"""
        # Test invalid material number
        with pytest.raises(PydanticValidationError):
            MaterialCreate(
                material_number="MAT 123",  # Space not allowed
                name="Test Material"
            )
        
        # Test empty name
        with pytest.raises(PydanticValidationError):
            MaterialCreate(
                name=""
            )
        
        # Test negative weight
        with pytest.raises(PydanticValidationError):
            MaterialCreate(
                name="Test Material",
                weight=-10
            )
    
    def test_material_update(self):
        """Test material update model"""
        update_data = MaterialUpdate(
            name="Updated Name",
            status=MaterialStatus.INACTIVE
        )
        
        assert update_data.name == "Updated Name"
        assert update_data.status == MaterialStatus.INACTIVE
        assert update_data.description is None
    
    def test_material_model(self):
        """Test main material model"""
        material = Material(
            id="MAT123",
            material_number="MAT123",
            name="Test Material",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert material.id == "MAT123"
        assert material.material_number == "MAT123"
        assert material.name == "Test Material"
        assert material.type == MaterialType.FINISHED
        assert material.status == MaterialStatus.ACTIVE
    
    def test_create_from_create_model(self):
        """Test creating material from create model"""
        create_data = MaterialCreate(
            name="Test Material",
            type=MaterialType.SERVICE,
            description="A test service"
        )
        
        material = Material.create_from_create_model(create_data, "MAT123")
        
        assert material.id == "MAT123"
        assert material.material_number == "MAT123"
        assert material.name == "Test Material"
        assert material.type == MaterialType.SERVICE
        assert material.description == "A test service"
    
    def test_create_from_create_model_autogen_id(self):
        """Test auto-generation of material number"""
        create_data = MaterialCreate(
            name="Test Material"
        )
        
        material = Material.create_from_create_model(create_data)
        
        assert material.id is not None
        assert material.material_number is not None
        assert material.material_number.startswith("MAT")
        assert len(material.material_number) > 3
        assert material.id == material.material_number
    
    def test_update_from_update_model(self):
        """Test updating material from update model"""
        material = Material(
            id="MAT123",
            material_number="MAT123",
            name="Original Name",
            description="Original description",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        update_data = MaterialUpdate(
            name="Updated Name",
            status=MaterialStatus.INACTIVE
        )
        
        material.update_from_update_model(update_data)
        
        assert material.name == "Updated Name"
        assert material.status == MaterialStatus.INACTIVE
        assert material.description == "Original description"  # Unchanged
        assert material.material_number == "MAT123"  # Unchanged

class TestMaterialDataLayer:
    def setup_method(self):
        """Set up a fresh state manager and data layer for each test"""
        self.state_manager = StateManager()
        self.data_layer = MaterialDataLayer(self.state_manager)
    
    def test_create_material(self):
        """Test creating a material through the data layer"""
        create_data = MaterialCreate(
            material_number="MAT001",
            name="Test Material"
        )
        
        material = self.data_layer.create(create_data)
        
        assert material.material_number == "MAT001"
        assert material.name == "Test Material"
        
        # Check it was added to state
        collection = self.state_manager.get_model(self.data_layer.state_key, EntityCollection)
        assert collection is not None
        assert collection.count() == 1
        assert collection.get("MAT001") is not None
    
    def test_get_material(self):
        """Test getting a material by ID"""
        # Create a material first
        create_data = MaterialCreate(
            material_number="MAT001",
            name="Test Material"
        )
        self.data_layer.create(create_data)
        
        # Get it back
        material = self.data_layer.get_by_id("MAT001")
        
        assert material is not None
        assert material.material_number == "MAT001"
        assert material.name == "Test Material"
    
    def test_list_materials(self):
        """Test listing all materials"""
        # Create a few materials
        self.data_layer.create(MaterialCreate(material_number="MAT001", name="Material 1"))
        self.data_layer.create(MaterialCreate(material_number="MAT002", name="Material 2"))
        self.data_layer.create(MaterialCreate(material_number="MAT003", name="Material 3"))
        
        # List them
        materials = self.data_layer.list_all()
        
        assert len(materials) == 3
        assert any(m.material_number == "MAT001" for m in materials)
        assert any(m.material_number == "MAT002" for m in materials)
        assert any(m.material_number == "MAT003" for m in materials)
    
    def test_update_material(self):
        """Test updating a material"""
        # Create a material first
        self.data_layer.create(MaterialCreate(
            material_number="MAT001",
            name="Original Name",
            description="Original description"
        ))
        
        # Update it
        update_data = MaterialUpdate(
            name="Updated Name",
            status=MaterialStatus.INACTIVE
        )
        
        updated = self.data_layer.update("MAT001", update_data)
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.status == MaterialStatus.INACTIVE
        assert updated.description == "Original description"  # Unchanged
        
        # Get it again to verify persistence
        material = self.data_layer.get_by_id("MAT001")
        assert material.name == "Updated Name"
        assert material.status == MaterialStatus.INACTIVE
    
    def test_delete_material(self):
        """Test deleting a material"""
        # Create a material first
        self.data_layer.create(MaterialCreate(material_number="MAT001", name="Material 1"))
        
        # Verify it exists
        assert self.data_layer.get_by_id("MAT001") is not None
        
        # Delete it
        result = self.data_layer.delete("MAT001")
        
        assert result is True
        assert self.data_layer.get_by_id("MAT001") is None
    
    def test_filter_materials(self):
        """Test filtering materials"""
        # Create some materials with different types
        self.data_layer.create(MaterialCreate(
            material_number="MAT001",
            name="Raw Material",
            type=MaterialType.RAW
        ))
        self.data_layer.create(MaterialCreate(
            material_number="MAT002",
            name="Finished Product",
            type=MaterialType.FINISHED
        ))
        self.data_layer.create(MaterialCreate(
            material_number="MAT003",
            name="Another Raw Material",
            type=MaterialType.RAW
        ))
        
        # Filter by type
        raw_materials = self.data_layer.filter(type=MaterialType.RAW)
        
        assert len(raw_materials) == 2
        assert all(m.type == MaterialType.RAW for m in raw_materials)
        
        # Filter by name containing a substring
        # This is more complex and not directly supported by the filter method,
        # but we can show how it would be done
        all_materials = self.data_layer.list_all()
        materials_with_raw = [m for m in all_materials if "Raw" in m.name]
        assert len(materials_with_raw) == 2
