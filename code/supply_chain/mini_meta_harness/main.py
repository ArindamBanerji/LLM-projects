# main.py
import importlib
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from meta_routes import ALL_ROUTES, HttpMethod, RouteDefinition
from services.template_service import TemplateService
from utils.error_utils import setup_exception_handlers

# Minimal FastAPI app
app = FastAPI(title="Mini-Meta SAP Harness", version="0.1")

# Set up error handlers
setup_exception_handlers(app)

# Create one instance of the TemplateService
template_service = TemplateService()

def get_controller_func(route: RouteDefinition):
    """
    Dynamically import the controller function from the string reference.
    e.g. "controllers.dashboard_controller.show_dashboard"
    """
    module_name, func_name = route.controller.rsplit(".", 1)
    mod = importlib.import_module(module_name)
    return getattr(mod, func_name)

# Register routes from ALL_ROUTES
for route_def in ALL_ROUTES:
    controller_func = get_controller_func(route_def)

    # This closure allows us to pass the route_def and controller_func
    async def endpoint(request: Request, handler=controller_func, rd=route_def):
        result = await handler(request)
        # If it's a dict and there's a template, render with TemplateService
        if isinstance(result, dict) and rd.template:
            return template_service.render_template(request, rd.template, result)
        # Otherwise, just return the result as-is (could be RedirectResponse, etc.)
        return result

    # For each route, register with the app
    # This minimal example only uses GET; add POST, etc. if you want more
    if HttpMethod.GET in route_def.methods:
        app.get(route_def.path, name=route_def.name)(endpoint)
    # If you had POST or others, you'd do something like:
    # if HttpMethod.POST in route_def.methods:
    #     app.post(route_def.path, name=route_def.name)(endpoint)

# Startup event to initialize services
@app.on_event("startup")
async def startup_event():
    """
    Initialize application services on startup.
    This ensures all services are properly initialized
    when the application starts.
    """
    print("Mini-meta harness started.")
    
    # Initialize services
    from services.material_service import material_service
    from services.p2p_service import p2p_service
    
    # Log services initialization
    print(f"Material service initialized: {material_service.__class__.__name__}")
    print(f"P2P service initialized: {p2p_service.__class__.__name__}")