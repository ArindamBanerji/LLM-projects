# manual_tests/test_material.py
import os
import sys

# Add the parent directory to the path so Python can find the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.material import (
    Material, MaterialCreate, MaterialUpdate, MaterialDataLayer,
    MaterialType, UnitOfMeasure, MaterialStatus
)
from services.state_manager import state_manager

def run_material_tests():
    """Run manual tests for material data models"""
    
    # Create an instance of the data layer
    material_layer = MaterialDataLayer(state_manager)
    
    print("\n=== MATERIAL DATA MODEL MANUAL TESTS ===\n")

    try:
        # 1. Create a material with minimal information
        print("\n--- Test 1: Creating a minimal material ---")
        basic_material = material_layer.create(MaterialCreate(
            name="Basic Test Material"
        ))
        print(f"Created material: {basic_material.material_number}, {basic_material.name}")
        print(f"Status: {basic_material.status}, Type: {basic_material.type}")
        print(f"Created at: {basic_material.created_at}")
        
        # 2. Create a material with complete information
        print("\n--- Test 2: Creating a detailed material ---")
        detailed_material = material_layer.create(MaterialCreate(
            material_number="MAT002",
            name="Detailed Test Material",
            description="This material has all properties set",
            type=MaterialType.RAW,
            base_unit=UnitOfMeasure.KILOGRAM,
            weight=10.5,
            volume=5.2,
            dimensions={"length": 10, "width": 5, "height": 2}
        ))
        print(f"Created material: {detailed_material.material_number}, {detailed_material.name}")
        print(f"Status: {detailed_material.status}, Type: {detailed_material.type}")
        print(f"Description: {detailed_material.description}")
        print(f"Weight: {detailed_material.weight} {detailed_material.base_unit.value}")
        print(f"Dimensions: {detailed_material.dimensions}")
        
        # 3. List all materials
        print("\n--- Test 3: Listing all materials ---")
        all_materials = material_layer.list_all()
        print(f"Total materials: {len(all_materials)}")
        for material in all_materials:
            print(f"- {material.material_number}: {material.name} ({material.type})")
        
        # 4. Get material by ID
        print("\n--- Test 4: Getting material by ID ---")
        retrieved_material = material_layer.get_by_id("MAT002")
        if retrieved_material:
            print(f"Retrieved: {retrieved_material.name} ({retrieved_material.material_number})")
        else:
            print("Material not found")
        
        # 5. Update a material
        print("\n--- Test 5: Updating a material ---")
        update_result = material_layer.update("MAT002", MaterialUpdate(
            name="Updated Material Name",
            status=MaterialStatus.INACTIVE,
            description="This description has been updated"
        ))
        if update_result:
            print(f"Updated material: {update_result.name}")
            print(f"New status: {update_result.status}")
            print(f"New description: {update_result.description}")
            print(f"Updated at: {update_result.updated_at}")
        else:
            print("Update failed")
        
        # 6. Filter materials
        print("\n--- Test 6: Filtering materials ---")
        inactive_materials = material_layer.filter(status=MaterialStatus.INACTIVE)
        print(f"Found {len(inactive_materials)} inactive materials:")
        for mat in inactive_materials:
            print(f"- {mat.material_number}: {mat.name}")
        
        # 7. Test validation errors
        print("\n--- Test 7: Testing validation errors ---")
        try:
            # Try creating material with invalid material number
            material_layer.create(MaterialCreate(
                material_number="INVALID NUMBER",  # Spaces not allowed
                name="Invalid Material"
            ))
            print("ERROR: Validation should have failed for invalid material number")
        except Exception as e:
            print(f"Validation correctly failed: {str(e)}")
            
        try:
            # Try creating material with empty name
            material_layer.create(MaterialCreate(
                name=""  # Empty name not allowed
            ))
            print("ERROR: Validation should have failed for empty name")
        except Exception as e:
            print(f"Validation correctly failed: {str(e)}")
            
        try:
            # Try creating material with negative weight
            material_layer.create(MaterialCreate(
                name="Material with negative weight",
                weight=-5.0  # Negative weight not allowed
            ))
            print("ERROR: Validation should have failed for negative weight")
        except Exception as e:
            print(f"Validation correctly failed: {str(e)}")
        
        # 8. Delete a material
        print("\n--- Test 8: Deleting a material ---")
        delete_result = material_layer.delete("MAT002")
        print(f"Delete result: {delete_result}")
        
        # Count materials again
        all_materials = material_layer.list_all()
        print(f"Total materials after delete: {len(all_materials)}")
        
        print("\n=== MATERIAL TEST SUMMARY ===")
        print(f"Total materials in system: {material_layer.count()}")
        print("Material tests completed successfully!")
        
    except Exception as e:
        print(f"\nERROR: Test failed with exception: {str(e)}")
        raise

if __name__ == "__main__":
    run_material_tests()
