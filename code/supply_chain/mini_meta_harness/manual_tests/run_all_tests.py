# manual_tests/run_all_tests.py
"""
Manual test runner for v1.4 features.
This script runs all the manual tests in sequence to validate the new models.
"""
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def separator(title):
    """Print a section separator"""
    print("\n" + "="*80)
    print(f" {title} ".center(80, "="))
    print("="*80 + "\n")

def run_all_tests():
    """Run all manual tests"""
    separator("MANUAL TESTS FOR V1.4")
    
    print("Running tests for Material and P2P data models...")
    print("These tests verify the functionality of the data models and their data layers.")
    print("To run the tests individually, use:")
    print("  python manual_tests/test_material.py")
    print("  python manual_tests/test_p2p.py")
    
    # Import and run material tests
    separator("MATERIAL TESTS")
    from manual_tests.test_material import run_material_tests
    try:
        run_material_tests()
    except Exception as e:
        print(f"Material tests failed: {e}")
        return False
    
    # Import and run P2P tests
    separator("P2P TESTS")
    from manual_tests.test_p2p import run_p2p_tests
    try:
        run_p2p_tests()
    except Exception as e:
        print(f"P2P tests failed: {e}")
        return False
    
    # All tests passed
    separator("TEST RESULTS")
    print("✅ All manual tests passed successfully!")
    print("The Material and P2P data models are working as expected.")
    return True

if __name__ == "__main__":
    success = run_all_tests()
    if not success:
        sys.exit(1)
