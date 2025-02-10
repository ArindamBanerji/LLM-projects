"""
Test configuration for SAP test harness MVP 0.1.
Provides centralized configuration for test execution.
"""

from typing import Dict, Any

class TestConfig:
    """Test configuration settings"""
    
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
    
    # Default test PR data
    DEFAULT_PR_DATA = {
        'material_id': 'MAT001',
        'quantity': 100,
        'plant': 'PLANT_1'
    }
    
    # Default test PO data
    DEFAULT_PO_DATA = {
        'vendor_id': 'VENDOR001'
    }
    
    # Test execution settings
    EXECUTION_CONFIG = {
        'async_timeout': 30,  # seconds
        'cleanup_data': True,
        'verbose_logging': True
    }
    
    # Test suite configuration
    TEST_SUITE_CONFIG = {
        'parallel_execution': False,  # Keep sequential for MVP 0.1
        'fail_fast': False,
        'skip_slow_tests': False
    }
    
    @classmethod
    def get_test_config(cls) -> Dict[str, Any]:
        """Get complete test configuration"""
        return {
            'execution': cls.EXECUTION_CONFIG,
            'test_suite': cls.TEST_SUITE_CONFIG,
            'test_data': {
                'material': cls.DEFAULT_MATERIAL,
                'pr_data': cls.DEFAULT_PR_DATA,
                'po_data': cls.DEFAULT_PO_DATA
            }
        }