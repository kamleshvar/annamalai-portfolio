"""Public archive routes."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    render_template,
    send_from_directory,
    url_for,
)
from sqlalchemy import text

from ..extensions import db
from ..forms import ContactForm
from ..models import (
    Achievement,
    Collaborator,
    EasterEgg,
    GalleryCategory,
    GalleryImage,
    Organization,
    Profile,
    Project,
    SiteSettings,
)
from ..utils import ALLOWED_UPLOAD_DIRS

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    settings = SiteSettings.load()
    profile = Profile.load()

    achievements = (
        Achievement.query.order_by(Achievement.sort_order.asc(), Achievement.id.asc()).all()
    )
    organizations = (
        Organization.query.order_by(Organization.sort_order.asc(), Organization.id.asc()).all()
    )
    projects = (
        Project.query.order_by(
            Project.featured.desc(), Project.sort_order.asc(), Project.id.asc()
        ).all()
    )
    collaborators = (
        Collaborator.query.order_by(
            Collaborator.sort_order.asc(), Collaborator.id.asc()
        ).all()
    )
    categories = (
        GalleryCategory.query.order_by(
            GalleryCategory.sort_order.asc(), GalleryCategory.id.asc()
        ).all()
    )
    gallery_images = [image for category in categories for image in category.images]
    categories_with_images = [category for category in categories if category.images]

    enabled_eggs = (
        EasterEgg.query.filter_by(enabled=True)
        .order_by(EasterEgg.sort_order.asc(), EasterEgg.id.asc())
        .all()
    )
    eggs_by_section: dict[str, list[EasterEgg]] = {}
    for egg in enabled_eggs:
        eggs_by_section.setdefault(egg.section, []).append(egg)

    fragments_by_slot: dict[int, EasterEgg] = {}
    for egg in enabled_eggs:
        if (
            egg.access_code
            and egg.access_slot in range(1, 5)
            and egg.access_slot not in fragments_by_slot
        ):
            fragments_by_slot[egg.access_slot] = egg
    access_fragments = [fragments_by_slot[slot] for slot in sorted(fragments_by_slot)]

    artifact_egg = next(
        (egg for egg in enabled_eggs if egg.interaction_type == "artifact"), None
    )
    terminal_egg = next(
        (
            egg
            for egg in enabled_eggs
            if egg.interaction_type == "terminal" and egg.section == "global"
        ),
        None,
    )

    featured_project = projects[0] if projects else None
    other_projects = [project for project in projects if project is not featured_project]

    stats = {
        "projects": len(projects),
        "achievements": len(achievements),
        "gallery": len(gallery_images),
        "collaborators": len(collaborators),
        "organizations": len(organizations),
        "teams": len(organizations),
    }

    return render_template(
        "index.html",
        settings=settings,
        profile=profile,
        achievements=achievements,
        organizations=organizations,
        projects=projects,
        featured_project=featured_project,
        other_projects=other_projects,
        collaborators=collaborators,
        categories=categories,
        categories_with_images=categories_with_images,
        gallery_images=gallery_images,
        enabled_eggs=enabled_eggs,
        eggs_by_section=eggs_by_section,
        access_fragments=access_fragments,
        fragments_by_slot=fragments_by_slot,
        artifact_egg=artifact_egg,
        terminal_egg=terminal_egg,
        stats=stats,
        contact_form=ContactForm(),
    )


@main_bp.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    """Serve owner-uploaded media only from known upload folders."""
    parts = PurePosixPath(filename).parts
    suffix = PurePosixPath(filename).suffix.lower().lstrip(".")
    if (
        len(parts) < 2
        or parts[0] not in ALLOWED_UPLOAD_DIRS
        or ".." in parts
        or "\\" in filename
        or "\x00" in filename
        or suffix not in current_app.config["ALLOWED_EXTENSIONS"]
    ):
        abort(404)
    response = send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        filename,
        conditional=True,
        max_age=604800,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


@main_bp.route("/api/archive")
def archive_api():
    """Public, read-only snapshot used by the secret terminal."""
    profile = Profile.load()
    projects = (
        Project.query.order_by(
            Project.featured.desc(), Project.sort_order.asc(), Project.id.asc()
        ).all()
    )
    achievements = (
        Achievement.query.order_by(Achievement.sort_order.asc(), Achievement.id.asc()).all()
    )
    organizations = (
        Organization.query.order_by(Organization.sort_order.asc(), Organization.id.asc()).all()
    )
    collaborators = (
        Collaborator.query.order_by(
            Collaborator.sort_order.asc(), Collaborator.id.asc()
        ).all()
    )
    gallery_count = GalleryImage.query.count()
    gallery_categories = (
        GalleryCategory.query.order_by(
            GalleryCategory.sort_order.asc(), GalleryCategory.id.asc()
        ).all()
    )
    terminal_egg = EasterEgg.query.filter_by(
        enabled=True, interaction_type="terminal", section="global"
    ).first()

    payload = {
        "identity": {
            "name": profile.name,
            "role": profile.role_line,
            "tagline": profile.tagline,
        },
        "stats": {
            "projects": len(projects),
            "achievements": len(achievements),
            "organizations": len(organizations),
            "collaborators": len(collaborators),
            "gallery_images": gallery_count,
        },
        "projects": [
            {
                "title": project.title,
                "tagline": project.tagline,
                "url": project.external_url,
                "github": project.github_url,
                "featured": project.featured,
                "tech": project.tech_list,
            }
            for project in projects
        ],
        "achievements": [
            {
                "title": achievement.title,
                "position": achievement.position,
                "year": achievement.year,
            }
            for achievement in achievements
        ],
        "organizations": [
            {"name": org.name, "role": org.role} for org in organizations
        ],
        "collaborators": [
            {"name": person.name, "website": person.website}
            for person in collaborators
        ],
        "gallery": {
            "image_count": gallery_count,
            "categories": [category.name for category in gallery_categories],
        },
        "handshake": terminal_egg.message if terminal_egg else "",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response


@main_bp.route("/healthz")
def healthz():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return jsonify({"status": "fault", "archive": "ANNAMALAI"}), 503
    return jsonify({"status": "online", "archive": "ANNAMALAI"})
