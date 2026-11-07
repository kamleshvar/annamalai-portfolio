"""Database models for the ANNAMALAI personal archive."""
from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class InitialsMixin:
    @property
    def initials(self) -> str:
        words = [word for word in (self.name or "A").split() if word]
        return "".join(word[0] for word in words[:2]).upper() or "A"


class Admin(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    must_change_password = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True))

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<Admin {self.username}>"


class Profile(TimestampMixin, InitialsMixin, db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default="ANNAMALAI")
    role_line = db.Column(
        db.String(180), nullable=False, default="Developer. Creator. Collaborator."
    )
    tagline = db.Column(
        db.String(240),
        nullable=False,
        default="Always building something beyond the ordinary.",
    )
    intro = db.Column(db.Text, default="")
    biography = db.Column(db.Text, default="")
    philosophy = db.Column(db.Text, default="")
    focus_areas = db.Column(db.String(240), default="Development / Leadership / Collaboration")
    location = db.Column(db.String(120), default="")
    email = db.Column(db.String(180), default="")
    phone = db.Column(db.String(60), default="")
    avatar = db.Column(db.String(255), default="")
    github_url = db.Column(db.String(255), default="")
    linkedin_url = db.Column(db.String(255), default="")
    instagram_url = db.Column(db.String(255), default="")
    x_url = db.Column(db.String(255), default="")

    @property
    def social_links(self) -> list[dict[str, str]]:
        links = [
            ("GitHub", self.github_url, "github"),
            ("LinkedIn", self.linkedin_url, "linkedin"),
            ("Instagram", self.instagram_url, "instagram"),
            ("X", self.x_url, "twitter"),
        ]
        return [
            {"label": label, "url": url.strip(), "icon": icon}
            for label, url, icon in links
            if url and url.strip()
        ]

    @classmethod
    def load(cls) -> "Profile":
        profile = db.session.query(cls).order_by(cls.id.asc()).first()
        if profile is None:
            profile = cls()
            db.session.add(profile)
            db.session.commit()
        return profile


class Achievement(TimestampMixin, db.Model):
    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    position = db.Column(db.String(80), nullable=False, default="")
    year = db.Column(db.String(20), default="")
    description = db.Column(db.Text, default="")
    certificate_image = db.Column(db.String(255), default="")
    event_image = db.Column(db.String(255), default="")
    sort_order = db.Column(db.Integer, default=0, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Achievement {self.title}>"


class Organization(TimestampMixin, InitialsMixin, db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    role = db.Column(db.String(120), nullable=False, default="")
    description = db.Column(db.Text, default="")
    website = db.Column(db.String(255), default="")
    logo = db.Column(db.String(255), default="")
    sort_order = db.Column(db.Integer, default=0, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"


class Project(TimestampMixin, db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    tagline = db.Column(db.String(240), default="")
    description = db.Column(db.Text, default="")
    long_description = db.Column(db.Text, default="")
    tech_stack = db.Column(db.String(500), default="")
    external_url = db.Column(db.String(500), default="")
    github_url = db.Column(db.String(500), default="")
    cover_image = db.Column(db.String(255), default="")
    featured = db.Column(db.Boolean, default=False, nullable=False, index=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False, index=True)

    images = db.relationship(
        "ProjectImage",
        backref="project",
        cascade="all, delete-orphan",
        order_by="ProjectImage.sort_order",
        lazy="selectin",
    )

    @property
    def tech_list(self) -> list[str]:
        if not self.tech_stack:
            return []
        parts = self.tech_stack.replace("\n", ",").split(",")
        return [part.strip() for part in parts if part.strip()]

    @property
    def display_image(self) -> str:
        if self.cover_image:
            return self.cover_image
        if self.images:
            return self.images[0].filename
        return ""

    def __repr__(self) -> str:
        return f"<Project {self.title}>"


class ProjectImage(TimestampMixin, db.Model):
    __tablename__ = "project_images"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(250), default="")
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class Collaborator(TimestampMixin, InitialsMixin, db.Model):
    __tablename__ = "collaborators"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    website = db.Column(db.String(500), default="")
    photo = db.Column(db.String(255), default="")
    sort_order = db.Column(db.Integer, default=0, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Collaborator {self.name}>"


class GalleryCategory(TimestampMixin, db.Model):
    __tablename__ = "gallery_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default="")
    sort_order = db.Column(db.Integer, default=0, nullable=False, index=True)

    images = db.relationship(
        "GalleryImage",
        backref="category",
        cascade="all, delete-orphan",
        order_by="GalleryImage.sort_order",
        lazy="selectin",
    )

    @property
    def cover(self) -> str:
        return self.images[0].filename if self.images else ""

    def __repr__(self) -> str:
        return f"<GalleryCategory {self.name}>"


class GalleryImage(TimestampMixin, db.Model):
    __tablename__ = "gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("gallery_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(250), default="")
    description = db.Column(db.Text, default="")
    width = db.Column(db.Integer, default=0, nullable=False)
    height = db.Column(db.Integer, default=0, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<GalleryImage {self.filename}>"


class EasterEgg(TimestampMixin, db.Model):
    __tablename__ = "easter_eggs"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    section = db.Column(db.String(40), nullable=False, default="global", index=True)
    interaction_type = db.Column(db.String(40), nullable=False, default="hidden")
    access_code = db.Column(db.String(24), nullable=False, default="")
    access_slot = db.Column(db.Integer, nullable=False, default=0)
    enabled = db.Column(db.Boolean, default=True, nullable=False, index=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<EasterEgg {self.key}>"


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False)
    subject = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<ContactMessage {self.subject}>"


class SiteSettings(TimestampMixin, db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)

    # Identity / metadata
    site_title = db.Column(db.String(120), nullable=False, default="ANNAMALAI")
    site_subtitle = db.Column(
        db.String(160), nullable=False, default="PERSONAL DIGITAL UNIVERSE"
    )
    archive_code = db.Column(db.String(60), nullable=False, default="ARCHIVE // A-001")
    meta_description = db.Column(
        db.Text,
        default="The personal digital universe of Annamalai — projects, achievements, teams, people and memories.",
    )

    # Hero
    hero_kicker = db.Column(
        db.String(180), nullable=False, default="PERSONAL ARCHIVE / TIMELINE A-001"
    )
    hero_line_1 = db.Column(
        db.String(180), nullable=False, default="EVERY TIMELINE HAS A STORY."
    )
    hero_line_2 = db.Column(db.String(180), nullable=False, default="THIS ONE IS MINE.")
    hero_description = db.Column(
        db.Text,
        default="Developer. Creator. Collaborator. Always building something beyond the ordinary.",
    )
    hero_background = db.Column(db.String(255), default="")

    # Section headings / intros
    about_heading = db.Column(db.String(180), nullable=False, default="MORE THAN JUST CODE.")
    about_note = db.Column(
        db.String(240), default="a living archive, not a finished story."
    )
    achievements_heading = db.Column(
        db.String(180), nullable=False, default="MARKS ON THE TIMELINE."
    )
    achievements_intro = db.Column(
        db.Text, default="Coordinates where effort became a result."
    )
    teams_heading = db.Column(
        db.String(220),
        nullable=False,
        default="THE PEOPLE AND TEAMS BEHIND THE WORK.",
    )
    teams_intro = db.Column(
        db.Text, default="Organizations, roles, and the shared work that shapes the archive."
    )
    projects_heading = db.Column(
        db.String(220), nullable=False, default="THINGS I BROUGHT INTO EXISTENCE."
    )
    projects_intro = db.Column(
        db.Text, default="A record of ideas that became real, and the work still in motion."
    )
    people_heading = db.Column(
        db.String(220), nullable=False, default="THE PEOPLE IN MY TIMELINE."
    )
    people_intro = db.Column(
        db.Text, default="Collaborators, builders, and the company that makes the work matter."
    )
    gallery_heading = db.Column(
        db.String(180), nullable=False, default="FRAGMENTS OF MEMORY."
    )
    gallery_intro = db.Column(
        db.Text, default="A visual archive of moments, milestones and the spaces between."
    )
    control_heading = db.Column(
        db.String(220), nullable=False, default="THE ARCHIVE CONTROL SYSTEM."
    )
    control_intro = db.Column(
        db.Text,
        default="A live interface into the records that power this universe. Every control is real.",
    )
    contact_heading = db.Column(
        db.String(180), nullable=False, default="SEND A SIGNAL."
    )
    contact_intro = db.Column(
        db.Text,
        default="Have a project, an idea, or a timeline worth crossing? The archive is listening.",
    )

    # Footer
    footer_note = db.Column(
        db.String(255),
        default="NOT JUST A PORTFOLIO. A TIMELINE OF EVERYTHING I AM BUILDING.",
    )
    footer_hint = db.Column(
        db.String(255), default="SOME RECORDS ARE HIDDEN. THE ARCHIVE REWARDS ATTENTION."
    )

    # Appearance
    color_bg = db.Column(db.String(9), default="#080909")
    color_panel = db.Column(db.String(9), default="#0D100F")
    color_text = db.Column(db.String(9), default="#EEEAE0")
    color_muted = db.Column(db.String(9), default="#AAA99F")
    color_red = db.Column(db.String(9), default="#A84D56")
    color_copper = db.Column(db.String(9), default="#A27A68")
    color_green = db.Column(db.String(9), default="#397B5A")
    color_green_light = db.Column(db.String(9), default="#B1E7BE")
    color_highlight = db.Column(db.String(9), default="#D6A37E")

    # Section visibility
    show_about = db.Column(db.Boolean, default=True, nullable=False)
    show_achievements = db.Column(db.Boolean, default=True, nullable=False)
    show_teams = db.Column(db.Boolean, default=True, nullable=False)
    show_projects = db.Column(db.Boolean, default=True, nullable=False)
    show_people = db.Column(db.Boolean, default=True, nullable=False)
    show_gallery = db.Column(db.Boolean, default=True, nullable=False)
    show_control = db.Column(db.Boolean, default=True, nullable=False)
    show_contact = db.Column(db.Boolean, default=True, nullable=False)

    # Motion / texture
    animations_enabled = db.Column(db.Boolean, default=True, nullable=False)
    grain_enabled = db.Column(db.Boolean, default=True, nullable=False)
    scanlines_enabled = db.Column(db.Boolean, default=True, nullable=False)

    @classmethod
    def load(cls) -> "SiteSettings":
        settings = db.session.query(cls).order_by(cls.id.asc()).first()
        if settings is None:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings
