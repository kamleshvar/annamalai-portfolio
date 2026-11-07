"""Security, upload, ordering and presentation helpers."""
from __future__ import annotations

import os
import re
import threading
import time
import unicodedata
import uuid
import warnings
from io import BytesIO
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

from flask import current_app, request, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .extensions import db

ALLOWED_UPLOAD_DIRS = {
    "profiles",
    "achievements",
    "organizations",
    "projects",
    "gallery",
    "site",
}

FORMAT_EXTENSION = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class UploadError(ValueError):
    """Raised when a file is not a safe, supported image."""


def _upload_root() -> Path:
    return Path(current_app.config["UPLOAD_FOLDER"]).resolve()


def ensure_upload_folders() -> None:
    root = _upload_root()
    for folder in sorted(ALLOWED_UPLOAD_DIRS):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / ".gitkeep").touch(exist_ok=True)


def save_image(
    file_storage: FileStorage | None,
    subdir: str,
    *,
    max_dimension: int | None = None,
) -> dict[str, int | str] | None:
    """Validate, normalize and store an uploaded image.

    Returns ``{"filename": "gallery/uuid.jpg", "width": w, "height": h}`` or
    ``None`` when no file was supplied. Raises :class:`UploadError` on any
    invalid or unsafe upload.
    """
    if file_storage is None or not file_storage.filename:
        return None
    if subdir not in ALLOWED_UPLOAD_DIRS:
        raise UploadError("Invalid upload destination.")

    safe_original = secure_filename(file_storage.filename)
    extension = safe_original.rsplit(".", 1)[-1].lower() if "." in safe_original else ""
    if extension not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise UploadError("Only JPG, JPEG, PNG and WEBP images are accepted.")

    max_dimension = max_dimension or int(current_app.config["MAX_IMAGE_DIMENSION"])

    try:
        file_storage.stream.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            verifier = Image.open(file_storage.stream)
            verifier.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning):
        raise UploadError("The uploaded file is not a valid image.") from None
    finally:
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(file_storage.stream)
            image.load()
            image_format = (image.format or "").upper()
            if image_format not in current_app.config["ALLOWED_IMAGE_FORMATS"]:
                raise UploadError("Unsupported image format.")
            image = ImageOps.exif_transpose(image)
            if max(image.size) > max_dimension:
                image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            width, height = image.size
            if width < 1 or height < 1:
                raise UploadError("The image has invalid dimensions.")

            output = BytesIO()
            if image_format == "JPEG":
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                image.save(
                    output,
                    format="JPEG",
                    quality=90,
                    optimize=True,
                    progressive=True,
                )
            elif image_format == "PNG":
                if image.mode == "P":
                    image = image.convert("RGBA")
                image.save(output, format="PNG", optimize=True)
            else:
                if image.mode == "P":
                    image = image.convert("RGBA")
                image.save(output, format="WEBP", quality=88, method=4)
    except (OSError, ValueError, Image.DecompressionBombWarning) as exc:
        if isinstance(exc, UploadError):
            raise
        raise UploadError("The image could not be processed.") from None
    finally:
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass

    unique_name = f"{uuid.uuid4().hex}.{FORMAT_EXTENSION[image_format]}"
    root = _upload_root()
    folder = root / subdir
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / unique_name
    try:
        with open(destination, "wb") as handle:
            handle.write(output.getvalue())
    except OSError:
        raise UploadError("The image could not be saved.") from None

    return {
        "filename": f"{subdir}/{unique_name}",
        "width": width,
        "height": height,
    }


def delete_upload(relative_path: str | None) -> None:
    """Safely remove a file inside the uploads directory."""
    if not relative_path:
        return
    root = _upload_root()
    candidate = (root / relative_path).resolve()
    try:
        if os.path.commonpath([str(root), str(candidate)]) != str(root):
            return
    except (ValueError, OSError):
        return
    if candidate.is_file():
        try:
            candidate.unlink()
        except OSError:
            pass


def delete_uploads(paths: Iterable[str | None]) -> None:
    for path in paths:
        delete_upload(path)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value[:100].strip("-") or "category"


def unique_slug(model, value: str, *, ignore_id: int | None = None) -> str:
    base = slugify(value)
    candidate = base
    counter = 2
    while True:
        stmt = db.select(model).where(model.slug == candidate)
        if ignore_id is not None:
            stmt = stmt.where(model.id != ignore_id)
        if db.session.execute(stmt).scalar_one_or_none() is None:
            return candidate
        candidate = f"{base}-{counter}"
        counter += 1


def next_sort_order(model) -> int:
    highest = db.session.execute(db.select(db.func.max(model.sort_order))).scalar()
    return int(highest or 0) + 1


def move_ordered(model, instance, direction: str) -> bool:
    """Move a sortable instance up/down, normalizing the full order."""
    if direction not in {"up", "down"}:
        return False
    items = list(
        db.session.execute(
            db.select(model).order_by(model.sort_order.asc(), model.id.asc())
        ).scalars()
    )
    try:
        index = items.index(instance)
    except ValueError:
        return False
    target = index - 1 if direction == "up" else index + 1
    if target < 0 or target >= len(items):
        return False
    items[index], items[target] = items[target], items[index]
    for position, item in enumerate(items, start=1):
        item.sort_order = position
    db.session.commit()
    return True


def is_safe_redirect_url(target: str | None) -> bool:
    if not target:
        return False
    host_url = request.host_url
    target_url = urlparse(urljoin(host_url, target))
    return target_url.scheme in {"http", "https"} and target_url.netloc == urlparse(host_url).netloc


def upload_url(filename: str | None) -> str:
    if not filename:
        return ""
    return url_for("main.uploaded_file", filename=filename)


class AttemptLimiter:
    """Small in-memory brute-force throttle for the single admin account.

    This is intentionally process-local. For a multi-process deployment use a
    shared store (Redis) or an upstream rate limiter.
    """

    def __init__(self, max_attempts: int = 6, window_seconds: int = 600) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str) -> list[float]:
        cutoff = time.time() - self.window_seconds
        attempts = [stamp for stamp in self._attempts.get(key, []) if stamp >= cutoff]
        if attempts:
            self._attempts[key] = attempts
        else:
            self._attempts.pop(key, None)
        return attempts

    def is_locked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key)) >= self.max_attempts

    def fail(self, key: str) -> None:
        with self._lock:
            attempts = self._prune(key)
            attempts.append(time.time())
            self._attempts[key] = attempts

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
