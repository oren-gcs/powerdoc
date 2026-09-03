from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DocFlow"
    app_version: str = "2.0.0"
    environment: str = "local"
    debug: bool = True
    secret_key: str = "docflow-local-dev-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    refresh_token_expire_days: int = 14
    database_url: str = f"sqlite:///{ROOT / 'data' / 'docflow.db'}"
    storage_path: str = str(ROOT / "data" / "storage")
    skills_path: str = str(ROOT / "skills")
    automations_path: str = str(ROOT / "automations")
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_from: str = "DocFlow <noreply@docflow.local>"
    seed_demo: bool = True
    cloud_provider: str = "local"  # local | aws | gcp

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
