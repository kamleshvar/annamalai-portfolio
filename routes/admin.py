"""Protected archive control room (admin dashboard)."""
from __future__ import annotations

from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db, login_manager
from ..forms import (
    AccountForm,
    AchievementForm,
    AppearanceForm,
    ChangePasswordForm,
    CollaboratorForm,
    EasterEggForm,
    GalleryCategoryForm,
    LoginForm,
    OrganizationForm,
    ProfileForm,
    ProjectForm,
)
from ..models import (
    Achievement,
    Admin,
    Collaborator,
    ContactMessage,
    EasterEgg,
    GalleryCategory,
    GalleryImage,
    Organization,
    Profile,
    Project,
    ProjectImage,
    SiteSettings,
    utcnow,
)
from ..utils import (
    AttemptLimiter,
    UploadError,
    delete_upload,
    delete_uploads,
    is_safe_redirect_url,
    move_ordered,
    next_sort_order,
    save_image,
    unique_slug,
)

admin_bp = Blueprint("admin", __name__)
login_limiter = AttemptLimiter(max_attempts=6, window_seconds=600)

PUBLIC_ADMIN_ENDPOINTS = {"admin.login"}
PASSWORD_CHANGE_ALLOWED = {"admin.change_password", "admin.logout", "static"}


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
@admin_bp.before_request
def guard_control_room():
    if request.endpoint in PUBLIC_ADMIN_ENDPOINTS:
        return None
    if not current_user.is_authenticated:
        return login_manager.unauthorized()
    if current_user.must_change_password and request.endpoint not in PASSWORD_CHANGE_ALLOWED:
        flash(
            "The initial archive password must be replaced before the control room opens.",
            "warning",
        )
        return redirect(url_for("admin.change_password"))
    return None


@admin_bp.context_processor
def inject_admin_globals():
    if not current_user.is_authenticated:
        return {"unread_count": 0}
    return {
        "unread_count": ContactMessage.query.filter_by(is_read=False).count(),
        "current_admin": current_user,
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
@admin_bp.route("/")
def index():
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        attempt_key = f"{request.remote_addr or 'unknown'}:{username.lower()}"
        if login_limiter.is_locked(attempt_key):
            flash(
                "Too many failed attempts. This access point is temporarily locked.",
                "error",
            )
            return render_template("admin/login.html", form=form)

        admin = Admin.query.filter_by(username=username).first()
        if admin is None or not admin.check_password(form.password.data):
            login_limiter.fail(attempt_key)
            flash("Invalid archive credentials. Access denied.", "error")
            return render_template("admin/login.html", form=form)

        login_limiter.reset(attempt_key)
        session.clear()
        login_user(admin, remember=form.remember.data)
        session.permanent = True
        admin.last_login_at = utcnow()
        db.session.commit()

        if admin.must_change_password:
            flash(
                "Access granted. Replace the initial password to activate this account.",
                "warning",
            )
            return redirect(url_for("admin.change_password"))

        next_url = request.args.get("next", "")
        if next_url and next_url.startswith("/admin") and is_safe_redirect_url(next_url):
            return redirect(next_url)
        flash(f"Welcome back, {admin.username}. The archive is online.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/login.html", form=form)


@admin_bp.route("/logout", methods=["POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()
    session.clear()
    flash("You have left the control room. Session closed.", "info")
    return redirect(url_for("admin.login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@admin_bp.route("/dashboard")
def dashboard():
    stats = {
        "projects": Project.query.count(),
        "achievements": Achievement.query.count(),
        "gallery_images": GalleryImage.query.count(),
        "collaborators": Collaborator.query.count(),
        "organizations": Organization.query.count(),
        "gallery_categories": GalleryCategory.query.count(),
        "unread_messages": ContactMessage.query.filter_by(is_read=False).count(),
        "messages": ContactMessage.query.count(),
        "easter_eggs": EasterEgg.query.filter_by(enabled=True).count(),
    }
    recent_messages = (
        ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(6).all()
    )
    recent_projects = (
        Project.query.order_by(Project.updated_at.desc()).limit(5).all()
    )
    recent_achievements = (
        Achievement.query.order_by(Achievement.updated_at.desc()).limit(4).all()
    )
    recent_eggs = (
        EasterEgg.query.order_by(EasterEgg.updated_at.desc()).limit(4).all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_messages=recent_messages,
        recent_projects=recent_projects,
        recent_achievements=recent_achievements,
        recent_eggs=recent_eggs,
        now=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@admin_bp.route("/profile", methods=["GET", "POST"])
def profile():
    profile = Profile.load()
    form = ProfileForm(obj=profile)
    if form.validate_on_submit():
        new_avatar = profile.avatar
        if form.avatar.data and getattr(form.avatar.data, "filename", ""):
            try:
                saved = save_image(form.avatar.data, "profiles")
            except UploadError as exc:
                flash(str(exc), "error")
                return render_template("admin/profile.html", form=form, profile=profile)
            if saved:
                new_avatar = str(saved["filename"])
        for field_name in (
            "name",
            "role_line",
            "tagline",
            "intro",
            "biography",
            "philosophy",
            "focus_areas",
            "location",
            "email",
            "phone",
            "github_url",
            "linkedin_url",
            "instagram_url",
            "x_url",
        ):
            setattr(profile, field_name, getattr(form, field_name).data or "")
        if new_avatar != profile.avatar:
            delete_upload(profile.avatar)
            profile.avatar = new_avatar
        db.session.commit()
        flash("Profile record updated across the public archive.", "success")
        return redirect(url_for("admin.profile"))
    return render_template("admin/profile.html", form=form, profile=profile)


@admin_bp.route("/profile/avatar/delete", methods=["POST"])
def profile_avatar_delete():
    profile = Profile.load()
    if profile.avatar:
        delete_upload(profile.avatar)
        profile.avatar = ""
        db.session.commit()
        flash("Profile photograph removed.", "info")
    return redirect(url_for("admin.profile"))


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------
@admin_bp.route("/achievements")
def achievements():
    items = Achievement.query.order_by(
        Achievement.sort_order.asc(), Achievement.id.asc()
    ).all()
    return render_template("admin/achievements.html", achievements=items)


@admin_bp.route("/achievements/new", methods=["GET", "POST"])
def achievement_new():
    form = AchievementForm()
    if form.validate_on_submit():
        saved = _save_field_images(
            [
                (form.certificate_image, "achievements"),
                (form.event_image, "achievements"),
            ]
        )
        if saved is None:
            return render_template(
                "admin/achievement_form.html", form=form, achievement=None
            )
        achievement = Achievement(
            title=form.title.data.strip(),
            position=(form.position.data or "").strip(),
            year=(form.year.data or "").strip(),
            description=(form.description.data or "").strip(),
            certificate_image=saved.get("certificate_image", ""),
            event_image=saved.get("event_image", ""),
            sort_order=form.sort_order.data or next_sort_order(Achievement),
        )
        db.session.add(achievement)
        db.session.commit()
        flash("Achievement record added to the timeline.", "success")
        return redirect(url_for("admin.achievements"))
    return render_template("admin/achievement_form.html", form=form, achievement=None)


@admin_bp.route("/achievements/<int:achievement_id>/edit", methods=["GET", "POST"])
def achievement_edit(achievement_id: int):
    achievement = db.get_or_404(Achievement, achievement_id)
    form = AchievementForm(obj=achievement)
    if form.validate_on_submit():
        saved = _save_field_images(
            [
                (form.certificate_image, "achievements"),
                (form.event_image, "achievements"),
            ]
        )
        if saved is None:
            return render_template(
                "admin/achievement_form.html", form=form, achievement=achievement
            )
        achievement.title = form.title.data.strip()
        achievement.position = (form.position.data or "").strip()
        achievement.year = (form.year.data or "").strip()
        achievement.description = (form.description.data or "").strip()
        achievement.sort_order = (
            form.sort_order.data
            if form.sort_order.data is not None
            else achievement.sort_order
        )
        for field_name, new_path in saved.items():
            old_path = getattr(achievement, field_name)
            if new_path != old_path:
                delete_upload(old_path)
                setattr(achievement, field_name, new_path)
        db.session.commit()
        flash("Achievement record updated.", "success")
        return redirect(url_for("admin.achievements"))
    return render_template(
        "admin/achievement_form.html", form=form, achievement=achievement
    )


@admin_bp.route("/achievements/<int:achievement_id>/delete", methods=["POST"])
def achievement_delete(achievement_id: int):
    achievement = db.get_or_404(Achievement, achievement_id)
    paths = [achievement.certificate_image, achievement.event_image]
    db.session.delete(achievement)
    db.session.commit()
    delete_uploads(paths)
    flash("Achievement record removed from the timeline.", "info")
    return redirect(url_for("admin.achievements"))


@admin_bp.route(
    "/achievements/<int:achievement_id>/image/<field>/delete", methods=["POST"]
)
def achievement_image_delete(achievement_id: int, field: str):
    if field not in {"certificate_image", "event_image"}:
        abort(404)
    achievement = db.get_or_404(Achievement, achievement_id)
    path = getattr(achievement, field)
    if path:
        delete_upload(path)
        setattr(achievement, field, "")
        db.session.commit()
        flash("Achievement photograph removed.", "info")
    return redirect(url_for("admin.achievement_edit", achievement_id=achievement.id))


@admin_bp.route("/achievements/<int:achievement_id>/move/<direction>", methods=["POST"])
def achievement_move(achievement_id: int, direction: str):
    achievement = db.get_or_404(Achievement, achievement_id)
    if not move_ordered(Achievement, achievement, direction):
        flash("That record is already at the edge of the sequence.", "warning")
    return redirect(url_for("admin.achievements"))


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------
@admin_bp.route("/organizations")
def organizations():
    items = Organization.query.order_by(
        Organization.sort_order.asc(), Organization.id.asc()
    ).all()
    return render_template("admin/organizations.html", organizations=items)


@admin_bp.route("/organizations/new", methods=["GET", "POST"])
def organization_new():
    form = OrganizationForm()
    if form.validate_on_submit():
        saved = _save_field_images([(form.logo, "organizations")])
        if saved is None:
            return render_template(
                "admin/organization_form.html", form=form, organization=None
            )
        org = Organization(
            name=form.name.data.strip(),
            role=(form.role.data or "").strip(),
            description=(form.description.data or "").strip(),
            website=(form.website.data or "").strip(),
            logo=saved.get("logo", ""),
            sort_order=form.sort_order.data or next_sort_order(Organization),
        )
        db.session.add(org)
        db.session.commit()
        flash("Organization record created.", "success")
        return redirect(url_for("admin.organizations"))
    return render_template("admin/organization_form.html", form=form, organization=None)


@admin_bp.route("/organizations/<int:organization_id>/edit", methods=["GET", "POST"])
def organization_edit(organization_id: int):
    organization = db.get_or_404(Organization, organization_id)
    form = OrganizationForm(obj=organization)
    if form.validate_on_submit():
        saved = _save_field_images([(form.logo, "organizations")])
        if saved is None:
            return render_template(
                "admin/organization_form.html", form=form, organization=organization
            )
        organization.name = form.name.data.strip()
        organization.role = (form.role.data or "").strip()
        organization.description = (form.description.data or "").strip()
        organization.website = (form.website.data or "").strip()
        organization.sort_order = (
            form.sort_order.data
            if form.sort_order.data is not None
            else organization.sort_order
        )
        new_logo = saved.get("logo", "")
        if new_logo and new_logo != organization.logo:
            delete_upload(organization.logo)
            organization.logo = new_logo
        db.session.commit()
        flash("Organization record updated.", "success")
        return redirect(url_for("admin.organizations"))
    return render_template(
        "admin/organization_form.html", form=form, organization=organization
    )


@admin_bp.route("/organizations/<int:organization_id>/delete", methods=["POST"])
def organization_delete(organization_id: int):
    organization = db.get_or_404(Organization, organization_id)
    logo = organization.logo
    db.session.delete(organization)
    db.session.commit()
    delete_upload(logo)
    flash("Organization record removed.", "info")
    return redirect(url_for("admin.organizations"))


@admin_bp.route("/organizations/<int:organization_id>/logo/delete", methods=["POST"])
def organization_logo_delete(organization_id: int):
    organization = db.get_or_404(Organization, organization_id)
    if organization.logo:
        delete_upload(organization.logo)
        organization.logo = ""
        db.session.commit()
        flash("Organization logo removed.", "info")
    return redirect(url_for("admin.organization_edit", organization_id=organization.id))


@admin_bp.route("/organizations/<int:organization_id>/move/<direction>", methods=["POST"])
def organization_move(organization_id: int, direction: str):
    organization = db.get_or_404(Organization, organization_id)
    if not move_ordered(Organization, organization, direction):
        flash("That record is already at the edge of the sequence.", "warning")
    return redirect(url_for("admin.organizations"))


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
@admin_bp.route("/projects")
def projects():
    items = Project.query.order_by(
        Project.featured.desc(), Project.sort_order.asc(), Project.id.asc()
    ).all()
    return render_template("admin/projects.html", projects=items)


@admin_bp.route("/projects/new", methods=["GET", "POST"])
def project_new():
    form = ProjectForm()
    if form.validate_on_submit():
        saved_cover = _save_field_images([(form.cover_image, "projects")])
        if saved_cover is None:
            return render_template("admin/project_form.html", form=form, project=None)
        saved_images = _save_many_images(form.images.data, "projects")
        if saved_images is None:
            delete_uploads(saved_cover.values())
            return render_template("admin/project_form.html", form=form, project=None)
        project = Project(
            title=form.title.data.strip(),
            tagline=(form.tagline.data or "").strip(),
            description=(form.description.data or "").strip(),
            long_description=(form.long_description.data or "").strip(),
            tech_stack=(form.tech_stack.data or "").strip(),
            external_url=(form.external_url.data or "").strip(),
            github_url=(form.github_url.data or "").strip(),
            cover_image=saved_cover.get("cover_image", ""),
            featured=bool(form.featured.data),
            sort_order=form.sort_order.data or next_sort_order(Project),
        )
        db.session.add(project)
        db.session.flush()
        for index, image in enumerate(saved_images, start=1):
            db.session.add(
                ProjectImage(
                    project_id=project.id,
                    filename=str(image["filename"]),
                    sort_order=index,
                )
            )
        db.session.commit()
        flash("Project record created. The public archive is updated.", "success")
        return redirect(url_for("admin.projects"))
    return render_template("admin/project_form.html", form=form, project=None)


@admin_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
def project_edit(project_id: int):
    project = db.get_or_404(Project, project_id)
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        saved_cover = _save_field_images([(form.cover_image, "projects")])
        if saved_cover is None:
            return render_template(
                "admin/project_form.html", form=form, project=project
            )
        saved_images = _save_many_images(form.images.data, "projects")
        if saved_images is None:
            delete_uploads(saved_cover.values())
            return render_template(
                "admin/project_form.html", form=form, project=project
            )
        project.title = form.title.data.strip()
        project.tagline = (form.tagline.data or "").strip()
        project.description = (form.description.data or "").strip()
        project.long_description = (form.long_description.data or "").strip()
        project.tech_stack = (form.tech_stack.data or "").strip()
        project.external_url = (form.external_url.data or "").strip()
        project.github_url = (form.github_url.data or "").strip()
        project.featured = bool(form.featured.data)
        project.sort_order = (
            form.sort_order.data
            if form.sort_order.data is not None
            else project.sort_order
        )
        new_cover = saved_cover.get("cover_image", "")
        if new_cover and new_cover != project.cover_image:
            delete_upload(project.cover_image)
            project.cover_image = new_cover
        start_order = max([image.sort_order for image in project.images] or [0]) + 1
        for offset, image in enumerate(saved_images):
            db.session.add(
                ProjectImage(
                    project_id=project.id,
                    filename=str(image["filename"]),
                    sort_order=start_order + offset,
                )
            )
        db.session.commit()
        flash("Project record updated.", "success")
        return redirect(url_for("admin.projects"))
    return render_template("admin/project_form.html", form=form, project=project)


@admin_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
def project_delete(project_id: int):
    project = db.get_or_404(Project, project_id)
    paths = [project.cover_image] + [image.filename for image in project.images]
    db.session.delete(project)
    db.session.commit()
    delete_uploads(paths)
    flash("Project record and its images removed.", "info")
    return redirect(url_for("admin.projects"))


@admin_bp.route("/projects/<int:project_id>/cover/delete", methods=["POST"])
def project_cover_delete(project_id: int):
    project = db.get_or_404(Project, project_id)
    if project.cover_image:
        delete_upload(project.cover_image)
        project.cover_image = ""
        db.session.commit()
        flash("Project cover image removed.", "info")
    return redirect(url_for("admin.project_edit", project_id=project.id))


@admin_bp.route("/projects/<int:project_id>/move/<direction>", methods=["POST"])
def project_move(project_id: int, direction: str):
    project = db.get_or_404(Project, project_id)
    if not move_ordered(Project, project, direction):
        flash("That record is already at the edge of the sequence.", "warning")
    return redirect(url_for("admin.projects"))


@admin_bp.route("/projects/<int:project_id>/feature", methods=["POST"])
def project_feature(project_id: int):
    project = db.get_or_404(Project, project_id)
    project.featured = not project.featured
    db.session.commit()
    flash(
        f"{project.title} is now {'featured' if project.featured else 'unfeatured'}.",
        "success",
    )
    return redirect(url_for("admin.projects"))


@admin_bp.route("/project-images/<int:image_id>/delete", methods=["POST"])
def project_image_delete(image_id: int):
    image = db.get_or_404(ProjectImage, image_id)
    project_id = image.project_id
    filename = image.filename
    db.session.delete(image)
    db.session.commit()
    delete_upload(filename)
    flash("Project image removed.", "info")
    return redirect(url_for("admin.project_edit", project_id=project_id))


@admin_bp.route("/project-images/<int:image_id>/caption", methods=["POST"])
def project_image_caption(image_id: int):
    image = db.get_or_404(ProjectImage, image_id)
    caption = (request.form.get("caption") or "").strip()
    if len(caption) > 250:
        flash("Project image captions cannot exceed 250 characters.", "error")
    else:
        image.caption = caption
        db.session.commit()
        flash("Project image caption updated.", "success")
    return redirect(url_for("admin.project_edit", project_id=image.project_id))


@admin_bp.route("/project-images/<int:image_id>/move/<direction>", methods=["POST"])
def project_image_move(image_id: int, direction: str):
    image = db.get_or_404(ProjectImage, image_id)
    _move_sibling(
        ProjectImage,
        image,
        direction,
        ProjectImage.project_id == image.project_id,
    )
    return redirect(url_for("admin.project_edit", project_id=image.project_id))


# ---------------------------------------------------------------------------
# Collaborators
# ---------------------------------------------------------------------------
@admin_bp.route("/collaborators")
def collaborators():
    items = Collaborator.query.order_by(
        Collaborator.sort_order.asc(), Collaborator.id.asc()
    ).all()
    return render_template("admin/collaborators.html", collaborators=items)


@admin_bp.route("/collaborators/new", methods=["GET", "POST"])
def collaborator_new():
    form = CollaboratorForm()
    if form.validate_on_submit():
        saved = _save_field_images([(form.photo, "profiles")])
        if saved is None:
            return render_template(
                "admin/collaborator_form.html", form=form, collaborator=None
            )
        collaborator = Collaborator(
            name=form.name.data.strip(),
            description=(form.description.data or "").strip(),
            website=(form.website.data or "").strip(),
            photo=saved.get("photo", ""),
            sort_order=form.sort_order.data or next_sort_order(Collaborator),
        )
        db.session.add(collaborator)
        db.session.commit()
        flash("Collaborator added to the timeline.", "success")
        return redirect(url_for("admin.collaborators"))
    return render_template(
        "admin/collaborator_form.html", form=form, collaborator=None
    )


@admin_bp.route("/collaborators/<int:collaborator_id>/edit", methods=["GET", "POST"])
def collaborator_edit(collaborator_id: int):
    collaborator = db.get_or_404(Collaborator, collaborator_id)
    form = CollaboratorForm(obj=collaborator)
    if form.validate_on_submit():
        saved = _save_field_images([(form.photo, "profiles")])
        if saved is None:
            return render_template(
                "admin/collaborator_form.html", form=form, collaborator=collaborator
            )
        collaborator.name = form.name.data.strip()
        collaborator.description = (form.description.data or "").strip()
        collaborator.website = (form.website.data or "").strip()
        collaborator.sort_order = (
            form.sort_order.data
            if form.sort_order.data is not None
            else collaborator.sort_order
        )
        new_photo = saved.get("photo", "")
        if new_photo and new_photo != collaborator.photo:
            delete_upload(collaborator.photo)
            collaborator.photo = new_photo
        db.session.commit()
        flash("Collaborator record updated.", "success")
        return redirect(url_for("admin.collaborators"))
    return render_template(
        "admin/collaborator_form.html", form=form, collaborator=collaborator
    )


@admin_bp.route("/collaborators/<int:collaborator_id>/delete", methods=["POST"])
def collaborator_delete(collaborator_id: int):
    collaborator = db.get_or_404(Collaborator, collaborator_id)
    photo = collaborator.photo
    db.session.delete(collaborator)
    db.session.commit()
    delete_upload(photo)
    flash("Collaborator record removed.", "info")
    return redirect(url_for("admin.collaborators"))


@admin_bp.route("/collaborators/<int:collaborator_id>/photo/delete", methods=["POST"])
def collaborator_photo_delete(collaborator_id: int):
    collaborator = db.get_or_404(Collaborator, collaborator_id)
    if collaborator.photo:
        delete_upload(collaborator.photo)
        collaborator.photo = ""
        db.session.commit()
        flash("Collaborator photograph removed.", "info")
    return redirect(url_for("admin.collaborator_edit", collaborator_id=collaborator.id))


@admin_bp.route("/collaborators/<int:collaborator_id>/move/<direction>", methods=["POST"])
def collaborator_move(collaborator_id: int, direction: str):
    collaborator = db.get_or_404(Collaborator, collaborator_id)
    if not move_ordered(Collaborator, collaborator, direction):
        flash("That record is already at the edge of the sequence.", "warning")
    return redirect(url_for("admin.collaborators"))


# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------
@admin_bp.route("/gallery")
def gallery():
    categories = GalleryCategory.query.order_by(
        GalleryCategory.sort_order.asc(), GalleryCategory.id.asc()
    ).all()
    category_form = GalleryCategoryForm()
    return render_template(
        "admin/gallery.html",
        categories=categories,
        category_form=category_form,
        image_count=GalleryImage.query.count(),
    )


@admin_bp.route("/gallery/categories/new", methods=["POST"])
def gallery_category_new():
    form = GalleryCategoryForm()
    if form.validate_on_submit():
        category = GalleryCategory(
            name=form.name.data.strip(),
            slug=unique_slug(GalleryCategory, form.name.data),
            description=(form.description.data or "").strip(),
            sort_order=form.sort_order.data or next_sort_order(GalleryCategory),
        )
        db.session.add(category)
        try:
            db.session.commit()
            flash("Gallery category created.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("That category already exists.", "error")
    else:
        for errors in form.errors.values():
            flash(errors[0], "error")
    return redirect(url_for("admin.gallery"))


@admin_bp.route("/gallery/categories/<int:category_id>")
def gallery_category(category_id: int):
    category = db.get_or_404(GalleryCategory, category_id)
    category_form = GalleryCategoryForm(obj=category, original=category)
    return render_template(
        "admin/gallery_category.html",
        category=category,
        category_form=category_form,
        images=category.images,
    )


@admin_bp.route("/gallery/categories/<int:category_id>/edit", methods=["POST"])
def gallery_category_edit(category_id: int):
    category = db.get_or_404(GalleryCategory, category_id)
    form = GalleryCategoryForm(original=category)
    if form.validate_on_submit():
        category.name = form.name.data.strip()
        category.slug = unique_slug(
            GalleryCategory, form.name.data, ignore_id=category.id
        )
        category.description = (form.description.data or "").strip()
        category.sort_order = (
            form.sort_order.data
            if form.sort_order.data is not None
            else category.sort_order
        )
        db.session.commit()
        flash("Gallery category updated.", "success")
    else:
        for errors in form.errors.values():
            flash(errors[0], "error")
    return redirect(url_for("admin.gallery_category", category_id=category.id))


@admin_bp.route("/gallery/categories/<int:category_id>/delete", methods=["POST"])
def gallery_category_delete(category_id: int):
    category = db.get_or_404(GalleryCategory, category_id)
    paths = [image.filename for image in category.images]
    db.session.delete(category)
    db.session.commit()
    delete_uploads(paths)
    flash("Gallery category and its images removed.", "info")
    return redirect(url_for("admin.gallery"))


@admin_bp.route("/gallery/categories/<int:category_id>/move/<direction>", methods=["POST"])
def gallery_category_move(category_id: int, direction: str):
    category = db.get_or_404(GalleryCategory, category_id)
    if not move_ordered(GalleryCategory, category, direction):
        flash("That category is already at the edge of the sequence.", "warning")
    return redirect(url_for("admin.gallery"))


@admin_bp.route("/gallery/categories/<int:category_id>/upload", methods=["POST"])
def gallery_upload(category_id: int):
    category = db.get_or_404(GalleryCategory, category_id)
    files = [file for file in request.files.getlist("images") if file and file.filename]
    if not files:
        flash("Choose at least one image to upload.", "warning")
        return redirect(url_for("admin.gallery_category", category_id=category.id))
    if len(files) > current_app.config["MAX_IMAGES_PER_UPLOAD"]:
        flash(
            f"Upload at most {current_app.config['MAX_IMAGES_PER_UPLOAD']} images at once.",
            "error",
        )
        return redirect(url_for("admin.gallery_category", category_id=category.id))

    saved = _save_many_images(files, "gallery")
    if saved is None:
        return redirect(url_for("admin.gallery_category", category_id=category.id))

    start_order = max([image.sort_order for image in category.images] or [0]) + 1
    for offset, image in enumerate(saved):
        db.session.add(
            GalleryImage(
                category_id=category.id,
                filename=str(image["filename"]),
                width=int(image["width"]),
                height=int(image["height"]),
                sort_order=start_order + offset,
            )
        )
    db.session.commit()
    flash(f"{len(saved)} photograph(s) added to the public gallery.", "success")
    return redirect(url_for("admin.gallery_category", category_id=category.id))


@admin_bp.route("/gallery/images/<int:image_id>/edit", methods=["POST"])
def gallery_image_update(image_id: int):
    image = db.get_or_404(GalleryImage, image_id)
    caption = (request.form.get("caption") or "").strip()
    description = (request.form.get("description") or "").strip()
    sort_order_raw = (request.form.get("sort_order") or "").strip()
    if len(caption) > 250 or len(description) > 2000:
        flash("Caption or description exceeds the allowed length.", "error")
        return redirect(
            url_for("admin.gallery_category", category_id=image.category_id)
        )
    image.caption = caption
    image.description = description
    if sort_order_raw.isdigit():
        image.sort_order = int(sort_order_raw)
    db.session.commit()
    flash("Photograph record updated.", "success")
    return redirect(url_for("admin.gallery_category", category_id=image.category_id))


@admin_bp.route("/gallery/images/<int:image_id>/move/<direction>", methods=["POST"])
def gallery_image_move(image_id: int, direction: str):
    image = db.get_or_404(GalleryImage, image_id)
    _move_sibling(
        GalleryImage, image, direction, GalleryImage.category_id == image.category_id
    )
    return redirect(url_for("admin.gallery_category", category_id=image.category_id))


@admin_bp.route("/gallery/images/<int:image_id>/delete", methods=["POST"])
def gallery_image_delete(image_id: int):
    image = db.get_or_404(GalleryImage, image_id)
    category_id = image.category_id
    filename = image.filename
    db.session.delete(image)
    db.session.commit()
    delete_upload(filename)
    flash("Photograph removed from the public gallery.", "info")
    return redirect(url_for("admin.gallery_category", category_id=category_id))


# ---------------------------------------------------------------------------
# Easter eggs
# ---------------------------------------------------------------------------
@admin_bp.route("/easter-eggs")
def easter_eggs():
    items = EasterEgg.query.order_by(
        EasterEgg.sort_order.asc(), EasterEgg.id.asc()
    ).all()
    return render_template(
        "admin/easter_eggs.html",
        easter_eggs=items,
        access_fragment_count=sum(
            1 for egg in items if egg.enabled and egg.access_code and egg.access_slot
        ),
    )


@admin_bp.route("/easter-eggs/new", methods=["GET", "POST"])
def easter_egg_new():
    form = EasterEggForm()
    if form.validate_on_submit():
        egg = EasterEgg(
            key=form.key.data.strip(),
            title=form.title.data.strip(),
            message=form.message.data.strip(),
            section=form.section.data,
            interaction_type=form.interaction_type.data,
            access_code=(form.access_code.data or "").strip().upper(),
            access_slot=form.access_slot.data or 0,
            enabled=bool(form.enabled.data),
            sort_order=form.sort_order.data or next_sort_order(EasterEgg),
        )
        db.session.add(egg)
        db.session.commit()
        flash("Hidden record created.", "success")
        return redirect(url_for("admin.easter_eggs"))
    return render_template("admin/easter_egg_form.html", form=form, egg=None)


@admin_bp.route("/easter-eggs/<int:egg_id>/edit", methods=["GET", "POST"])
def easter_egg_edit(egg_id: int):
    egg = db.get_or_404(EasterEgg, egg_id)
    form = EasterEggForm(obj=egg, original=egg)
    if form.validate_on_submit():
        egg.key = form.key.data.strip()
        egg.title = form.title.data.strip()
        egg.message = form.message.data.strip()
        egg.section = form.section.data
        egg.interaction_type = form.interaction_type.data
        egg.access_code = (form.access_code.data or "").strip().upper()
        egg.access_slot = form.access_slot.data or 0
        egg.enabled = bool(form.enabled.data)
        egg.sort_order = (
            form.sort_order.data if form.sort_order.data is not None else egg.sort_order
        )
        db.session.commit()
        flash("Hidden record updated.", "success")
        return redirect(url_for("admin.easter_eggs"))
    return render_template("admin/easter_egg_form.html", form=form, egg=egg)


@admin_bp.route("/easter-eggs/<int:egg_id>/delete", methods=["POST"])
def easter_egg_delete(egg_id: int):
    egg = db.get_or_404(EasterEgg, egg_id)
    db.session.delete(egg)
    db.session.commit()
    flash("Hidden record deleted.", "info")
    return redirect(url_for("admin.easter_eggs"))


@admin_bp.route("/easter-eggs/<int:egg_id>/toggle", methods=["POST"])
def easter_egg_toggle(egg_id: int):
    egg = db.get_or_404(EasterEgg, egg_id)
    egg.enabled = not egg.enabled
    db.session.commit()
    flash(
        f"{egg.title} is now {'enabled' if egg.enabled else 'disabled'}.",
        "success",
    )
    return redirect(url_for("admin.easter_eggs"))


@admin_bp.route("/easter-eggs/<int:egg_id>/move/<direction>", methods=["POST"])
def easter_egg_move(egg_id: int, direction: str):
    egg = db.get_or_404(EasterEgg, egg_id)
    if not move_ordered(EasterEgg, egg, direction):
        flash("That record is already at the edge of the sequence.", "warning")
    return redirect(url_for("admin.easter_eggs"))


# ---------------------------------------------------------------------------
# Appearance
# ---------------------------------------------------------------------------
@admin_bp.route("/appearance", methods=["GET", "POST"])
def appearance():
    settings = SiteSettings.load()
    form = AppearanceForm(obj=settings)
    if form.validate_on_submit():
        new_background = settings.hero_background
        if form.hero_background.data and getattr(
            form.hero_background.data, "filename", ""
        ):
            try:
                saved = save_image(form.hero_background.data, "site")
            except UploadError as exc:
                flash(str(exc), "error")
                return render_template(
                    "admin/appearance.html", form=form, settings=settings
                )
            if saved:
                new_background = str(saved["filename"])
        for field_name, field in form._fields.items():
            if field_name in {"csrf_token", "submit", "hero_background"}:
                continue
            setattr(settings, field_name, field.data)
        if new_background != settings.hero_background:
            delete_upload(settings.hero_background)
            settings.hero_background = new_background
        db.session.commit()
        flash("Website appearance and content updated.", "success")
        return redirect(url_for("admin.appearance"))
    return render_template("admin/appearance.html", form=form, settings=settings)


@admin_bp.route("/appearance/background/delete", methods=["POST"])
def appearance_remove_background():
    settings = SiteSettings.load()
    if settings.hero_background:
        delete_upload(settings.hero_background)
        settings.hero_background = ""
        db.session.commit()
        flash("Hero background removed.", "info")
    return redirect(url_for("admin.appearance"))


# ---------------------------------------------------------------------------
# Contact messages
# ---------------------------------------------------------------------------
@admin_bp.route("/messages")
def messages():
    status = request.args.get("status", "all")
    query = ContactMessage.query
    if status == "unread":
        query = query.filter_by(is_read=False)
    elif status == "read":
        query = query.filter_by(is_read=True)
    items = query.order_by(ContactMessage.created_at.desc()).all()
    return render_template(
        "admin/messages.html",
        messages=items,
        status=status,
        unread_count=ContactMessage.query.filter_by(is_read=False).count(),
        total_count=ContactMessage.query.count(),
    )


@admin_bp.route("/messages/<int:message_id>/read", methods=["POST"])
def message_read(message_id: int):
    message = db.get_or_404(ContactMessage, message_id)
    message.is_read = True
    db.session.commit()
    referrer = request.referrer
    if referrer and is_safe_redirect_url(referrer):
        return redirect(referrer)
    return redirect(url_for("admin.messages"))


@admin_bp.route("/messages/<int:message_id>/unread", methods=["POST"])
def message_unread(message_id: int):
    message = db.get_or_404(ContactMessage, message_id)
    message.is_read = False
    db.session.commit()
    referrer = request.referrer
    if referrer and is_safe_redirect_url(referrer):
        return redirect(referrer)
    return redirect(url_for("admin.messages"))


@admin_bp.route("/messages/<int:message_id>/delete", methods=["POST"])
def message_delete(message_id: int):
    message = db.get_or_404(ContactMessage, message_id)
    db.session.delete(message)
    db.session.commit()
    flash("Message deleted from the archive.", "info")
    return redirect(url_for("admin.messages"))


@admin_bp.route("/messages/read-all", methods=["POST"])
def messages_read_all():
    ContactMessage.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All signals marked as read.", "success")
    return redirect(url_for("admin.messages"))


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------
@admin_bp.route("/account", methods=["GET", "POST"])
def account():
    form = AccountForm(obj=current_user)
    if form.validate_on_submit():
        new_username = form.username.data.strip()
        existing = Admin.query.filter(
            Admin.username == new_username, Admin.id != current_user.id
        ).first()
        if existing:
            flash("That username is already assigned to another archive administrator.", "error")
        else:
            current_user.username = new_username
            db.session.commit()
            flash("Administrator username updated.", "success")
            return redirect(url_for("admin.account"))
    return render_template("admin/account.html", form=form)


@admin_bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    form = ChangePasswordForm()
    force_change = bool(current_user.must_change_password)
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("The current password is incorrect.", "error")
        elif current_user.check_password(form.new_password.data):
            flash("The new password must be different from the current password.", "error")
        else:
            current_user.set_password(form.new_password.data)
            current_user.must_change_password = False
            db.session.commit()
            flash("Password replaced. The control room is fully activated.", "success")
            return redirect(url_for("admin.dashboard"))
    return render_template(
        "admin/change_password.html", form=form, force_change=force_change
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _save_field_images(field_map) -> dict[str, str] | None:
    """Save optional single image fields, cleaning up if any upload fails."""
    saved: dict[str, str] = {}
    try:
        for field, folder in field_map:
            name = field.name
            data = field.data
            if data and getattr(data, "filename", ""):
                result = save_image(data, folder)
                if result:
                    saved[name] = str(result["filename"])
        return saved
    except UploadError as exc:
        delete_uploads(saved.values())
        flash(str(exc), "error")
        return None


def _save_many_images(files, folder: str) -> list[dict] | None:
    """Save a list of images; all saved files are removed if one fails."""
    cleaned = [file for file in (files or []) if file and getattr(file, "filename", "")]
    if not cleaned:
        return []
    if len(cleaned) > current_app.config["MAX_IMAGES_PER_UPLOAD"]:
        flash(
            f"Upload at most {current_app.config['MAX_IMAGES_PER_UPLOAD']} images at once.",
            "error",
        )
        return None
    saved: list[dict] = []
    try:
        for file in cleaned:
            result = save_image(file, folder)
            if result:
                saved.append(result)
        return saved
    except UploadError as exc:
        delete_uploads([str(item["filename"]) for item in saved])
        flash(str(exc), "error")
        return None


def _move_sibling(model, instance, direction: str, condition) -> bool:
    if direction not in {"up", "down"}:
        return False
    siblings = list(
        db.session.execute(
            db.select(model)
            .where(condition)
            .order_by(model.sort_order.asc(), model.id.asc())
        ).scalars()
    )
    try:
        index = siblings.index(instance)
    except ValueError:
        return False
    target = index - 1 if direction == "up" else index + 1
    if target < 0 or target >= len(siblings):
        flash("That record is already at the edge of the sequence.", "warning")
        return False
    siblings[index], siblings[target] = siblings[target], siblings[index]
    for position, item in enumerate(siblings, start=1):
        item.sort_order = position
    db.session.commit()
    return True
