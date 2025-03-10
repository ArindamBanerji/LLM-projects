# controllers/dashboard_controller.py
from fastapi import Request
from fastapi.responses import RedirectResponse
from typing import Dict, Any
from services.state_manager import state_manager
from controllers import BaseController
from datetime import datetime

async def show_dashboard(request: Request) -> Dict[str, Any]:
    """
    Renders a minimal dashboard with visit counter
    """
    # Get current visit count from state and increment
    visit_count = state_manager.get("dashboard_visits", 0)
    visit_count += 1
    state_manager.set("dashboard_visits", visit_count)
    
    # Get last visit time
    last_visit = state_manager.get("last_dashboard_visit", "First visit")
    
    # Set current visit time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state_manager.set("last_dashboard_visit", current_time)
    
    return {
        "welcome_message": "Welcome to the mini-meta harness!",
        "visit_count": visit_count,
        "last_visit": last_visit,
        "current_time": current_time
    }

async def redirect_to_dashboard(request: Request) -> RedirectResponse:
    """
    Redirects from root '/' to '/dashboard'
    """
    # Use BaseController's redirect method
    return BaseController.redirect_to_route("dashboard")
