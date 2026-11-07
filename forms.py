"""WTForms definitions for public and administrative interactions."""
from __future__ import annotations

import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, MultipleFileField
from wtforms import (
    BooleanField,
    EmailField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    NumberRange,
    Optional,
    Regexp,
    URL,
    ValidationError,
)

from .models import EasterEgg, GalleryCategory


def normalize_url(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    if value and not re.match(r"^https?://", value, re.IGNORECASE):
        value = "https://" + value
    return value


URL_FILTERS = [normalize_url]


class HexColor:
    def __call__(self, form, field) -> None:
        if field.data and not re.fullmatch(r"#[0-9A-Fa-f]{6}", field.data.strip()):
            raise ValidationError("Use a six-digit hex color, for example #A84D56.")


class LoginForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=40)]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=1, max=200)]
    )
    remember = BooleanField("Keep this archive open")


class ContactForm(FlaskForm):
    name = StringField(
        "Your name", validators=[DataRequired(), Length(min=2, max=120)]
    )
    email = EmailField(
        "Email", validators=[DataRequired(), Email(check_deliverability=False), Length(max=180)]
    )
    subject = StringField(
        "Subject", validators=[DataRequired(), Length(min=3, max=180)]
    )
    message = TextAreaField(
        "Message", validators=[DataRequired(), Length(min=10, max=4000)]
    )
    # Honeypot. Hidden from humans; filled only by naive bots.
    website = HiddenField("Website")


class ProfileForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    role_line = StringField("Role line", validators=[DataRequired(), Length(max=180)])
    tagline = StringField("Tagline", validators=[Optional(), Length(max=240)])
    intro = TextAreaField("Short introduction", validators=[Optional(), Length(max=1200)])
    biography = TextAreaField("Biography", validators=[Optional(), Length(max=8000)])
    philosophy = TextAreaField("Philosophy / quote", validators=[Optional(), Length(max=600)])
    focus_areas = StringField("Focus areas", validators=[Optional(), Length(max=240)])
    location = StringField("Location", validators=[Optional(), Length(max=120)])
    email = EmailField(
        "Contact email",
        validators=[Optional(), Email(check_deliverability=False), Length(max=180)],
    )
    phone = StringField("Phone", validators=[Optional(), Length(max=60)])
    github_url = StringField(
        "GitHub URL", filters=URL_FILTERS, validators=[Optional(), URL(), Length(max=255)]
    )
    linkedin_url = StringField(
        "LinkedIn URL", filters=URL_FILTERS, validators=[Optional(), URL(), Length(max=255)]
    )
    instagram_url = StringField(
        "Instagram URL", filters=URL_FILTERS, validators=[Optional(), URL(), Length(max=255)]
    )
    x_url = StringField(
        "X URL", filters=URL_FILTERS, validators=[Optional(), URL(), Length(max=255)]
    )
    avatar = FileField("Profile photograph")


class AchievementForm(FlaskForm):
    title = StringField(
        "Competition / event", validators=[DataRequired(), Length(max=180)]
    )
    position = StringField("Position", validators=[Optional(), Length(max=80)])
    year = StringField("Year", validators=[Optional(), Length(max=20)])
    description = TextAreaField("Notes", validators=[Optional(), Length(max=4000)])
    certificate_image = FileField("Certificate photograph")
    event_image = FileField("Event photograph")
    sort_order = IntegerField(
        "Sort order", validators=[Optional(), NumberRange(min=0, max=9999)], default=0
    )


class OrganizationForm(FlaskForm):
    name = StringField("Organization", validators=[DataRequired(), Length(max=160)])
    role = StringField("Role", validators=[Optional(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=4000)])
    website = StringField(
        "Website", filters=URL_FILTERS, validators=[Optional(), URL(), Length(max=255)]
    )
    logo = FileField("Organization logo")
    sort_order = IntegerField(
        "Sort order", validators=[Optional(), NumberRange(min=0, max=9999)], default=0
    )


class ProjectForm(FlaskForm):
    title = StringField("Project title", validators=[DataRequired(), Length(max=160)])
    tagline = StringField("Tagline", validators=[Optional(), Length(max=240)])
    description = TextAreaField("Short description", validators=[Optional(), Length(max=2000)])
    long_description = TextAreaField("Full description", validators=[Optional(), Length(max=10000)])
    tech_stack = StringField(
        "Technology tags",
        validators=[Optional(), Length(max=500)],
        description="Comma-separated, for example: Flask, SQLite, JavaScript",
    )
    external_url = StringField(
        "Live project URL", filters=URL_FILTERS, validators=[Optional(), URL(), Length(max=500)]
    )
    github_url = StringField(
        "GitHub URL", filters=URL_FILTERS, validators=[Optional(), URL(), Length(max=500)]
    )
    featured = BooleanField("Feature this project")
    cover_image = FileField("Cover image")
    images = MultipleFileField("Additional screenshots")
    sort_order = IntegerField(
        "Sort order", validators=[Optional(), NumberRange(min=0, max=9999)], default=0
    )


class CollaboratorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    website = StringField(
        "Website", filters=URL_FILTERS, validators=[Optional(), URL(), Length(max=500)]
    )
    photo = FileField("Profile photograph")
    sort_order = IntegerField(
        "Sort order", validators=[Optional(), NumberRange(min=0, max=9999)], default=0
    )


class GalleryCategoryForm(FlaskForm):
    name = StringField("Category name", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    sort_order = IntegerField(
        "Sort order", validators=[Optional(), NumberRange(min=0, max=9999)], default=0
    )

    def __init__(self, *args, original: GalleryCategory | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.original = original

    def validate_name(self, field):
        query = GalleryCategory.query.filter(GalleryCategory.name.ilike(field.data.strip()))
        if self.original is not None:
            query = query.filter(GalleryCategory.id != self.original.id)
        if query.first():
            raise ValidationError("A category with this name already exists.")


class GalleryImageForm(FlaskForm):
    caption = StringField("Caption", validators=[Optional(), Length(max=250)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    sort_order = IntegerField(
        "Sort order", validators=[Optional(), NumberRange(min=0, max=9999)], default=0
    )


SECTION_CHOICES = [
    ("global", "Global / terminal"),
    ("hero", "Hero"),
    ("about", "About"),
    ("achievements", "Achievements"),
    ("teams", "Teams"),
    ("projects", "Projects"),
    ("people", "People"),
    ("gallery", "Gallery"),
    ("control", "Control system"),
    ("contact", "Contact"),
    ("footer", "Footer"),
]

INTERACTION_CHOICES = [
    ("hidden", "Hidden object"),
    ("artifact", "Artifact"),
    ("document", "Archive document"),
    ("terminal", "Terminal record"),
]


class EasterEggForm(FlaskForm):
    key = StringField(
        "Unique key",
        validators=[
            DataRequired(),
            Length(min=2, max=80),
            Regexp(
                r"^[a-z0-9][a-z0-9\-_]*$",
                message="Use lowercase letters, numbers, hyphens or underscores.",
            ),
        ],
    )
    title = StringField("Title", validators=[DataRequired(), Length(max=160)])
    message = TextAreaField(
        "Revealed message", validators=[DataRequired(), Length(max=4000)]
    )
    section = SelectField(
        "Assigned section", choices=SECTION_CHOICES, validators=[DataRequired()]
    )
    interaction_type = SelectField(
        "Interaction type", choices=INTERACTION_CHOICES, validators=[DataRequired()]
    )
    access_code = StringField(
        "Access fragment code",
        validators=[
            Optional(),
            Length(max=24),
            Regexp(
                r"^[A-Za-z0-9][A-Za-z0-9\-_]*$",
                message="Use letters, numbers, hyphens or underscores only.",
            ),
        ],
    )
    access_slot = IntegerField(
        "Access fragment slot",
        validators=[Optional(), NumberRange(min=0, max=4)],
        default=0,
    )
    enabled = BooleanField("Enabled", default=True)
    sort_order = IntegerField(
        "Sort order", validators=[Optional(), NumberRange(min=0, max=9999)], default=0
    )

    def __init__(self, *args, original: EasterEgg | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.original = original

    def validate_key(self, field):
        query = EasterEgg.query.filter_by(key=field.data.strip())
        if self.original is not None:
            query = query.filter(EasterEgg.id != self.original.id)
        if query.first():
            raise ValidationError("This key is already assigned to another record.")

    def validate_access_code(self, field):
        code = (field.data or "").strip().upper()
        field.data = code
        if not code:
            return
        if not self.access_slot.data:
            raise ValidationError(
                "Choose an access-fragment slot (1–4) for this code."
            )
        query = EasterEgg.query.filter(EasterEgg.access_code == code)
        if self.original is not None:
            query = query.filter(EasterEgg.id != self.original.id)
        if query.first():
            raise ValidationError("This access code is already in use.")

    def validate_access_slot(self, field):
        slot = field.data or 0
        if slot and not (self.access_code.data or "").strip():
            raise ValidationError("Add an access code for this fragment slot.")
        if not slot:
            return
        query = EasterEgg.query.filter(EasterEgg.access_slot == slot)
        if self.original is not None:
            query = query.filter(EasterEgg.id != self.original.id)
        if query.first():
            raise ValidationError("Another hidden record already uses this slot.")


class AppearanceForm(FlaskForm):
    site_title = StringField("Site title", validators=[DataRequired(), Length(max=120)])
    site_subtitle = StringField(
        "Site subtitle", validators=[DataRequired(), Length(max=160)]
    )
    archive_code = StringField(
        "Archive code", validators=[DataRequired(), Length(max=60)]
    )
    meta_description = TextAreaField(
        "Meta description", validators=[Optional(), Length(max=500)]
    )

    hero_kicker = StringField("Hero kicker", validators=[Optional(), Length(max=180)])
    hero_line_1 = StringField("Hero line 1", validators=[Optional(), Length(max=180)])
    hero_line_2 = StringField("Hero line 2", validators=[Optional(), Length(max=180)])
    hero_description = TextAreaField(
        "Hero description", validators=[Optional(), Length(max=1200)]
    )
    hero_background = FileField("Hero background image")

    about_heading = StringField("About heading", validators=[Optional(), Length(max=180)])
    about_note = StringField("About margin note", validators=[Optional(), Length(max=240)])

    achievements_heading = StringField(
        "Achievements heading", validators=[Optional(), Length(max=180)]
    )
    achievements_intro = TextAreaField(
        "Achievements intro", validators=[Optional(), Length(max=600)]
    )
    teams_heading = StringField(
        "Teams heading", validators=[Optional(), Length(max=220)]
    )
    teams_intro = TextAreaField("Teams intro", validators=[Optional(), Length(max=600)])
    projects_heading = StringField(
        "Projects heading", validators=[Optional(), Length(max=220)]
    )
    projects_intro = TextAreaField("Projects intro", validators=[Optional(), Length(max=600)])
    people_heading = StringField(
        "People heading", validators=[Optional(), Length(max=220)]
    )
    people_intro = TextAreaField("People intro", validators=[Optional(), Length(max=600)])
    gallery_heading = StringField(
        "Gallery heading", validators=[Optional(), Length(max=180)]
    )
    gallery_intro = TextAreaField("Gallery intro", validators=[Optional(), Length(max=600)])
    control_heading = StringField(
        "Control heading", validators=[Optional(), Length(max=220)]
    )
    control_intro = TextAreaField("Control intro", validators=[Optional(), Length(max=600)])
    contact_heading = StringField(
        "Contact heading", validators=[Optional(), Length(max=180)]
    )
    contact_intro = TextAreaField("Contact intro", validators=[Optional(), Length(max=600)])

    footer_note = StringField("Footer statement", validators=[Optional(), Length(max=255)])
    footer_hint = StringField("Footer secret hint", validators=[Optional(), Length(max=255)])

    color_bg = StringField(
        "Background", validators=[DataRequired(), HexColor(), Length(max=9)]
    )
    color_panel = StringField(
        "Panel", validators=[DataRequired(), HexColor(), Length(max=9)]
    )
    color_text = StringField(
        "Primary text", validators=[DataRequired(), HexColor(), Length(max=9)]
    )
    color_muted = StringField(
        "Secondary text", validators=[DataRequired(), HexColor(), Length(max=9)]
    )
    color_red = StringField(
        "Archive red", validators=[DataRequired(), HexColor(), Length(max=9)]
    )
    color_copper = StringField(
        "Copper", validators=[DataRequired(), HexColor(), Length(max=9)]
    )
    color_green = StringField(
        "Archive green", validators=[DataRequired(), HexColor(), Length(max=9)]
    )
    color_green_light = StringField(
        "Signal green", validators=[DataRequired(), HexColor(), Length(max=9)]
    )
    color_highlight = StringField(
        "Highlight", validators=[DataRequired(), HexColor(), Length(max=9)]
    )

    show_about = BooleanField("Show About section")
    show_achievements = BooleanField("Show Achievements section")
    show_teams = BooleanField("Show Teams section")
    show_projects = BooleanField("Show Projects section")
    show_people = BooleanField("Show People section")
    show_gallery = BooleanField("Show Gallery section")
    show_control = BooleanField("Show Control System section")
    show_contact = BooleanField("Show Contact section")

    animations_enabled = BooleanField("Enable entrance and scroll animations")
    grain_enabled = BooleanField("Enable film grain texture")
    scanlines_enabled = BooleanField("Enable scanline texture")


class AccountForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=40),
            Regexp(
                r"^[A-Za-z0-9_.-]+$",
                message="Use letters, numbers, dots, dashes or underscores only.",
            ),
        ],
    )


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current password", validators=[DataRequired(), Length(max=200)]
    )
    new_password = PasswordField(
        "New password", validators=[DataRequired(), Length(min=8, max=200)]
    )
    confirm_password = PasswordField(
        "Confirm new password", validators=[DataRequired(), Length(min=8, max=200)]
    )

    def validate_new_password(self, field):
        if not re.search(r"[A-Za-z]", field.data or "") or not re.search(
            r"\d", field.data or ""
        ):
            raise ValidationError("Use at least one letter and one number.")

    def validate_confirm_password(self, field):
        if self.new_password.data != field.data:
            raise ValidationError("The new passwords do not match.")
