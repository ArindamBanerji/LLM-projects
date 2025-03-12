# meta_routes.py

from enum import Enum
from typing import NamedTuple, List, Optional

#
# 1. Define an enum for HTTP methods
#
class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

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
# 3. ALL_ROUTES for the v1.6 SAP Test Harness
#
ALL_ROUTES: List[RouteDefinition] = [
    # Dashboard routes
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
    
    # Material UI routes
    RouteDefinition(
        name="material_list",
        path="/materials",
        methods=[HttpMethod.GET],
        controller="controllers.material_controller.list_materials",
        template="material/list.html"
    ),
    RouteDefinition(
        name="material_detail",
        path="/materials/{material_id}",
        methods=[HttpMethod.GET],
        controller="controllers.material_controller.get_material",
        template="material/detail.html"
    ),
    RouteDefinition(
        name="material_create_form",
        path="/materials/create",
        methods=[HttpMethod.GET],
        controller="controllers.material_controller.create_material_form",
        template="material/create.html"
    ),
    RouteDefinition(
        name="material_create",
        path="/materials/create",
        methods=[HttpMethod.POST],
        controller="controllers.material_controller.create_material",
        template="material/create.html"
    ),
    RouteDefinition(
        name="material_update_form",
        path="/materials/{material_id}/edit",
        methods=[HttpMethod.GET],
        controller="controllers.material_controller.update_material_form",
        template="material/create.html"
    ),
    RouteDefinition(
        name="material_update",
        path="/materials/{material_id}/edit",
        methods=[HttpMethod.POST],
        controller="controllers.material_controller.update_material",
        template="material/create.html"
    ),
    RouteDefinition(
        name="material_deprecate",
        path="/materials/{material_id}/deprecate",
        methods=[HttpMethod.GET],
        controller="controllers.material_controller.deprecate_material",
        template=None
    ),
    
    # Material API routes
    RouteDefinition(
        name="api_material_list",
        path="/api/v1/materials",
        methods=[HttpMethod.GET],
        controller="controllers.material_controller.api_list_materials",
        template=None
    ),
    RouteDefinition(
        name="api_material_detail",
        path="/api/v1/materials/{material_id}",
        methods=[HttpMethod.GET],
        controller="controllers.material_controller.api_get_material",
        template=None
    ),
    RouteDefinition(
        name="api_material_create",
        path="/api/v1/materials",
        methods=[HttpMethod.POST],
        controller="controllers.material_controller.api_create_material",
        template=None
    ),
    RouteDefinition(
        name="api_material_update",
        path="/api/v1/materials/{material_id}",
        methods=[HttpMethod.PUT],
        controller="controllers.material_controller.api_update_material",
        template=None
    ),
    RouteDefinition(
        name="api_material_deprecate",
        path="/api/v1/materials/{material_id}/deprecate",
        methods=[HttpMethod.POST],
        controller="controllers.material_controller.api_deprecate_material",
        template=None
    ),
    
    # Monitor API routes
    RouteDefinition(
        name="api_monitor_health",
        path="/api/v1/monitor/health",
        methods=[HttpMethod.GET],
        controller="controllers.monitor_controller.api_health_check",
        template=None
    ),
    RouteDefinition(
        name="api_monitor_metrics",
        path="/api/v1/monitor/metrics",
        methods=[HttpMethod.GET],
        controller="controllers.monitor_controller.api_get_metrics",
        template=None
    ),
    RouteDefinition(
        name="api_monitor_errors",
        path="/api/v1/monitor/errors",
        methods=[HttpMethod.GET],
        controller="controllers.monitor_controller.api_get_errors",
        template=None
    ),
    RouteDefinition(
        name="api_monitor_collect_metrics",
        path="/api/v1/monitor/metrics/collect",
        methods=[HttpMethod.POST],
        controller="controllers.monitor_controller.api_collect_metrics",
        template=None
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
