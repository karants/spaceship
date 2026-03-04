"""
Spaceship — Application Factory

Assembles the Flask app: database, storage backend, security headers,
Jinja globals, and blueprint registration.
"""

import os

from flask import Flask

from .database import Database, EarthPhotoModel, MissionLogModel
from .security import apply_security_headers, generate_csrf_token
from .storage import create_storage


def launch(config_name: str = "config.DevelopmentConfig") -> Flask:
    """Create and configure the Spaceship Flask application."""

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )
    app.config.from_object(config_name)

    # ---- Database ----
    db = Database.get_instance(app.config["DATABASE_PATH"])
    db.init_schema()
    app.extensions["db"] = db
    app.extensions["mission_log_model"] = MissionLogModel(db)
    app.extensions["earth_photo_model"] = EarthPhotoModel(db)

    # ---- Storage backend ----
    storage = create_storage(app)
    app.extensions["storage"] = storage

    # ---- Upload directory (local fallback) ----
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ---- Security headers on every response ----
    app.after_request(apply_security_headers)

    # ---- Jinja template globals ----
    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    
    from datetime import datetime

    def timestamp_to_date(value):
        return datetime.fromtimestamp(value).strftime("%B %Y")

    app.jinja_env.filters["timestamp_to_date"] = timestamp_to_date

    # ---- Blueprints ----
    from .blueprints.voyage import voyage_bp
    from .blueprints.groundstation import groundstation_bp

    app.register_blueprint(voyage_bp)
    app.register_blueprint(groundstation_bp, url_prefix="/groundstation")

    return app
