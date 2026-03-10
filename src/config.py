from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mi_username: str
    mi_password: str
    mi_cloud_country: str = "cn"

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
