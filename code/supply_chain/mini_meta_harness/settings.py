# settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Mini Meta Harness"
    # Add other fields as needed, e.g. host, port, debug, etc.

settings = Settings()
