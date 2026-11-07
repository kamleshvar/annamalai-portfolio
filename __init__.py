"""ANNAMALAI — Personal Digital Universe application factory."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import unquote

from flask import Flask, abort, render_template, request, session
from flask_login import current_user
from flask_wtf.csrf import CSRFError

from config import CONFIG_MAP
from .commands import register_commands
from .extensions import csrf, db, login_manager, migrate
from .models import Admin, Profile, SiteSettings
from .schema import ensure_archive_schema
from .seed import seed_database
from .utils import ensure_upload_folders

logger = logging.getLogger(__name__)

# Files that should never be served by the web process. The Flask app only has
# one public static folder and one upload route, but this request-level guard
# keeps future route changes from accidentally exposing project source, secrets
# or the SQLite database.
_BLOCKED_SOURCE_EXTENSIONS = frozenset(
    {
        ".py",
        ".pyc",
        ".pyo",
        ".pyd",
        ".pyw",
        ".db",
        ".db-wal",
        ".db-shm",
        ".sqlite",
        ".sqlite3",
        ".env",
        ".ini",
        ".cfg",
        ".conf",
        ".sql",
        ".log",
        ".bak",
        ".backup",
        ".old",
        ".orig",
        ".zip",
        ".tar",
        ".gz",
        ".tgz",
        ".rar",
        ".7z",
        ".yml",
        ".yaml",
        ".toml",
        ".lock",
        ".ipynb",
        ".sh",
        ".ps1",
        ".bat",
        ".cmd",
        ".pem",
        ".key",
        ".crt",
        ".csr",
        ".p12",
        ".pfx",
        ".map",
        ".md",
        ".markdown",
        ".rst",
    }
)

_BLOCKED_SOURCE_PARTS = frozenset(
    {
        "app",
        "tests",
        "venv",
        "node_modules",
        "instance",
        "migrations",
        "__pycache__",
    }
)

_BLOCKED_FILENAMES = frozenset(
    {
        "annamalai.db",
        "config.py",
        "run.py",
        "wsgi.py",
        "manage.py",
        "requirements.txt",
        "readme.md",
        "dockerfile",
        "docker-compose.yml",
        "pyproject.toml",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
    }
)

# The public static folder is intentionally limited to assets the browser must
# download. Anything else (Markdown, source maps, archives) is refused.
_STATIC_ASSET_EXTENSIONS = frozenset(
    {
        ".css",
        ".js",
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".ico",
        ".avif",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".mp4",
        ".webm",
        ".webmanifest",
    }
)


def create_app(config_name: str | None = None, test_config: dict | None = None) -> Flask:
    config_name = config_name or os.getenv("FLASK_CONFIG", "default")
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(CONFIG_MAP.get(config_name, CONFIG_MAP["default"]))
    if test_config:
        app.config.update(test_config)

    _validate_runtime_config(app)

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Blueprints
    from .routes.admin import admin_bp
    from .routes.contact import contact_bp
    from .routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    register_commands(app)
    _register_user_loader()
    _register_context(app)
    _register_filters(app)
    _register_error_handlers(app)
    _register_source_protection(app)
    _register_security_headers(app)

    with app.app_context():
        ensure_upload_folders()
        if app.config.get("AUTO_BOOTSTRAP", False):
            db.create_all()
            added_columns = ensure_archive_schema()
            created = seed_database(backfill_access_fragments=bool(added_columns))
            if created.get("admin"):
                logger.warning(
                    "Initial administrator seeded. Log in and change the password immediately."
                )

    return app


def _validate_runtime_config(app: Flask) -> None:
    if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"] == "dev-only-change-this-key":
        if not app.config.get("TESTING") and not app.debug:
            raise RuntimeError(
                "SECRET_KEY is not set. Create a .env file from .env.example first."
            )
        logger.warning("Using an insecure development SECRET_KEY. Set SECRET_KEY in .env.")


def _register_user_loader() -> None:
    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return db.session.get(Admin, int(user_id))
        except (TypeError, ValueError):
            return None


def _fallback_settings() -> SiteSettings:
    """Ephemeral settings object used only if the database is unreachable."""
    settings = SiteSettings()
    for key, value in {
        "site_title": "ANNAMALAI",
        "site_subtitle": "PERSONAL DIGITAL UNIVERSE",
        "archive_code": "ARCHIVE // A-001",
        "meta_description": "The personal digital universe of Annamalai.",
        "hero_kicker": "PERSONAL ARCHIVE / TIMELINE A-001",
        "hero_line_1": "EVERY TIMELINE HAS A STORY.",
        "hero_line_2": "THIS ONE IS MINE.",
        "hero_description": "Developer. Creator. Collaborator.",
        "about_heading": "MORE THAN JUST CODE.",
        "about_note": "a living archive, not a finished story.",
        "achievements_heading": "MARKS ON THE TIMELINE.",
        "achievements_intro": "",
        "teams_heading": "THE PEOPLE AND TEAMS BEHIND THE WORK.",
        "teams_intro": "",
        "projects_heading": "THINGS I BROUGHT INTO EXISTENCE.",
        "projects_intro": "",
        "people_heading": "THE PEOPLE IN MY TIMELINE.",
        "people_intro": "",
        "gallery_heading": "FRAGMENTS OF MEMORY.",
        "gallery_intro": "",
        "control_heading": "THE ARCHIVE CONTROL SYSTEM.",
        "control_intro": "",
        "contact_heading": "SEND A SIGNAL.",
        "contact_intro": "",
        "footer_note": "NOT JUST A PORTFOLIO.",
        "footer_hint": "",
        "color_bg": "#080909",
        "color_panel": "#0D100F",
        "color_text": "#EEEAE0",
        "color_muted": "#AAA99F",
        "color_red": "#A84D56",
        "color_copper": "#A27A68",
        "color_green": "#397B5A",
        "color_green_light": "#B1E7BE",
        "color_highlight": "#D6A37E",
        "show_about": True,
        "show_achievements": True,
        "show_teams": True,
        "show_projects": True,
        "show_people": True,
        "show_gallery": True,
        "show_control": True,
        "show_contact": True,
        "animations_enabled": True,
        "grain_enabled": True,
        "scanlines_enabled": True,
    }.items():
        setattr(settings, key, value)
    settings.hero_background = ""
    return settings


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_archive_globals():
        try:
            profile = Profile.load()
            settings = SiteSettings.load()
        except Exception:  # pragma: no cover - database outage fallback
            db.session.rollback()
            profile = Profile(name="ANNAMALAI")
            settings = _fallback_settings()
        return {
            "site": settings,
            "profile": profile,
            "current_year": datetime.now(timezone.utc).year,
            "max_upload_mb": app.config["MAX_CONTENT_LENGTH_MB"],
            "is_admin_area": request.path.startswith("/admin"),
        }

    @app.before_request
    def mark_session_permanent():
        if current_user.is_authenticated:
            session.permanent = True


def _register_filters(app: Flask) -> None:
    @app.template_filter("datefmt")
    def datefmt(value, fmt: str = "%d %b %Y"):
        if not value:
            return "—"
        if isinstance(value, str):
            return value
        return value.strftime(fmt)

    @app.template_filter("timefmt")
    def timefmt(value, fmt: str = "%d.%m.%Y · %H:%M"):
        if not value:
            return "—"
        if isinstance(value, str):
            return value
        return value.strftime(fmt)

    @app.template_filter("paragraphs")
    def paragraphs(value):
        if not value:
            return []
        return [block.strip() for block in str(value).split("\n\n") if block.strip()]


def _register_error_handlers(app: Flask) -> None:
    def render_error(code: int, title: str, message: str):
        return (
            render_template(
                "errors/error.html",
                code=code,
                error_title=title,
                error_message=message,
            ),
            code,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return render_error(
            404,
            "RECORD NOT FOUND",
            "This coordinate does not exist in the archive. The timeline may have shifted.",
        )

    @app.errorhandler(403)
    def forbidden(_error):
        return render_error(
            403,
            "ACCESS DENIED",
            "Your clearance does not cover this part of the archive.",
        )

    @app.errorhandler(413)
    def too_large(_error):
        return render_error(
            413,
            "PAYLOAD TOO LARGE",
            f"The upload exceeds the {app.config['MAX_CONTENT_LENGTH_MB']} MB archive limit.",
        )

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        return render_error(
            400,
            "VERIFICATION FAILED",
            "The security token expired or was invalid. Reload the page and try again.",
        )

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled archive error: %s", error)
        return render_error(
            500,
            "TEMPORAL FAULT",
            "The archive encountered an unexpected fault. The timeline is still intact.",
        )


def _register_source_protection(app: Flask) -> None:
    """Refuse requests for project source, secrets, databases and raw docs.

    Client-delivered HTML, CSS and JavaScript cannot be hidden from a browser;
    this guard only protects files that should remain server-side.
    """

    @app.before_request
    def block_source_exposure():
        path = unquote(request.path or "/", errors="replace").replace("\\", "/").lower()

        if "\x00" in path or len(path) > 2048:
            abort(404)

        parts = tuple(part for part in path.split("/") if part)
        if any(part.startswith(".") for part in parts):
            abort(404)
        if any(part in _BLOCKED_SOURCE_PARTS for part in parts):
            abort(404)
        if parts and parts[-1] in _BLOCKED_FILENAMES:
            abort(404)
        if any(path.endswith(extension) for extension in _BLOCKED_SOURCE_EXTENSIONS):
            abort(404)

        if path == "/static" or path.startswith("/static/"):
            if PurePosixPath(path).suffix not in _STATIC_ASSET_EXTENSIONS:
                abort(404)


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none';",
        )
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if request.path.startswith("/admin"):
            response.headers["Cache-Control"] = "no-store, private"
        return response
