"""StatementIQ configuration loaded from .env"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Paths
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    poppler_path: str = r"C:\poppler-26.09.0\Library\bin"

    # Upload
    max_upload_mb: int = 25

    # Classification
    confidence_threshold: float = 0.75

    # Retention
    retention_enabled: bool = False

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Database
    database_url: str = "sqlite:///./statementiq.db"

    # Derived paths
    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def upload_dir(self) -> Path:
        p = self.base_dir.parent / "uploads"
        p.mkdir(exist_ok=True)
        return p

    @property
    def ml_models_dir(self) -> Path:
        p = self.base_dir / "ml" / "models"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def config_dir(self) -> Path:
        return self.base_dir / "config"

    @property
    def samples_dir(self) -> Path:
        p = self.base_dir / "samples"
        p.mkdir(exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

