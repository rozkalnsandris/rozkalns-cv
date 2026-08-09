from __future__ import annotations

import atexit

from app import close_app_services, create_app as create_base_app


def create_app():
    app = create_base_app()
    atexit.register(close_app_services, app)
    return app
