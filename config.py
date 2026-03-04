"""
Spaceship — Configuration

Keys are stored as bcrypt-style SHA-256 hashes in a local file,
never as plaintext in environment variables or source code.
See README for how to generate your key file.
"""

import hashlib
import os
import secrets


class Config:
    """Base configuration."""

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

    # Flask session key — auto-generated per instance, persisted to file
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Path to the file containing the SHA-256 hash of the access key
    KEY_FILE = os.path.join(INSTANCE_DIR, "access.key")

    # Database
    DATABASE_PATH = os.path.join(INSTANCE_DIR, "spaceship.db")

    # Local upload fallback (used only when Cloudinary is not configured)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # Cloudinary — free tier, 25 GB storage + 25 GB bandwidth/month
    # Set these in .env or environment; leave empty to fall back to local storage
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

    # Gallery pagination
    PHOTOS_PER_PAGE = 6

    # Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    @property
    def cloudinary_configured(self) -> bool:
        return bool(
            self.CLOUDINARY_CLOUD_NAME
            and self.CLOUDINARY_API_KEY
            and self.CLOUDINARY_API_SECRET
        )


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True


class DevelopmentConfig(Config):
    DEBUG = True
