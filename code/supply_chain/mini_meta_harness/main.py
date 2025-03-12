# main.py
import importlib
import logging
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from meta_routes import ALL_ROUTES, HttpMethod, RouteDefinition
from services.template_service import TemplateService
from utils.error_utils import setup_exception_handlers
from services import register_service, get_material_service, get_p2p_service, get_monitor_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sap_test_harness")

# Minimal FastAPI app
app = FastAPI(
    title="SAP Test Harness",
    description="Test API for SAP Integration",
    version="1.6.0"
)

# Set up error handlers
setup_exception_handlers(app)

# Add specific handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Request validation error: {str(exc)}")
    return await request_validation_exception_handler(request, exc)

# Create one instance of the TemplateService
template_service = TemplateService()

# Try to mount static files if directory exists
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {str(e)}")

def get_controller_func(route: RouteDefinition):
    """
    Dynamically import the controller function from the string reference.
    e.g. "controllers.dashboard_controller.show_dashboard"
    """
    module_name, func_name = route.controller.rsplit(".", 1)
    mod = importlib.import_module(module_name)
    return getattr(mod, func_name)

# Define endpoint factory function outside the loop
def create_endpoint_handler(handler, route_def):
    """
    Create an endpoint handler for a specific controller function and route definition.
    This ensures each route gets its own dedicated handler with properly bound values.
    
    Args:
        handler: The controller function to handle the request
        route_def: The route definition containing path, template, etc.
    
    Returns:
        An async function that can be used as a FastAPI endpoint handler
    """
    async def endpoint(request: Request):
        try:
            # Call the handler with the request object
            result = await handler(request)
            
            # If result is a dict and there's a template, render with TemplateService
            if isinstance(result, dict) and route_def.template:
                return template_service.render_template(request, route_def.template, result)
            
            # Otherwise, just return the result as-is
            return result
        except Exception as e:
            # Log the error but re-raise it to be handled by the global exception handlers
            logger.error(f"Error in endpoint {route_def.path}: {str(e)}")
            raise
    
    # Set function name and docstring for better debugging
    endpoint.__name__ = f"{route_def.name}_endpoint"
    endpoint.__doc__ = f"Endpoint handler for {route_def.path}"
    
    return endpoint

# Process each route definition
for route_def in ALL_ROUTES:
    # Get the controller function
    controller_func = get_controller_func(route_def)
    
    # Create endpoint handler with bound values for this specific route
    endpoint_handler = create_endpoint_handler(controller_func, route_def)
    
    # Register the endpoint with FastAPI based on HTTP method
    if HttpMethod.GET in route_def.methods:
        app.get(
            route_def.path, 
            name=route_def.name, 
            response_class=HTMLResponse if route_def.template else None
        )(endpoint_handler)
    
    if HttpMethod.POST in route_def.methods:
        app.post(
            route_def.path, 
            name=route_def.name
        )(endpoint_handler)
    
    # Add handlers for other HTTP methods
    if HttpMethod.PUT in route_def.methods:
        app.put(
            route_def.path, 
            name=route_def.name
        )(endpoint_handler)
    
    if HttpMethod.DELETE in route_def.methods:
        app.delete(
            route_def.path, 
            name=route_def.name
        )(endpoint_handler)
    
    if HttpMethod.PATCH in route_def.methods:
        app.patch(
            route_def.path,
            name=route_def.name
        )(endpoint_handler)

# Startup event to initialize services
@app.on_event("startup")
async def startup_event():
    """
    Initialize application services on startup.
    This ensures all services are properly initialized
    when the application starts.
    """
    logger.info("SAP Test Harness v1.6 starting...")
    
    try:
        # Initialize services
        material_service = get_material_service()
        p2p_service = get_p2p_service()
        monitor_service = get_monitor_service()
        
        # Register services in the service registry
        register_service("material", material_service)
        register_service("p2p", p2p_service)
        register_service("monitor", monitor_service)
        
        # Initialize monitoring by collecting initial metrics
        monitor_service.collect_current_metrics()
        
        # Log successful initialization
        logger.info(f"Material service initialized: {material_service.__class__.__name__}")
        logger.info(f"P2P service initialized: {p2p_service.__class__.__name__}")
        logger.info(f"Monitor service initialized: {monitor_service.__class__.__name__}")
        
        # Update component status in monitor service
        monitor_service.update_component_status("material_service", "healthy", {
            "class": material_service.__class__.__name__,
            "initialization_time": datetime.now().isoformat()
        })
        
        monitor_service.update_component_status("p2p_service", "healthy", {
            "class": p2p_service.__class__.__name__,
            "initialization_time": datetime.now().isoformat()
        })
        
        monitor_service.update_component_status("monitor_service", "healthy", {
            "class": monitor_service.__class__.__name__,
            "initialization_time": datetime.now().isoformat()
        })
        
        logger.info("SAP Test Harness started successfully")
    except Exception as e:
        logger.error(f"Error during service initialization: {str(e)}")
        # Re-raise the exception to prevent the application from starting with
        # improperly initialized services
        raise

# Shutdown event to clean up resources
@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources on application shutdown.
    """
    logger.info("SAP Test Harness shutting down...")
    
    try:
        # Get monitor service and log shutdown
        monitor_service = get_monitor_service()
        monitor_service.log_error(
            error_type="system",
            message="Application shutdown initiated",
            component="main",
            context={"event": "shutdown"}
        )
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    
    logger.info("SAP Test Harness shutdown complete")

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    uvicorn.run(app, host="0.0.0.0", port=8000)
