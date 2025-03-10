# services/template_service.py
from fastapi import Request
from fastapi.templating import Jinja2Templates

class TemplateService:
    """
    Minimal service to render Jinja2 templates
    """
    def __init__(self, templates_dir: str = "templates"):
        self.templates = Jinja2Templates(directory=templates_dir)

    def render_template(self, request: Request, template_name: str, context: dict):
        return self.templates.TemplateResponse(
            template_name,
            {"request": request, **context}
        )
