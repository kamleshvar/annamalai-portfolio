"""Local development entry point.

Run:
    python run.py

For production use a WSGI server, for example:
    waitress-serve --listen=0.0.0.0:8000 run:app
"""
from __future__ import annotations

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = bool(app.config.get("DEBUG", False))
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=port,
        debug=debug,
        use_reloader=debug,
    )
