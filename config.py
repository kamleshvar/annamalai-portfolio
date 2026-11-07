"""Application configuration.

All secrets are read from environment variables. The development defaults are
intentionally safe for local use only and must be replaced for deployment.
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration shared by development and production."""

    # --- Core -------------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'annamalai.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Sessions / cookies ----------------------------------------------
    SESSION_COOKIE_NAME = "annamalai_archive_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = env_bool("REMEMBER_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # --- Uploads ----------------------------------------------------------
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "16")) * 1024 * 1024
    MAX_IMAGE_DIMENSION = 2600
    MAX_IMAGES_PER_UPLOAD = 24
    MAX_CONTENT_LENGTH_MB = int(os.getenv("MAX_UPLOAD_MB", "16"))

    # --- Forms ------------------------------------------------------------
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = timedelta(hours=8).total_seconds()

    # --- Initial administrator -------------------------------------------
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "futuremusic")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "sucess")
    AUTO_BOOTSTRAP = env_bool("AUTO_BOOTSTRAP", True)

    # --- Misc -------------------------------------------------------------
    SITE_TIMEZONE = os.getenv("SITE_TIMEZONE", "Asia/Kolkata")
    JSON_SORT_KEYS = False
    TEMPLATES_AUTO_RELOAD = env_bool("FLASK_DEBUG", False)
    PREFERRED_URL_SCHEME = "https" if env_bool("SESSION_COOKIE_SECURE", False) else "http"


class DevelopmentConfig(Config):
    DEBUG = env_bool("FLASK_DEBUG", False)


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    AUTO_BOOTSTRAP = False
    SERVER_NAME = "localhost.localdomain"


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
