"""Application settings, read once from the environment (and .env in development)."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from psycopg.conninfo import make_conninfo
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str  # without a password, e.g. postgresql://nyaya@127.0.0.1:5432/nyaya
    postgres_password: str = ""  # kept out of the URL so no credential sits in a connection string

    # Language model (any OpenAI-compatible endpoint: Groq in production, Ollama locally)
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "qwen2.5:7b"
    llm_api_key: str = ""
    llm_daily_cap: int = 500
    llm_timeout_seconds: float = 60.0
    llm_context_tokens: int = 8000

    # Models
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    model_device: str = "auto"
    reranker_backend: str = "torch"  # torch | onnx-int8
    rerank_depth: int = 50  # 0 disables reranking
    rerank_max_tokens: int = 512
    embed_max_tokens: int = 512  # longer paragraphs are truncated for the vector; BM25 still sees all text
    models_dir: Path = Path("./models")

    # Search and grounding thresholds (reranker scores are in 0..1)
    relevance_threshold: float = 0.05
    support_threshold: float = 0.1
    result_limit: int = 10
    candidate_limit: int = 100

    # API
    port: int = 8000
    allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000"])
    rate_limit: str = "30/minute"
    trusted_proxy_ips: str = "127.0.0.1"

    # Pipeline
    data_dir: Path = Path("./data")
    dataset_bucket: str = "indian-supreme-court-judgments"
    ingest_years: Annotated[list[int], NoDecode] = Field(default_factory=lambda: [2024, 2025, 2026])
    max_failure_share: float = 0.1

    @property
    def database_dsn(self) -> str:
        """Connection string with the password added (if one is set and the URL has none)."""
        return make_conninfo(self.database_url, password=self.postgres_password) if self.postgres_password else \
            self.database_url

    @field_validator("allowed_origins", "ingest_years", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Accept comma-separated env values such as INGEST_YEARS=2024,2025."""
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
