# services/template_service.py
from fastapi import Request
from fastapi.templating import Jinja2Templates
from services.url_service import url_service

class TemplateService:
    """
    Minimal service to render Jinja2 templates
    """
    def __init__(self, templates_dir: str = "templates"):
        self.templates = Jinja2Templates(directory=templates_dir)
        
        # Add url_for function to templates
        self.templates.env.globals["url_for"] = self.url_for
        
    def url_for(self, name: str, **params):
        """
        Generate URL for a route by name, to be used in templates
        """
        return url_service.get_url_for_route(name, params if params else None)

    def render_template(self, request: Request, template_name: str, context: dict):
        return self.templates.TemplateResponse(
            template_name,
            {"request": request, **context}
        )