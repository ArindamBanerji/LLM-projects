# controllers/dashboard_controller.py

from fastapi import Request
from fastapi.responses import RedirectResponse
from typing import Dict, Any

async def show_dashboard(request: Request) -> Dict[str, Any]:
    """
    Renders a minimal dashboard
    """
    return {
        "welcome_message": "Welcome to the mini-meta harness!"
    }

async def redirect_to_dashboard(request: Request) -> RedirectResponse:
    """
    Redirects from root '/' to '/dashboard'
    """
    return RedirectResponse(url="/dashboard")
