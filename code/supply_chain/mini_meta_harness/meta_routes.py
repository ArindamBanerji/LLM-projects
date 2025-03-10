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
    ),
    # Error test routes (for manual testing of error handling)
    RouteDefinition(
        name="test_not_found",
        path="/test/not-found",
        methods=[HttpMethod.GET],
        controller="controllers.error_test_controller.test_not_found",
        template=None
    ),
    RouteDefinition(
        name="test_validation_error",
        path="/test/validation-error",
        methods=[HttpMethod.GET],
        controller="controllers.error_test_controller.test_validation_error",
        template=None
    ),
    RouteDefinition(
        name="test_bad_request",
        path="/test/bad-request",
        methods=[HttpMethod.GET],
        controller="controllers.error_test_controller.test_bad_request",
        template=None
    ),
    RouteDefinition(
        name="test_success_response",
        path="/test/success-response",
        methods=[HttpMethod.GET],
        controller="controllers.error_test_controller.test_success_response",
        template=None
    )
]
