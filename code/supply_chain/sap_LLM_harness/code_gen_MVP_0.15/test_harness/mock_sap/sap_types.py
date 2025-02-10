"""
Core type definitions for SAP Simulator components.

This module provides standardized dataclasses for SAP API responses and errors,
serving as the foundation for the test harness MVP 0.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class SAPError:
    """
    Represents a standardized SAP error response.
    
    Attributes:
        code (str): Unique error code identifier (e.g., AUTH001, MAT001)
        message (str): Human-readable error description
        details (Optional[Dict[str, Any]]): Additional error context information
    """
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class SAPResponse:
    """
    Standardized wrapper for SAP API responses.
    
    This class provides a consistent structure for all API responses in the test harness.
    For successful operations, the 'data' field contains the response payload.
    For failed operations, the 'error' field contains error details.
    
    Attributes:
        success (bool): Indicates whether the operation was successful
        data (Optional[Dict[str, Any]]): Response payload for successful operations
        error (Optional[SAPError]): Error information for failed operations
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[SAPError] = None

    def __post_init__(self):
        """
        Validates response consistency after initialization.
        
        Ensures that successful responses have data but no error,
        and failed responses have an error but no data.
        """
        if self.success:
            if self.error is not None:
                raise ValueError("Successful response cannot have error information")
            if self.data is None:
                raise ValueError("Successful response must have data")
        else:
            if self.error is None:
                raise ValueError("Failed response must have error information")
            if self.data is not None:
                raise ValueError("Failed response cannot have data")

    @classmethod
    def success_response(cls, data: Dict[str, Any]) -> SAPResponse:
        """
        Creates a successful response with the given data.

        Args:
            data: Response payload

        Returns:
            SAPResponse: Successful response instance
        """
        return cls(success=True, data=data)

    @classmethod
    def error_response(cls, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> SAPResponse:
        """
        Creates an error response with the given error details.

        Args:
            code: Error code identifier
            message: Error description
            details: Optional additional error context

        Returns:
            SAPResponse: Error response instance
        """
        return cls(
            success=False, 
            error=SAPError(
                code=code,
                message=message,
                details=details
            )
        )