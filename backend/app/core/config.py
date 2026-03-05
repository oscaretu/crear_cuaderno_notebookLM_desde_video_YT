from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "NotebookLM API"
    version: str = "1.0.0"

    # Rutas
    storage_state_path: Path = Path.home() / ".notebooklm" / "storage_state.json"

    # Configuración de notebooklm
    default_language: str = "es"
    default_timeout_fuente: float = 60.0
    default_retardo: float = 3.0

    class Config:
        env_file = ".env"


settings = Settings()
