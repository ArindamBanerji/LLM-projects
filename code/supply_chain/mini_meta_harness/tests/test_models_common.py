# tests/test_models_common.py
import pytest
from datetime import datetime, timedelta
from models.common import BaseDataModel, EntityCollection

class TestBaseDataModel:
    def test_init_with_defaults(self):
        """Test initialization with default values"""
        model = BaseDataModel()
        
        # ID should be None by default
        assert model.id is None
        
        # created_at should be set automatically
        assert isinstance(model.created_at, datetime)
        
        # updated_at should be set automatically now
        assert model.updated_at is not None
        assert isinstance(model.updated_at, datetime)
    
    def test_init_with_values(self):
        """Test initialization with provided values"""
        now = datetime.now()
        model = BaseDataModel(id="test-id", created_at=now)
        
        assert model.id == "test-id"
        assert model.created_at == now
    
    def test_update_method(self):
        """Test the update method"""
        model = BaseDataModel(id="test-id")
        original_created_at = model.created_at
        original_updated_at = model.updated_at
        
        # Sleep briefly to ensure updated_at will be different
        import time
        time.sleep(0.001)
        
        # Update the model
        model.update({"id": "new-id"})
        
        # Check that id was updated
        assert model.id == "new-id"
        
        # Check that created_at was not changed
        assert model.created_at == original_created_at
        
        # Check that updated_at was set to a newer time
        assert model.updated_at is not None
        assert model.updated_at > original_updated_at
    
    def test_update_ignores_nonexistent_fields(self):
        """Test that update ignores fields that don't exist in the model"""
        model = BaseDataModel(id="test-id")
        
        # Update with a non-existent field
        model.update({"nonexistent_field": "value"})
        
        # Check that the model doesn't have the field
        assert not hasattr(model, "nonexistent_field")

class TestEntityCollection:
    def test_init(self):
        """Test initialization"""
        collection = EntityCollection(name="test-collection")
        
        assert collection.name == "test-collection"
        assert collection.entities == {}
    
    def test_add_and_get(self):
        """Test adding and getting entities"""
        collection = EntityCollection(name="test-collection")
        entity = BaseDataModel(id="test-id")
        
        # Add the entity
        collection.add("test-id", entity)
        
        # Get the entity
        retrieved = collection.get("test-id")
        
        assert retrieved == entity
    
    def test_get_nonexistent(self):
        """Test getting a non-existent entity"""
        collection = EntityCollection(name="test-collection")
        
        # Get a non-existent entity
        retrieved = collection.get("nonexistent")
        
        assert retrieved is None
    
    def test_get_all(self):
        """Test getting all entities"""
        collection = EntityCollection(name="test-collection")
        entity1 = BaseDataModel(id="test-id-1")
        entity2 = BaseDataModel(id="test-id-2")
        
        # Add entities
        collection.add("test-id-1", entity1)
        collection.add("test-id-2", entity2)
        
        # Get all entities
        all_entities = collection.get_all()
        
        assert len(all_entities) == 2
        assert entity1 in all_entities
        assert entity2 in all_entities
    
    def test_remove(self):
        """Test removing an entity"""
        collection = EntityCollection(name="test-collection")
        entity = BaseDataModel(id="test-id")
        
        # Add the entity
        collection.add("test-id", entity)
        
        # Remove the entity
        result = collection.remove("test-id")
        
        assert result is True
        assert collection.get("test-id") is None
    
    def test_remove_nonexistent(self):
        """Test removing a non-existent entity"""
        collection = EntityCollection(name="test-collection")
        
        # Remove a non-existent entity
        result = collection.remove("nonexistent")
        
        assert result is False
    
    def test_count(self):
        """Test counting entities"""
        collection = EntityCollection(name="test-collection")
        
        # Initially empty
        assert collection.count() == 0
        
        # Add entities
        collection.add("test-id-1", BaseDataModel(id="test-id-1"))
        collection.add("test-id-2", BaseDataModel(id="test-id-2"))
        
        # Count should be 2
        assert collection.count() == 2
        
        # Remove an entity
        collection.remove("test-id-1")
        
        # Count should be 1
        assert collection.count() == 1
