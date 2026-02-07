from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")
    amadeus_api_key: str = Field("", alias="AMADEUS_API_KEY")
    amadeus_api_secret: str = Field("", alias="AMADEUS_API_SECRET")
    amadeus_env: str = Field("test", alias="AMADEUS_ENV")
    opentripmap_api_key: str = Field("", alias="OPENTRIPMAP_API_KEY")
    opentripmap_base_url: str = Field(
        "https://api.opentripmap.com/0.1/en",
        alias="OPENTRIPMAP_BASE_URL",
    )
    http_trust_env: bool = Field(False, alias="HTTP_TRUST_ENV")
    result_cache_ttl_seconds: int = Field(600, alias="RESULT_CACHE_TTL_SECONDS")
    city_candidates_limit: int = Field(5, alias="CITY_CANDIDATES_LIMIT")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
