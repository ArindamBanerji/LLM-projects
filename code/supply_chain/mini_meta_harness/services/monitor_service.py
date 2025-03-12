# services/monitor_service.py
"""
Monitoring service for the SAP Test Harness.

This service provides functionality for monitoring system health,
collecting performance metrics, and tracking errors.
"""

import os
import time
import platform
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from collections import deque
from services.state_manager import state_manager

class SystemMetrics:
    """
    System metrics data structure.
    """
    def __init__(self):
        self.timestamp: datetime = datetime.now()
        self.cpu_percent: float = 0.0
        self.memory_usage: float = 0.0
        self.available_memory: float = 0.0
        self.disk_usage: float = 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for storage"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_usage": self.memory_usage,
            "available_memory": self.available_memory,
            "disk_usage": self.disk_usage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemMetrics':
        """Create metrics from dictionary"""
        metrics = cls()
        metrics.timestamp = datetime.fromisoformat(data["timestamp"])
        metrics.cpu_percent = data["cpu_percent"]
        metrics.memory_usage = data["memory_usage"]
        metrics.available_memory = data["available_memory"]
        metrics.disk_usage = data["disk_usage"]
        return metrics

class ErrorLog:
    """
    Error log entry data structure.
    """
    def __init__(self, 
                 error_type: str, 
                 message: str, 
                 timestamp: Optional[datetime] = None,
                 component: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.error_type: str = error_type
        self.message: str = message
        self.timestamp: datetime = timestamp or datetime.now()
        self.component: Optional[str] = component
        self.context: Dict[str, Any] = context or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error log to dictionary for storage"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorLog':
        """Create error log from dictionary"""
        return cls(
            error_type=data["error_type"],
            message=data["message"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            component=data["component"],
            context=data["context"]
        )

class ComponentStatus:
    """
    Component status data structure.
    """
    def __init__(self, name: str):
        self.name: str = name
        self.status: str = "unknown"
        self.last_check: datetime = datetime.now()
        self.details: Dict[str, Any] = {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert component status to dictionary for storage"""
        return {
            "name": self.name,
            "status": self.status,
            "last_check": self.last_check.isoformat(),
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComponentStatus':
        """Create component status from dictionary"""
        status = cls(data["name"])
        status.status = data["status"]
        status.last_check = datetime.fromisoformat(data["last_check"])
        status.details = data["details"]
        return status

class MonitorService:
    """
    Service for monitoring system health and performance.
    Provides health checks, metrics collection, and error logging.
    """
    
    def __init__(self, state_manager_instance=None, metrics_max_age_hours=24, max_error_logs=1000):
        """
        Initialize the monitoring service.
        
        Args:
            state_manager_instance: Optional state manager for dependency injection
            metrics_max_age_hours: How many hours of metrics to keep
            max_error_logs: Maximum number of error logs to store
        """
        self.state_manager = state_manager_instance or state_manager
        self.metrics_max_age_hours = metrics_max_age_hours
        self.max_error_logs = max_error_logs
        self.metrics_key = "system_metrics"
        self.error_logs_key = "error_logs"
        self.component_status_key = "component_status"
        
        # Initialize state if needed
        self._initialize_state()
    
    def _initialize_state(self) -> None:
        """Initialize state if not already present"""
        if not self.state_manager.get(self.metrics_key):
            self.state_manager.set(self.metrics_key, [])
        
        if not self.state_manager.get(self.error_logs_key):
            self.state_manager.set(self.error_logs_key, [])
            
        if not self.state_manager.get(self.component_status_key):
            self.state_manager.set(self.component_status_key, {})
    
    # ===== Health Check Methods =====
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Perform a comprehensive system health check.
        
        Returns:
            Dictionary with health check results
        """
        start_time = time.time()
        
        # Check various components
        db_status = self.check_database_status()
        services_status = self.check_services_status()
        disk_status = self.check_disk_status()
        memory_status = self.check_memory_status()
        
        # Calculate overall status
        components = [db_status, services_status, disk_status, memory_status]
        if any(c["status"] == "error" for c in components):
            overall_status = "error"
        elif any(c["status"] == "warning" for c in components):
            overall_status = "warning"
        else:
            overall_status = "healthy"
            
        # Calculate response time
        response_time = time.time() - start_time
            
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "response_time_ms": round(response_time * 1000, 2),
            "components": {
                "database": db_status,
                "services": services_status,
                "disk": disk_status,
                "memory": memory_status
            },
            "system_info": self.get_system_info()
        }
    
    def check_database_status(self) -> Dict[str, Any]:
        """
        Check state manager database status.
        
        Returns:
            Status information dictionary
        """
        try:
            # For in-memory state manager, just check if it responds
            status = "healthy"
            state_keys = self.state_manager.get_all_keys()
            details = {
                "state_keys_count": len(state_keys),
                "required_keys_present": all(
                    key in state_keys 
                    for key in [self.metrics_key, self.error_logs_key, self.component_status_key]
                )
            }
            
            # Optionally check for persistent state
            if hasattr(self.state_manager, "_persistence_file"):
                details["persistence_enabled"] = True
                details["persistence_file"] = self.state_manager._persistence_file
                
                if self.state_manager._persistence_file:
                    details["persistence_file_exists"] = os.path.exists(self.state_manager._persistence_file)
            else:
                details["persistence_enabled"] = False
                
            return {
                "status": status,
                "details": details
            }
        except Exception as e:
            return {
                "status": "error",
                "details": {
                    "error": str(e)
                }
            }
    
    def check_services_status(self) -> Dict[str, Any]:
        """
        Check the status of registered services.
        
        Returns:
            Status information dictionary
        """
        try:
            from services import get_service, clear_service_registry
            
            services_status = {}
            
            # Try to get registered services
            try:
                material_service = get_service("material")
                services_status["material_service"] = "available"
            except Exception:
                services_status["material_service"] = "unavailable"
                
            try:
                p2p_service = get_service("p2p")
                services_status["p2p_service"] = "available"
            except Exception:
                services_status["p2p_service"] = "unavailable"
            
            # Get component status records
            component_status = self.state_manager.get(self.component_status_key, {})
            
            # Determine overall status
            if all(status == "available" for status in services_status.values()):
                status = "healthy"
            elif any(status == "available" for status in services_status.values()):
                status = "warning"
            else:
                status = "error"
                
            return {
                "status": status,
                "details": {
                    "services": services_status,
                    "components": component_status
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "details": {
                    "error": str(e)
                }
            }
    
    def check_disk_status(self) -> Dict[str, Any]:
        """
        Check disk space status.
        
        Returns:
            Status information dictionary
        """
        try:
            # Get disk usage for the current directory
            disk_usage = psutil.disk_usage('.')
            
            # Calculate percentages
            percent_used = disk_usage.percent
            percent_free = 100 - percent_used
            
            # Determine status based on free space
            if percent_free < 5:  # Critical
                status = "error"
            elif percent_free < 10:  # Warning
                status = "warning"
            else:  # Healthy
                status = "healthy"
                
            return {
                "status": status,
                "details": {
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "percent_used": round(percent_used, 1),
                    "percent_free": round(percent_free, 1)
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "details": {
                    "error": str(e)
                }
            }
    
    def check_memory_status(self) -> Dict[str, Any]:
        """
        Check system memory status.
        
        Returns:
            Status information dictionary
        """
        try:
            # Get memory information
            memory = psutil.virtual_memory()
            
            # Calculate percentages and values
            percent_used = memory.percent
            percent_available = 100 - percent_used
            
            # Determine status based on available memory
            if percent_available < 5:  # Critical
                status = "error"
            elif percent_available < 15:  # Warning
                status = "warning"
            else:  # Healthy
                status = "healthy"
                
            return {
                "status": status,
                "details": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent_used": round(percent_used, 1),
                    "percent_available": round(percent_available, 1)
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "details": {
                    "error": str(e)
                }
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get basic system information.
        
        Returns:
            Dictionary with system information
        """
        try:
            return {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(logical=True),
                "physical_cpu_count": psutil.cpu_count(logical=False)
            }
        except Exception as e:
            return {
                "error": str(e)
            }
    
    def update_component_status(self, component_name: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the status of a specific component.
        
        Args:
            component_name: Name of the component
            status: Status string (e.g., "healthy", "warning", "error")
            details: Additional details about the component status
        """
        # Get current component status
        component_status = self.state_manager.get(self.component_status_key, {})
        
        # Create or update the component status
        component = ComponentStatus(component_name)
        component.status = status
        component.last_check = datetime.now()
        component.details = details or {}
        
        # Store as dictionary
        component_status[component_name] = component.to_dict()
        
        # Update state
        self.state_manager.set(self.component_status_key, component_status)
    
    def get_component_status(self, component_name: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Get status information for one or all components.
        
        Args:
            component_name: Optional name of specific component
            
        Returns:
            Component status information
        """
        component_status = self.state_manager.get(self.component_status_key, {})
        
        if component_name:
            return component_status.get(component_name, {})
        
        return list(component_status.values())
    
    # ===== Metrics Collection Methods =====
    
    def collect_current_metrics(self) -> SystemMetrics:
        """
        Collect current system metrics.
        
        Returns:
            SystemMetrics instance with current metrics
        """
        metrics = SystemMetrics()
        
        # Collect CPU usage
        metrics.cpu_percent = psutil.cpu_percent(interval=0.5)
        
        # Collect memory usage
        memory = psutil.virtual_memory()
        metrics.memory_usage = memory.percent
        metrics.available_memory = memory.available / (1024**3)  # GB
        
        # Collect disk usage
        disk = psutil.disk_usage('.')
        metrics.disk_usage = disk.percent
        
        # Store metrics
        self._store_metrics(metrics)
        
        return metrics
    
    def _store_metrics(self, metrics: SystemMetrics) -> None:
        """
        Store metrics in state manager.
        
        Args:
            metrics: SystemMetrics to store
        """
        # Get current metrics
        current_metrics = self.state_manager.get(self.metrics_key, [])
        
        # Add new metrics
        current_metrics.append(metrics.to_dict())
        
        # Prune old metrics
        cutoff_time = datetime.now() - timedelta(hours=self.metrics_max_age_hours)
        current_metrics = [
            m for m in current_metrics 
            if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]
        
        # Save updated metrics
        self.state_manager.set(self.metrics_key, current_metrics)
    
    def get_metrics(self, hours: Optional[int] = None) -> List[SystemMetrics]:
        """
        Get system metrics for specified time period.
        
        Args:
            hours: Number of hours to look back (None for all available)
            
        Returns:
            List of SystemMetrics objects
        """
        # Get stored metrics
        stored_metrics = self.state_manager.get(self.metrics_key, [])
        
        # Filter by time if requested
        if hours is not None:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            stored_metrics = [
                m for m in stored_metrics 
                if datetime.fromisoformat(m["timestamp"]) > cutoff_time
            ]
        
        # Convert to SystemMetrics objects
        return [SystemMetrics.from_dict(m) for m in stored_metrics]
    
    def get_metrics_summary(self, hours: Optional[int] = None) -> Dict[str, Any]:
        """
        Get a summary of system metrics.
        
        Args:
            hours: Number of hours to look back (None for all available)
            
        Returns:
            Dictionary with metrics summary
        """
        metrics = self.get_metrics(hours)
        
        if not metrics:
            return {
                "count": 0,
                "time_period_hours": hours,
                "message": "No metrics available"
            }
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in metrics) / len(metrics)
        avg_memory = sum(m.memory_usage for m in metrics) / len(metrics)
        avg_disk = sum(m.disk_usage for m in metrics) / len(metrics)
        
        # Find maximum values
        max_cpu = max(m.cpu_percent for m in metrics)
        max_memory = max(m.memory_usage for m in metrics)
        max_disk = max(m.disk_usage for m in metrics)
        
        # Calculate time range
        oldest = min(m.timestamp for m in metrics)
        newest = max(m.timestamp for m in metrics)
        
        return {
            "count": len(metrics),
            "time_range": {
                "oldest": oldest.isoformat(),
                "newest": newest.isoformat(),
                "duration_hours": round((newest - oldest).total_seconds() / 3600, 2)
            },
            "averages": {
                "cpu_percent": round(avg_cpu, 1),
                "memory_usage_percent": round(avg_memory, 1),
                "disk_usage_percent": round(avg_disk, 1)
            },
            "maximums": {
                "cpu_percent": round(max_cpu, 1),
                "memory_usage_percent": round(max_memory, 1),
                "disk_usage_percent": round(max_disk, 1)
            },
            "current": metrics[-1].to_dict() if metrics else None
        }
    
    # ===== Error Logging Methods =====
    
    def log_error(self, 
                  error_type: str, 
                  message: str, 
                  component: Optional[str] = None,
                  context: Optional[Dict[str, Any]] = None) -> ErrorLog:
        """
        Log an error in the system.
        
        Args:
            error_type: Type of error (e.g., "validation", "database", "system")
            message: Error message
            component: Component where the error occurred
            context: Additional context information
            
        Returns:
            ErrorLog object that was created
        """
        # Create error log
        error_log = ErrorLog(
            error_type=error_type,
            message=message,
            component=component,
            context=context
        )
        
        # Store error log
        self._store_error_log(error_log)
        
        return error_log
    
    def _store_error_log(self, error_log: ErrorLog) -> None:
        """
        Store error log in state manager.
        
        Args:
            error_log: ErrorLog to store
        """
        # Get current error logs
        current_logs = self.state_manager.get(self.error_logs_key, [])
        
        # Add new log
        current_logs.append(error_log.to_dict())
        
        # Limit size of log history
        if len(current_logs) > self.max_error_logs:
            current_logs = current_logs[-self.max_error_logs:]
        
        # Save updated logs
        self.state_manager.set(self.error_logs_key, current_logs)
    
    def get_error_logs(self, 
                       error_type: Optional[str] = None, 
                       component: Optional[str] = None,
                       hours: Optional[int] = None,
                       limit: Optional[int] = None) -> List[ErrorLog]:
        """
        Get error logs with optional filtering.
        
        Args:
            error_type: Optional filter by error type
            component: Optional filter by component
            hours: Optional time limit in hours
            limit: Optional maximum number of logs to return
            
        Returns:
            List of ErrorLog objects
        """
        # Get stored logs
        stored_logs = self.state_manager.get(self.error_logs_key, [])
        
        # Filter by time if requested
        if hours is not None:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            stored_logs = [
                log for log in stored_logs 
                if datetime.fromisoformat(log["timestamp"]) > cutoff_time
            ]
        
        # Filter by error type if requested
        if error_type is not None:
            stored_logs = [log for log in stored_logs if log["error_type"] == error_type]
        
        # Filter by component if requested
        if component is not None:
            stored_logs = [log for log in stored_logs if log.get("component") == component]
        
        # Convert to ErrorLog objects
        error_logs = [ErrorLog.from_dict(log) for log in stored_logs]
        
        # Sort by timestamp (newest first)
        error_logs.sort(key=lambda log: log.timestamp, reverse=True)
        
        # Apply limit if requested
        if limit is not None and limit > 0:
            error_logs = error_logs[:limit]
        
        return error_logs
    
    def get_error_summary(self, hours: Optional[int] = None) -> Dict[str, Any]:
        """
        Get a summary of error logs.
        
        Args:
            hours: Optional time limit in hours
            
        Returns:
            Dictionary with error summary
        """
        logs = self.get_error_logs(hours=hours)
        
        if not logs:
            return {
                "count": 0,
                "time_period_hours": hours,
                "message": "No errors logged"
            }
        
        # Count errors by type
        error_types = {}
        for log in logs:
            error_types[log.error_type] = error_types.get(log.error_type, 0) + 1
        
        # Count errors by component
        components = {}
        for log in logs:
            if log.component:
                components[log.component] = components.get(log.component, 0) + 1
        
        # Calculate time range
        oldest = min(log.timestamp for log in logs)
        newest = max(log.timestamp for log in logs)
        
        return {
            "count": len(logs),
            "time_range": {
                "oldest": oldest.isoformat(),
                "newest": newest.isoformat(),
                "duration_hours": round((newest - oldest).total_seconds() / 3600, 2)
            },
            "by_type": error_types,
            "by_component": components,
            "recent": [log.to_dict() for log in logs[:5]]  # 5 most recent errors
        }
    
    def clear_error_logs(self) -> int:
        """
        Clear all error logs.
        
        Returns:
            Number of logs cleared
        """
        logs = self.state_manager.get(self.error_logs_key, [])
        count = len(logs)
        
        # Clear logs
        self.state_manager.set(self.error_logs_key, [])
        
        return count

# Create a singleton instance
monitor_service = MonitorService()
