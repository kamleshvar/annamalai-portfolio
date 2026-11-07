"""Public contact signalling."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..forms import ContactForm
from ..models import ContactMessage
from ..utils import AttemptLimiter

contact_bp = Blueprint("contact", __name__)
contact_limiter = AttemptLimiter(max_attempts=8, window_seconds=300)


@contact_bp.route("/contact", methods=["POST"])
def send_message():
    form = ContactForm()
    if not form.validate_on_submit():
        message = "The signal was incomplete. "
        if form.errors:
            first_field, errors = next(iter(form.errors.items()))
            message += errors[0]
        flash(message, "error")
        return redirect(url_for("main.index", _anchor="contact"))

    # Honeypot: silently accept, never write to the archive.
    if form.website.data:
        return redirect(url_for("main.index", _anchor="contact"))

    key = request.remote_addr or "unknown"
    if contact_limiter.is_locked(key):
        flash(
            "Too many signals from this coordinate. Wait a few minutes, then try again.",
            "warning",
        )
        return redirect(url_for("main.index", _anchor="contact"))
    contact_limiter.fail(key)

    message = ContactMessage(
        name=form.name.data.strip(),
        email=form.email.data.strip().lower(),
        subject=form.subject.data.strip(),
        message=form.message.data.strip(),
    )
    try:
        db.session.add(message)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("The archive could not store your signal. Please try again.", "error")
        return redirect(url_for("main.index", _anchor="contact"))

    flash(
        "Signal received. Your message is now in the archive — thank you for reaching out.",
        "success",
    )
    return redirect(url_for("main.index", _anchor="contact"))
