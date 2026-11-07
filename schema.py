"""Small, idempotent schema upgrades for existing local databases.

The project intentionally keeps SQLite as its default database and does not
require a migration service for normal use. ``db.create_all()`` cannot add
columns to a table that already exists, so this module applies the few additive
changes needed by the archive puzzle without touching stored content.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

from .extensions import db

EASTER_EGG_COLUMN_UPGRADES = {
    "access_code": "VARCHAR(24) NOT NULL DEFAULT ''",
    "access_slot": "INTEGER NOT NULL DEFAULT 0",
}


def ensure_archive_schema() -> list[str]:
    """Add missing columns to an existing archive database.

    Returns the names of the columns that were added. Fresh databases are
    created by ``db.create_all()`` with the current model and need no changes.
    """
    inspector = inspect(db.engine)
    if "easter_eggs" not in inspector.get_table_names():
        return []

    existing = {column["name"] for column in inspector.get_columns("easter_eggs")}
    added: list[str] = []
    if all(name in existing for name in EASTER_EGG_COLUMN_UPGRADES):
        return added

    with db.engine.begin() as connection:
        for name, definition in EASTER_EGG_COLUMN_UPGRADES.items():
            if name in existing:
                continue
            connection.execute(
                text(f"ALTER TABLE easter_eggs ADD COLUMN {name} {definition}")
            )
            added.append(name)
    return added
