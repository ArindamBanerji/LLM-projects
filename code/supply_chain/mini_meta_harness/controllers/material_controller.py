# controllers/material_controller.py
"""
Controller for Material UI and API endpoints.

This controller provides handlers for material operations including:
- Listing materials
- Getting material details
- Creating materials
- Updating materials
- Deprecating materials
"""

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from controllers import BaseController
from models.material import (
    MaterialCreate, MaterialUpdate, MaterialType, 
    MaterialStatus, UnitOfMeasure
)
from services import get_material_service, get_monitor_service
from services.url_service import url_service
from utils.error_utils import NotFoundError, ValidationError, BadRequestError

# Pydantic models for request validation

class MaterialSearchParams(BaseModel):
    """Parameters for material search and filtering"""
    search: Optional[str] = None
    type: Optional[MaterialType] = None
    status: Optional[MaterialStatus] = None
    limit: Optional[int] = Field(None, ge=1, le=100)
    offset: Optional[int] = Field(None, ge=0)

# UI Controller methods

async def list_materials(request: Request) -> Dict[str, Any]:
    """
    List materials with optional filtering (UI endpoint).
    
    Args:
        request: FastAPI request
        
    Returns:
        Template context dictionary
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Parse query parameters
        params = await BaseController.parse_query_params(request, MaterialSearchParams)
        
        # Get materials with filtering
        materials = material_service.list_materials(
            status=params.status,
            type=params.type,
            search_term=params.search
        )
        
        # Get material type options for the filter
        material_types = [t.value for t in MaterialType]
        material_statuses = [s.value for s in MaterialStatus]
        
        # Build template context
        context = {
            "materials": materials,
            "count": len(materials),
            "filters": {
                "search": params.search,
                "type": params.type.value if params.type else None,
                "status": params.status.value if params.status else None
            },
            "filter_options": {
                "types": material_types,
                "statuses": material_statuses
            },
            "title": "Materials"
        }
        
        return context
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="controller_error",
            message=f"Error in list_materials: {str(e)}",
            component="material_controller",
            context={"path": request.url.path, "query_params": str(request.query_params)}
        )
        raise

async def get_material(request: Request, material_id: str) -> Dict[str, Any]:
    """
    Get material details (UI endpoint).
    
    Args:
        request: FastAPI request
        material_id: Material ID or number
        
    Returns:
        Template context dictionary
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Get the material
        material = material_service.get_material(material_id)
        
        # Get related procurement information
        # In v1.6 we don't have the p2p_controller yet, so just prepare for future integration
        related_documents = {
            "requisitions": [],
            "orders": []
        }
        
        # Build template context
        context = {
            "material": material,
            "related_documents": related_documents,
            "title": f"Material: {material.name}"
        }
        
        return context
    except NotFoundError:
        # If material is not found, redirect to the materials list with an error message
        return BaseController.redirect_to_route(
            "material_list", 
            params={"error": f"Material {material_id} not found"}
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="controller_error",
            message=f"Error in get_material: {str(e)}",
            component="material_controller",
            context={"path": request.url.path, "material_id": material_id}
        )
        raise

async def create_material_form(request: Request) -> Dict[str, Any]:
    """
    Display the material creation form (UI endpoint).
    
    Args:
        request: FastAPI request
        
    Returns:
        Template context dictionary
    """
    # Get options for form dropdowns
    material_types = [t.value for t in MaterialType]
    units_of_measure = [u.value for u in UnitOfMeasure]
    
    # Build template context
    context = {
        "title": "Create Material",
        "form_action": url_service.get_url_for_route("material_create"),
        "form_method": "POST",
        "options": {
            "types": material_types,
            "units": units_of_measure,
            "statuses": [s.value for s in MaterialStatus]
        }
    }
    
    return context

async def create_material(request: Request) -> Dict[str, Any]:
    """
    Create a new material (UI endpoint).
    
    Args:
        request: FastAPI request
        
    Returns:
        Redirect to the new material or back to the form with errors
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Parse form data
        form_data = await request.form()
        
        # Build material creation data
        material_data = {
            "name": form_data.get("name"),
            "description": form_data.get("description"),
            "type": form_data.get("type"),
            "base_unit": form_data.get("base_unit"),
            "status": form_data.get("status", MaterialStatus.ACTIVE.value)
        }
        
        # Add optional numeric fields if provided
        if form_data.get("weight"):
            material_data["weight"] = float(form_data.get("weight"))
        if form_data.get("volume"):
            material_data["volume"] = float(form_data.get("volume"))
        
        # Create the material
        material_create = MaterialCreate(**material_data)
        material = material_service.create_material(material_create)
        
        # Redirect to the material detail page
        return BaseController.redirect_to_route(
            "material_detail", 
            params={"material_id": material.material_number},
            status_code=303  # See Other
        )
    except ValidationError as e:
        # Return to form with validation errors
        context = await create_material_form(request)
        context["errors"] = e.details
        context["form_data"] = dict(form_data)
        return context
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="controller_error",
            message=f"Error in create_material: {str(e)}",
            component="material_controller",
            context={"path": request.url.path}
        )
        raise

async def update_material_form(request: Request, material_id: str) -> Dict[str, Any]:
    """
    Display the material update form (UI endpoint).
    
    Args:
        request: FastAPI request
        material_id: Material ID or number
        
    Returns:
        Template context dictionary
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Get the material
        material = material_service.get_material(material_id)
        
        # Get options for form dropdowns
        material_types = [t.value for t in MaterialType]
        units_of_measure = [u.value for u in UnitOfMeasure]
        
        # Build template context
        context = {
            "title": f"Edit Material: {material.name}",
            "material": material,
            "form_action": url_service.get_url_for_route("material_update", {"material_id": material_id}),
            "form_method": "POST",
            "options": {
                "types": material_types,
                "units": units_of_measure,
                "statuses": [s.value for s in MaterialStatus]
            }
        }
        
        return context
    except NotFoundError:
        # If material is not found, redirect to the materials list with an error message
        return BaseController.redirect_to_route(
            "material_list", 
            params={"error": f"Material {material_id} not found"}
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="controller_error",
            message=f"Error in update_material_form: {str(e)}",
            component="material_controller",
            context={"path": request.url.path, "material_id": material_id}
        )
        raise

async def update_material(request: Request, material_id: str) -> Dict[str, Any]:
    """
    Update an existing material (UI endpoint).
    
    Args:
        request: FastAPI request
        material_id: Material ID or number
        
    Returns:
        Redirect to the material or back to the form with errors
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Parse form data
        form_data = await request.form()
        
        # Build material update data
        material_data = {}
        
        # Only include fields that were actually submitted
        if "name" in form_data:
            material_data["name"] = form_data.get("name")
        if "description" in form_data:
            material_data["description"] = form_data.get("description")
        if "type" in form_data:
            material_data["type"] = form_data.get("type")
        if "base_unit" in form_data:
            material_data["base_unit"] = form_data.get("base_unit")
        if "status" in form_data:
            material_data["status"] = form_data.get("status")
        if "weight" in form_data and form_data.get("weight"):
            material_data["weight"] = float(form_data.get("weight"))
        if "volume" in form_data and form_data.get("volume"):
            material_data["volume"] = float(form_data.get("volume"))
        
        # Update the material
        material_update = MaterialUpdate(**material_data)
        material = material_service.update_material(material_id, material_update)
        
        # Redirect to the material detail page
        return BaseController.redirect_to_route(
            "material_detail", 
            params={"material_id": material.material_number},
            status_code=303  # See Other
        )
    except ValidationError as e:
        # Return to form with validation errors
        context = await update_material_form(request, material_id)
        context["errors"] = e.details
        context["form_data"] = dict(form_data)
        return context
    except NotFoundError:
        # If material is not found, redirect to the materials list with an error message
        return BaseController.redirect_to_route(
            "material_list", 
            params={"error": f"Material {material_id} not found"}
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="controller_error",
            message=f"Error in update_material: {str(e)}",
            component="material_controller",
            context={"path": request.url.path, "material_id": material_id}
        )
        raise

async def deprecate_material(request: Request, material_id: str) -> Dict[str, Any]:
    """
    Deprecate a material (UI endpoint).
    
    Args:
        request: FastAPI request
        material_id: Material ID or number
        
    Returns:
        Redirect to the material or to the list with an error
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Deprecate the material
        material = material_service.deprecate_material(material_id)
        
        # Redirect to the material detail page
        return BaseController.redirect_to_route(
            "material_detail", 
            params={"material_id": material.material_number, "message": "Material has been deprecated"},
            status_code=303  # See Other
        )
    except ValidationError as e:
        # If validation fails, redirect with error
        return BaseController.redirect_to_route(
            "material_detail", 
            params={"material_id": material_id, "error": str(e)}
        )
    except NotFoundError:
        # If material is not found, redirect to the materials list with an error message
        return BaseController.redirect_to_route(
            "material_list", 
            params={"error": f"Material {material_id} not found"}
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="controller_error",
            message=f"Error in deprecate_material: {str(e)}",
            component="material_controller",
            context={"path": request.url.path, "material_id": material_id}
        )
        raise

# API Controller methods

async def api_list_materials(request: Request) -> JSONResponse:
    """
    List materials with optional filtering (API endpoint).
    
    Args:
        request: FastAPI request
        
    Returns:
        JSON response with materials data
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Parse query parameters
        params = await BaseController.parse_query_params(request, MaterialSearchParams)
        
        # Get materials with filtering
        materials = material_service.list_materials(
            status=params.status,
            type=params.type,
            search_term=params.search
        )
        
        # Convert to dictionaries for JSON response
        materials_data = [
            {
                "material_number": m.material_number,
                "name": m.name,
                "description": m.description,
                "type": m.type.value,
                "status": m.status.value,
                "created_at": m.created_at.isoformat(),
                "updated_at": m.updated_at.isoformat(),
                # Include other fields as needed
                "base_unit": m.base_unit.value,
                "weight": m.weight,
                "volume": m.volume
            }
            for m in materials
        ]
        
        # Build API response
        return BaseController.create_success_response(
            data={
                "materials": materials_data,
                "count": len(materials),
                "filters": {
                    "search": params.search,
                    "type": params.type.value if params.type else None,
                    "status": params.status.value if params.status else None
                }
            },
            message="Materials retrieved successfully"
        )
    except ValidationError as e:
        # Return validation error response
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "validation_error",
                "message": "Invalid query parameters",
                "details": e.details
            }
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="api_error",
            message=f"Error in api_list_materials: {str(e)}",
            component="material_controller",
            context={"path": request.url.path, "query_params": str(request.query_params)}
        )
        raise

async def api_get_material(request: Request, material_id: str) -> JSONResponse:
    """
    Get material details (API endpoint).
    
    Args:
        request: FastAPI request
        material_id: Material ID or number
        
    Returns:
        JSON response with material data
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Get the material
        material = material_service.get_material(material_id)
        
        # Convert to dictionary for JSON response
        material_data = {
            "material_number": material.material_number,
            "name": material.name,
            "description": material.description,
            "type": material.type.value,
            "status": material.status.value,
            "base_unit": material.base_unit.value,
            "weight": material.weight,
            "volume": material.volume,
            "dimensions": material.dimensions,
            "created_at": material.created_at.isoformat(),
            "updated_at": material.updated_at.isoformat()
        }
        
        # Build API response
        return BaseController.create_success_response(
            data={"material": material_data},
            message=f"Material {material_id} retrieved successfully"
        )
    except NotFoundError as e:
        # Return not found error response
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": "not_found",
                "message": str(e),
                "details": {"material_id": material_id}
            }
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="api_error",
            message=f"Error in api_get_material: {str(e)}",
            component="material_controller",
            context={"path": request.url.path, "material_id": material_id}
        )
        raise

async def api_create_material(request: Request) -> JSONResponse:
    """
    Create a new material (API endpoint).
    
    Args:
        request: FastAPI request
        
    Returns:
        JSON response with created material data
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Parse request body
        material_data = await BaseController.parse_json_body(request, MaterialCreate)
        
        # Create the material
        material = material_service.create_material(material_data)
        
        # Convert to dictionary for JSON response
        material_response = {
            "material_number": material.material_number,
            "name": material.name,
            "description": material.description,
            "type": material.type.value,
            "status": material.status.value,
            "created_at": material.created_at.isoformat()
        }
        
        # Build API response
        return BaseController.create_success_response(
            data={"material": material_response},
            message="Material created successfully",
            status_code=201  # Created
        )
    except ValidationError as e:
        # Return validation error response
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "validation_error",
                "message": "Invalid material data",
                "details": e.details
            }
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="api_error",
            message=f"Error in api_create_material: {str(e)}",
            component="material_controller",
            context={"path": request.url.path}
        )
        raise

async def api_update_material(request: Request, material_id: str) -> JSONResponse:
    """
    Update an existing material (API endpoint).
    
    Args:
        request: FastAPI request
        material_id: Material ID or number
        
    Returns:
        JSON response with updated material data
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Parse request body
        update_data = await BaseController.parse_json_body(request, MaterialUpdate)
        
        # Update the material
        material = material_service.update_material(material_id, update_data)
        
        # Convert to dictionary for JSON response
        material_response = {
            "material_number": material.material_number,
            "name": material.name,
            "description": material.description,
            "type": material.type.value,
            "status": material.status.value,
            "updated_at": material.updated_at.isoformat()
        }
        
        # Build API response
        return BaseController.create_success_response(
            data={"material": material_response},
            message=f"Material {material_id} updated successfully"
        )
    except NotFoundError as e:
        # Return not found error response
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": "not_found",
                "message": str(e),
                "details": {"material_id": material_id}
            }
        )
    except ValidationError as e:
        # Return validation error response
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "validation_error",
                "message": "Invalid update data",
                "details": e.details
            }
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="api_error",
            message=f"Error in api_update_material: {str(e)}",
            component="material_controller",
            context={"path": request.url.path, "material_id": material_id}
        )
        raise

async def api_deprecate_material(request: Request, material_id: str) -> JSONResponse:
    """
    Deprecate a material (API endpoint).
    
    Args:
        request: FastAPI request
        material_id: Material ID or number
        
    Returns:
        JSON response with deprecation result
    """
    material_service = get_material_service()
    monitor_service = get_monitor_service()
    
    try:
        # Deprecate the material
        material = material_service.deprecate_material(material_id)
        
        # Build API response
        return BaseController.create_success_response(
            data={
                "material_number": material.material_number,
                "status": material.status.value,
                "updated_at": material.updated_at.isoformat()
            },
            message=f"Material {material_id} has been deprecated"
        )
    except NotFoundError as e:
        # Return not found error response
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": "not_found",
                "message": str(e),
                "details": {"material_id": material_id}
            }
        )
    except ValidationError as e:
        # Return validation error response
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "validation_error",
                "message": str(e),
                "details": e.details if hasattr(e, 'details') else {}
            }
        )
    except Exception as e:
        # Log error
        monitor_service.log_error(
            error_type="api_error",
            message=f"Error in api_deprecate_material: {str(e)}",
            component="material_controller",
            context={"path": request.url.path, "material_id": material_id}
        )
        raise
