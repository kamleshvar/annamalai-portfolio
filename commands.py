"""Custom Flask CLI commands."""
from __future__ import annotations

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import Admin
from .schema import ensure_archive_schema
from .seed import seed_database


def register_commands(app) -> None:
    @app.cli.command("init-db")
    @click.option("--no-seed", is_flag=True, help="Create tables without demo content.")
    @with_appcontext
    def init_db(no_seed: bool) -> None:
        """Create database tables and seed the initial archive."""
        db.create_all()
        added_columns = ensure_archive_schema()
        if not no_seed:
            created = seed_database(backfill_access_fragments=bool(added_columns))
            click.echo("Database ready.")
            click.echo(
                "Created: "
                + ", ".join(f"{name}={count}" for name, count in created.items())
            )
        else:
            click.echo("Database tables created without seed content.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.password_option(confirmation_prompt=True)
    @with_appcontext
    def create_admin(username: str, password: str) -> None:
        """Create an administrator securely (passwords are hashed)."""
        username = username.strip()
        if len(username) < 3 or len(username) > 40:
            raise click.ClickException("Username must be 3–40 characters.")
        if Admin.query.filter_by(username=username).first():
            raise click.ClickException("That username already exists.")
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        admin = Admin(username=username, must_change_password=False)
        admin.password_hash = generate_password_hash(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Administrator '{username}' created.")

    @app.cli.command("set-admin-password")
    @click.option("--username", default=None, help="Defaults to the first administrator.")
    @click.password_option(confirmation_prompt=True)
    @with_appcontext
    def set_admin_password(username: str | None, password: str) -> None:
        """Reset an administrator password from the server console."""
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        query = Admin.query
        if username:
            query = query.filter_by(username=username)
        admin = query.order_by(Admin.id).first()
        if not admin:
            raise click.ClickException("No administrator found.")
        admin.set_password(password)
        admin.must_change_password = False
        db.session.commit()
        click.echo("Password updated. Existing sessions remain valid until expiry.")
