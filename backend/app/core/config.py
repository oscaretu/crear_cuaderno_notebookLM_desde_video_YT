from pydantic_settings import BaseSettings
from pathlib import Path
import logging


class Settings(BaseSettings):
    app_name: str = "NotebookLM API"
    version: str = "1.0.0"

    # Rutas
    storage_state_path: Path = Path.home() / ".notebooklm" / "storage_state.json"

    # Configuración de notebooklm
    default_language: str = "es"
    default_timeout_fuente: float = 60.0
    default_retardo: float = 3.0

    # Debug
    debug: bool = False

    class Config:
        env_file = ".env"


def setup_logging(debug: bool = False):
    """Configura el nivel de logging según el parámetro debug"""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


settings = Settings()
