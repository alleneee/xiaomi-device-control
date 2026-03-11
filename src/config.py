import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

CREDENTIALS_FILE = Path(__file__).parent.parent / ".mi_credentials"


class Settings(BaseSettings):
    mi_username: str = ""
    mi_password: str = ""
    mi_cloud_country: str = "cn"

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.mi_username and CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)
        settings = Settings(
            mi_username=creds.get("username", ""),
            mi_password=creds.get("password", ""),
            mi_cloud_country=creds.get("country", "cn"),
        )
    return settings


def save_credentials(username: str, password: str, country: str = "cn"):
    get_settings.cache_clear()
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump({"username": username, "password": password, "country": country}, f)


def has_credentials() -> bool:
    s = get_settings()
    return bool(s.mi_username and s.mi_password)
