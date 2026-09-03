from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "revenue-recovery-orchestrator"
    random_seed: int = 42

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    data_dir: str = "data"
    artifacts_dir: str = "artifacts"
    active_dataset: str = "demo"
    models_dir: str = ""
    upload_max_bytes: int = 25_000_000

    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    agent_mode: str = "auto"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    llm_timeout_seconds: float = 90.0
    llm_max_retries: int = 1
    max_agent_iterations: int = 3

    @property
    def repo_root(self) -> Path:
        return REPO_ROOT

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def artifacts_path(self) -> Path:
        path = Path(self.artifacts_dir)
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def models_path(self) -> Path:
        if self.models_dir.strip():
            path = Path(self.models_dir)
            return path if path.is_absolute() else REPO_ROOT / path
        return self.artifacts_path / "models"

    @property
    def active_dataset_path(self) -> Path:
        name = Path(self.active_dataset)
        if name.is_absolute():
            return name
        return self.data_path / name

    @property
    def uploads_path(self) -> Path:
        return self.data_path / "uploads"

    @property
    def workflows_path(self) -> Path:
        return self.artifacts_path / "workflows"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
