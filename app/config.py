from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://foodops:foodops@localhost:5432/foodops"
    llm_model: str = ""
    llm_api_key: str = ""
    chroma_path: str = "./.chroma"


@lru_cache
def get_settings() -> Settings:
    return Settings()
