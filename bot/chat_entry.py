from __future__ import annotations

import atexit
from logging.config import dictConfig

from app import close_app_services, create_app as create_base_app


def _configure_application_logging() -> None:
    """Emit CVBot INFO telemetry to the WSGI error stream exactly once."""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                }
            },
            "handlers": {
                "wsgi": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://flask.logging.wsgi_errors_stream",
                    "formatter": "default",
                }
            },
            "loggers": {
                create_base_app.__module__: {
                    "level": "INFO",
                    "handlers": ["wsgi"],
                    "propagate": False,
                }
            },
        }
    )


def create_app():
    _configure_application_logging()
    app = create_base_app()
    atexit.register(close_app_services, app)
    return app
