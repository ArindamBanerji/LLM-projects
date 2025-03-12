# tests/test_monitor_service.py
"""
Tests for the Monitor Service.

This module contains tests for the MonitorService component, including
health checks, metrics collection, and error logging.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from services.monitor_service import (
    MonitorService, SystemMetrics, ErrorLog, ComponentStatus
)
from services.state_manager import StateManager

class TestMonitorService:
    def setup_method(self):
        """Set up a fresh state manager and monitor service for each test"""
        self.state_manager = StateManager()
        self.monitor_service = MonitorService(self.state_manager)
    
    # ===== Data Structure Tests =====
    
    def test_system_metrics_structure(self):
        """Test SystemMetrics data structure"""
        # Create metrics
        metrics = SystemMetrics()
        metrics.cpu_percent = 50.5
        metrics.memory_usage = 75.2
        metrics.available_memory = 4.5
        metrics.disk_usage = 80.0
        
        # Convert to dict
        metrics_dict = metrics.to_dict()
        
        # Check dictionary contents
        assert "timestamp" in metrics_dict
        assert metrics_dict["cpu_percent"] == 50.5
        assert metrics_dict["memory_usage"] == 75.2
        assert metrics_dict["available_memory"] == 4.5
        assert metrics_dict["disk_usage"] == 80.0
        
        # Test from_dict method
        reconstructed = SystemMetrics.from_dict(metrics_dict)
        assert reconstructed.cpu_percent == metrics.cpu_percent
        assert reconstructed.memory_usage == metrics.memory_usage
        assert reconstructed.available_memory == metrics.available_memory
        assert reconstructed.disk_usage == metrics.disk_usage
    
    def test_error_log_structure(self):
        """Test ErrorLog data structure"""
        # Create error log
        error = ErrorLog(
            error_type="test_error",
            message="Test error message",
            component="test_component",
            context={"key": "value"}
        )
        
        # Convert to dict
        error_dict = error.to_dict()
        
        # Check dictionary contents
        assert error_dict["error_type"] == "test_error"
        assert error_dict["message"] == "Test error message"
        assert error_dict["component"] == "test_component"
        assert error_dict["context"] == {"key": "value"}
        assert "timestamp" in error_dict
        
        # Test from_dict method
        reconstructed = ErrorLog.from_dict(error_dict)
        assert reconstructed.error_type == error.error_type
        assert reconstructed.message == error.message
        assert reconstructed.component == error.component
        assert reconstructed.context == error.context
    
    def test_component_status_structure(self):
        """Test ComponentStatus data structure"""
        # Create component status
        status = ComponentStatus("test_component")
        status.status = "healthy"
        status.details = {"version": "1.0"}
        
        # Convert to dict
        status_dict = status.to_dict()
        
        # Check dictionary contents
        assert status_dict["name"] == "test_component"
        assert status_dict["status"] == "healthy"
        assert status_dict["details"] == {"version": "1.0"}
        assert "last_check" in status_dict
        
        # Test from_dict method
        reconstructed = ComponentStatus.from_dict(status_dict)
        assert reconstructed.name == status.name
        assert reconstructed.status == status.status
        assert reconstructed.details == status.details
    
    # ===== Health Check Tests =====
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_check_system_health(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test the comprehensive system health check"""
        # Configure mocks
        mock_cpu_percent.return_value = 50.0
        
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_memory.total = 16 * 1024**3  # 16 GB
        mock_memory.available = 6 * 1024**3  # 6 GB
        mock_memory.used = 10 * 1024**3  # 10 GB
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 70.0
        mock_disk.total = 500 * 1024**3  # 500 GB
        mock_disk.used = 350 * 1024**3  # 350 GB
        mock_disk.free = 150 * 1024**3  # 150 GB
        mock_disk_usage.return_value = mock_disk
        
        # Perform health check
        health_data = self.monitor_service.check_system_health()
        
        # Verify health data structure
        assert "status" in health_data
        assert "timestamp" in health_data
        assert "response_time_ms" in health_data
        assert "components" in health_data
        assert "system_info" in health_data
        
        # Verify components
        components = health_data["components"]
        assert "database" in components
        assert "services" in components
        assert "disk" in components
        assert "memory" in components
        
        # Verify statuses
        assert components["disk"]["status"] == "healthy"  # 70% disk usage is OK
        assert components["memory"]["status"] == "healthy"  # 60% memory usage is OK
    
    def test_check_database_status(self):
        """Test database status check"""
        # Check database status
        db_status = self.monitor_service.check_database_status()
        
        # Verify structure
        assert "status" in db_status
        assert "details" in db_status
        
        # Verify details
        assert "state_keys_count" in db_status["details"]
        assert "required_keys_present" in db_status["details"]
    
    @patch('psutil.disk_usage')
    def test_check_disk_status(self, mock_disk_usage):
        """Test disk status check with various conditions"""
        # Test healthy disk (10% used)
        mock_disk = MagicMock()
        mock_disk.percent = 10.0
        mock_disk.total = 100 * 1024**3
        mock_disk.used = 10 * 1024**3
        mock_disk.free = 90 * 1024**3
        mock_disk_usage.return_value = mock_disk
        
        status = self.monitor_service.check_disk_status()
        assert status["status"] == "healthy"
        
        # Test warning disk (93% used)
        mock_disk.percent = 93.0
        mock_disk.free = 7 * 1024**3
        mock_disk.used = 93 * 1024**3
        
        status = self.monitor_service.check_disk_status()
        assert status["status"] == "warning"
        
        # Test error disk (97% used)
        mock_disk.percent = 97.0
        mock_disk.free = 3 * 1024**3
        mock_disk.used = 97 * 1024**3
        
        status = self.monitor_service.check_disk_status()
        assert status["status"] == "error"
    
    @patch('psutil.virtual_memory')
    def test_check_memory_status(self, mock_virtual_memory):
        """Test memory status check with various conditions"""
        # Test healthy memory (50% used)
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.total = 16 * 1024**3
        mock_memory.available = 8 * 1024**3
        mock_memory.used = 8 * 1024**3
        mock_virtual_memory.return_value = mock_memory
        
        status = self.monitor_service.check_memory_status()
        assert status["status"] == "healthy"
        
        # Test warning memory (90% used)
        mock_memory.percent = 90.0
        mock_memory.available = 1.6 * 1024**3
        mock_memory.used = 14.4 * 1024**3
        
        status = self.monitor_service.check_memory_status()
        assert status["status"] == "warning"
        
        # Test error memory (97% used)
        mock_memory.percent = 97.0
        mock_memory.available = 0.48 * 1024**3
        mock_memory.used = 15.52 * 1024**3
        
        status = self.monitor_service.check_memory_status()
        assert status["status"] == "error"
    
    def test_get_system_info(self):
        """Test getting system information"""
        # Get system info
        system_info = self.monitor_service.get_system_info()
        
        # Verify structure
        assert "platform" in system_info
        assert "platform_release" in system_info
        assert "platform_version" in system_info
        assert "architecture" in system_info
        assert "processor" in system_info
        assert "python_version" in system_info
        assert "cpu_count" in system_info
    
    def test_update_component_status(self):
        """Test updating component status"""
        # Update component status
        self.monitor_service.update_component_status(
            "test_component",
            "healthy",
            {"version": "1.0", "uptime": 3600}
        )
        
        # Get updated status
        status = self.monitor_service.get_component_status("test_component")
        
        # Verify status was updated
        assert status["name"] == "test_component"
        assert status["status"] == "healthy"
        assert status["details"]["version"] == "1.0"
        assert status["details"]["uptime"] == 3600
    
    # ===== Metrics Collection Tests =====
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_collect_current_metrics(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test collecting current system metrics"""
        # Configure mocks
        mock_cpu_percent.return_value = 40.0
        
        mock_memory = MagicMock()
        mock_memory.percent = 55.0
        mock_memory.available = 7.2 * 1024**3
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 65.0
        mock_disk_usage.return_value = mock_disk
        
        # Collect metrics
        metrics = self.monitor_service.collect_current_metrics()
        
        # Verify metrics
        assert metrics.cpu_percent == 40.0
        assert metrics.memory_usage == 55.0
        assert metrics.available_memory == 7.2
        assert metrics.disk_usage == 65.0
        
        # Verify metrics are stored in state
        stored_metrics = self.state_manager.get("system_metrics")
        assert stored_metrics is not None
        assert len(stored_metrics) == 1
    
    def test_get_metrics(self):
        """Test retrieving stored metrics"""
        # Add some test metrics to state
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        two_hours_ago = now - timedelta(hours=2)
        
        metrics_data = [
            {
                "timestamp": two_hours_ago.isoformat(),
                "cpu_percent": 30.0,
                "memory_usage": 40.0,
                "available_memory": 9.6,
                "disk_usage": 60.0
            },
            {
                "timestamp": one_hour_ago.isoformat(),
                "cpu_percent": 50.0,
                "memory_usage": 60.0,
                "available_memory": 6.4,
                "disk_usage": 70.0
            },
            {
                "timestamp": now.isoformat(),
                "cpu_percent": 70.0,
                "memory_usage": 80.0,
                "available_memory": 3.2,
                "disk_usage": 80.0
            }
        ]
        
        self.state_manager.set("system_metrics", metrics_data)
        
        # Get all metrics
        all_metrics = self.monitor_service.get_metrics()
        assert len(all_metrics) == 3
        
        # Get metrics for last hour
        recent_metrics = self.monitor_service.get_metrics(hours=1)
        assert len(recent_metrics) == 2
        assert recent_metrics[0].timestamp >= one_hour_ago
        assert recent_metrics[1].timestamp >= one_hour_ago
    
    def test_get_metrics_summary(self):
        """Test getting metrics summary"""
        # Add some test metrics to state
        now = datetime.now()
        metrics_data = [
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "cpu_percent": 30.0,
                "memory_usage": 40.0,
                "available_memory": 9.6,
                "disk_usage": 60.0
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "cpu_percent": 50.0,
                "memory_usage": 60.0,
                "available_memory": 6.4,
                "disk_usage": 70.0
            },
            {
                "timestamp": now.isoformat(),
                "cpu_percent": 70.0,
                "memory_usage": 80.0,
                "available_memory": 3.2,
                "disk_usage": 80.0
            }
        ]
        
        self.state_manager.set("system_metrics", metrics_data)
        
        # Get metrics summary
        summary = self.monitor_service.get_metrics_summary()
        
        # Verify summary structure
        assert "count" in summary
        assert "time_range" in summary
        assert "averages" in summary
        assert "maximums" in summary
        assert "current" in summary
        
        # Verify summary data
        assert summary["count"] == 3
        assert summary["averages"]["cpu_percent"] == 50.0  # (30 + 50 + 70) / 3
        assert summary["averages"]["memory_usage_percent"] == 60.0  # (40 + 60 + 80) / 3
        assert summary["averages"]["disk_usage_percent"] == 70.0  # (60 + 70 + 80) / 3
        
        assert summary["maximums"]["cpu_percent"] == 70.0
        assert summary["maximums"]["memory_usage_percent"] == 80.0
        assert summary["maximums"]["disk_usage_percent"] == 80.0
    
    # ===== Error Logging Tests =====
    
    def test_log_error(self):
        """Test logging an error"""
        # Log an error
        error = self.monitor_service.log_error(
            error_type="test_error",
            message="Test error message",
            component="test_component",
            context={"key": "value"}
        )
        
        # Verify error properties
        assert error.error_type == "test_error"
        assert error.message == "Test error message"
        assert error.component == "test_component"
        assert error.context == {"key": "value"}
        
        # Verify error was stored in state
        stored_errors = self.state_manager.get("error_logs")
        assert stored_errors is not None
        assert len(stored_errors) == 1
        
        # Verify error was stored correctly
        stored_error = stored_errors[0]
        assert stored_error["error_type"] == "test_error"
        assert stored_error["message"] == "Test error message"
        assert stored_error["component"] == "test_component"
        assert stored_error["context"] == {"key": "value"}
    
    def test_get_error_logs(self):
        """Test retrieving error logs with filtering"""
        # Add some test error logs to state
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        two_hours_ago = now - timedelta(hours=2)
        
        error_logs = [
            {
                "error_type": "type_a",
                "message": "Error A1",
                "component": "component_a",
                "timestamp": two_hours_ago.isoformat(),
                "context": {}
            },
            {
                "error_type": "type_b",
                "message": "Error B1",
                "component": "component_b",
                "timestamp": one_hour_ago.isoformat(),
                "context": {}
            },
            {
                "error_type": "type_a",
                "message": "Error A2",
                "component": "component_c",
                "timestamp": now.isoformat(),
                "context": {}
            }
        ]
        
        self.state_manager.set("error_logs", error_logs)
        
        # Get all error logs
        all_errors = self.monitor_service.get_error_logs()
        assert len(all_errors) == 3
        
        # Filter by error type
        type_a_errors = self.monitor_service.get_error_logs(error_type="type_a")
        assert len(type_a_errors) == 2
        assert all(e.error_type == "type_a" for e in type_a_errors)
        
        # Filter by component
        component_b_errors = self.monitor_service.get_error_logs(component="component_b")
        assert len(component_b_errors) == 1
        assert component_b_errors[0].component == "component_b"
        
        # Filter by time
        recent_errors = self.monitor_service.get_error_logs(hours=1)
        assert len(recent_errors) == 2
        assert all(e.timestamp >= one_hour_ago for e in recent_errors)
        
        # Filter with limit
        limited_errors = self.monitor_service.get_error_logs(limit=2)
        assert len(limited_errors) == 2
    
    def test_get_error_summary(self):
        """Test getting error summary"""
        # Add some test error logs to state
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        two_hours_ago = now - timedelta(hours=2)
        
        error_logs = [
            {
                "error_type": "type_a",
                "message": "Error A1",
                "component": "component_a",
                "timestamp": two_hours_ago.isoformat(),
                "context": {}
            },
            {
                "error_type": "type_b",
                "message": "Error B1",
                "component": "component_b",
                "timestamp": one_hour_ago.isoformat(),
                "context": {}
            },
            {
                "error_type": "type_a",
                "message": "Error A2",
                "component": "component_c",
                "timestamp": now.isoformat(),
                "context": {}
            }
        ]
        
        self.state_manager.set("error_logs", error_logs)
        
        # Get error summary
        summary = self.monitor_service.get_error_summary()
        
        # Verify summary structure
        assert "count" in summary
        assert "time_range" in summary
        assert "by_type" in summary
        assert "by_component" in summary
        assert "recent" in summary
        
        # Verify summary data
        assert summary["count"] == 3
        assert summary["by_type"] == {"type_a": 2, "type_b": 1}
        assert summary["by_component"] == {"component_a": 1, "component_b": 1, "component_c": 1}
        assert len(summary["recent"]) > 0
    
    def test_clear_error_logs(self):
        """Test clearing error logs"""
        # Add some test error logs to state
        error_logs = [
            {
                "error_type": "type_a",
                "message": "Error A",
                "component": "component_a",
                "timestamp": datetime.now().isoformat(),
                "context": {}
            },
            {
                "error_type": "type_b",
                "message": "Error B",
                "component": "component_b",
                "timestamp": datetime.now().isoformat(),
                "context": {}
            }
        ]
        
        self.state_manager.set("error_logs", error_logs)
        
        # Verify logs are present
        assert len(self.monitor_service.get_error_logs()) == 2
        
        # Clear logs
        count = self.monitor_service.clear_error_logs()
        
        # Verify logs were cleared
        assert count == 2
        assert len(self.monitor_service.get_error_logs()) == 0
    
    def test_max_error_logs_limit(self):
        """Test that error logs are limited to max_error_logs"""
        # Create a monitor service with a small limit
        monitor_service = MonitorService(self.state_manager, max_error_logs=3)
        
        # Log more errors than the limit
        for i in range(5):
            monitor_service.log_error(
                error_type="test_error",
                message=f"Test error {i}"
            )
        
        # Verify only the most recent logs are kept
        logs = monitor_service.get_error_logs()
        assert len(logs) == 3
        
        # Verify we have the most recent logs (2, 3, 4)
        messages = [log.message for log in logs]
        assert "Test error 2" in messages
        assert "Test error 3" in messages
        assert "Test error 4" in messages
