import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent

for dotenv_path in (BACKEND_DIR / ".env", PROJECT_ROOT / ".env"):
    load_dotenv(dotenv_path=dotenv_path, override=False)


class BaseConfig:
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    PORT = int(os.getenv("PORT", "5000"))
    ORS_API_KEY = os.getenv("ORS_API_KEY", "")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
    OPENWEATHER_UNITS = os.getenv("OPENWEATHER_UNITS", "metric")
    NOMINATIM_USER_AGENT = os.getenv(
        "NOMINATIM_USER_AGENT",
        "smart-supply-chain-optimization/1.0",
    )
    NOMINATIM_EMAIL = os.getenv("NOMINATIM_EMAIL", "")
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))
    REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


def get_config():
    env = os.getenv("FLASK_ENV", "production").lower()
    if env == "development":
        return DevelopmentConfig
    return ProductionConfig
