# meta_routes.py

from enum import Enum
from typing import NamedTuple, List, Optional

#
# 1. Define an enum for HTTP methods
#
class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    # Add PUT, DELETE, PATCH if needed

#
# 2. Define a NamedTuple for route definitions
#
class RouteDefinition(NamedTuple):
    name: str
    path: str
    methods: List[HttpMethod]
    controller: str
    template: Optional[str] = None

#
# 3. ALL_ROUTES for the mini-meta harness
#    We'll have a root route (redirect) and a /dashboard route
#
ALL_ROUTES: List[RouteDefinition] = [
    RouteDefinition(
        name="root",
        path="/",
        methods=[HttpMethod.GET],
        controller="controllers.dashboard_controller.redirect_to_dashboard",
        template=None
    ),
    RouteDefinition(
        name="dashboard",
        path="/dashboard",
        methods=[HttpMethod.GET],
        controller="controllers.dashboard_controller.show_dashboard",
        template="dashboard.html"
    )
]
