"""
Spaceship — Entry Point

Usage:
    python launch.py                     (development)
    gunicorn launch:app --bind 0.0.0.0   (production)
"""

import os

from app import launch

env = os.environ.get("FLASK_ENV", "development")
config_map = {
    "development": "config.DevelopmentConfig",
    "production": "config.ProductionConfig",
}
app = launch(config_map.get(env, "config.DevelopmentConfig"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=(env == "development"))
