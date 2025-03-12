# controllers/monitor_controller.py
"""
Controller for Monitor API endpoints.

This controller provides handlers for system monitoring operations including:
- Health check
- Metrics collection and retrieval
- Error log access
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from controllers import BaseController
from services import get_monitor_service

# Pydantic models for request validation

class MetricsQueryParams(BaseModel):
    """Parameters for metrics queries"""
    hours: Optional[int] = Field(None, ge=1, le=168)  # Max 7 days

class ErrorsQueryParams(BaseModel):
    """Parameters for error log queries"""
    hours: Optional[int] = Field(None, ge=1, le=168)
    error_type: Optional[str] = None
    component: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)

# API Controller methods

async def api_health_check(request: Request) -> JSONResponse:
    """
    Check system health (API endpoint).
    
    Args:
        request: FastAPI request
        
    Returns:
        JSON response with health check results
    """
    monitor_service = get_monitor_service()
    
    try:
        # Perform health check
        health_data = monitor_service.check_system_health()
        
        # Determine response status code based on health status
        status_code = 200
        if health_data["status"] == "error":
            status_code = 503  # Service Unavailable
        elif health_data["status"] == "warning":
            status_code = 429  # Too Many Requests (we're using this for warnings)
        
        # Return health check results
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="controller_error",
            message=f"Error in api_health_check: {str(e)}",
            component="monitor_controller",
            context={"path": request.url.path}
        )
        
        # Return error response
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Failed to perform health check",
                "error": str(e)
            }
        )

async def api_get_metrics(request: Request) -> JSONResponse:
    """
    Get system metrics (API endpoint).
    
    Args:
        request: FastAPI request
        
    Returns:
        JSON response with metrics data
    """
    monitor_service = get_monitor_service()
    
    try:
        # Parse query parameters
        params = await BaseController.parse_query_params(request, MetricsQueryParams)
        
        # Get metrics summary
        metrics_summary = monitor_service.get_metrics_summary(hours=params.hours)
        
        # Return metrics data
        return BaseController.create_success_response(
            data=metrics_summary,
            message="System metrics retrieved successfully"
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="controller_error",
            message=f"Error in api_get_metrics: {str(e)}",
            component="monitor_controller",
            context={"path": request.url.path, "query_params": str(request.query_params)}
        )
        
        # Return error response
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "server_error",
                "message": f"Failed to retrieve metrics: {str(e)}"
            }
        )

async def api_get_errors(request: Request) -> JSONResponse:
    """
    Get error logs (API endpoint).
    
    Args:
        request: FastAPI request
        
    Returns:
        JSON response with error logs
    """
    monitor_service = get_monitor_service()
    
    try:
        # Parse query parameters
        params = await BaseController.parse_query_params(request, ErrorsQueryParams)
        
        # Get error logs with filters
        if params.error_type or params.component or params.limit:
            # Use individual parameters for filtering
            error_logs = monitor_service.get_error_logs(
                error_type=params.error_type,
                component=params.component,
                hours=params.hours,
                limit=params.limit
            )
            
            # Convert to dictionaries for JSON response
            errors_data = [log.to_dict() for log in error_logs]
            
            # Return error logs
            return BaseController.create_success_response(
                data={
                    "errors": errors_data,
                    "count": len(errors_data),
                    "filters": {
                        "error_type": params.error_type,
                        "component": params.component,
                        "hours": params.hours,
                        "limit": params.limit
                    }
                },
                message="Error logs retrieved successfully"
            )
        else:
            # Get error summary
            error_summary = monitor_service.get_error_summary(hours=params.hours)
            
            # Return error summary
            return BaseController.create_success_response(
                data=error_summary,
                message="Error summary retrieved successfully"
            )
    except Exception as e:
        # Log error (but don't cause an infinite loop if this fails)
        try:
            monitor_service.log_error(
                error_type="controller_error",
                message=f"Error in api_get_errors: {str(e)}",
                component="monitor_controller",
                context={"path": request.url.path, "query_params": str(request.query_params)}
            )
        except:
            pass  # If logging fails, continue anyway
        
        # Return error response
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "server_error",
                "message": f"Failed to retrieve error logs: {str(e)}"
            }
        )

async def api_collect_metrics(request: Request) -> JSONResponse:
    """
    Collect current system metrics (API endpoint).
    
    Args:
        request: FastAPI request
        
    Returns:
        JSON response with collected metrics
    """
    monitor_service = get_monitor_service()
    
    try:
        # Collect current metrics
        metrics = monitor_service.collect_current_metrics()
        
        # Return metrics data
        return BaseController.create_success_response(
            data={
                "timestamp": metrics.timestamp.isoformat(),
                "cpu_percent": metrics.cpu_percent,
                "memory_usage": metrics.memory_usage,
                "available_memory": metrics.available_memory,
                "disk_usage": metrics.disk_usage
            },
            message="Metrics collected successfully"
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="controller_error",
            message=f"Error in api_collect_metrics: {str(e)}",
            component="monitor_controller",
            context={"path": request.url.path}
        )
        
        # Return error response
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "server_error",
                "message": f"Failed to collect metrics: {str(e)}"
            }
        )
