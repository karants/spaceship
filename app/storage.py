"""
Spaceship — Storage Layer

Abstracts image storage behind a common interface so the rest of the app
doesn't care whether files live on disk or in Cloudinary.

Classes:
    LocalStorage   — saves to app/static/uploads/ (development / fallback)
    CloudStorage   — uploads to Cloudinary free tier (production)

Factory:
    create_storage(app) — returns the appropriate backend based on config.
"""

import os
from abc import ABC, abstractmethod

import cloudinary
import cloudinary.api
import cloudinary.uploader


class StorageBackend(ABC):
    """Common interface every storage backend must implement."""

    @abstractmethod
    def save(self, file_storage, filename: str) -> str:
        """
        Persist *file_storage* (a Werkzeug FileStorage object).
        Returns the public URL or relative path for the saved file.
        """

    @abstractmethod
    def delete(self, reference: str) -> None:
        """Remove a previously stored file identified by *reference*."""

    @abstractmethod
    def url_for(self, reference: str) -> str:
        """Return the publicly accessible URL for *reference*."""


# ======================================================================
# Local disk storage (development / offline fallback)
# ======================================================================

class LocalStorage(StorageBackend):
    """Stores images in the local static/uploads directory."""

    def __init__(self, upload_folder: str):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    def save(self, file_storage, filename: str) -> str:
        dest = os.path.join(self.upload_folder, filename)
        file_storage.save(dest)
        return filename  # reference = just the filename

    def delete(self, reference: str) -> None:
        path = os.path.join(self.upload_folder, reference)
        if os.path.exists(path):
            os.remove(path)

    def url_for(self, reference: str) -> str:
        # Will be resolved in templates via Flask's url_for('static', ...)
        return f"/static/uploads/{reference}"


# ======================================================================
# Cloudinary storage (production — free tier: 25 GB)
# ======================================================================

class CloudStorage(StorageBackend):
    """Stores images on Cloudinary's free tier CDN."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

    def save(self, file_storage, filename: str) -> str:
        # Strip extension for the public_id
        public_id = f"spaceship/{os.path.splitext(filename)[0]}"
        result = cloudinary.uploader.upload(
            file_storage,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
        # reference = the full public_id (used for deletion & URL)
        return result["public_id"]

    def delete(self, reference: str) -> None:
        try:
            cloudinary.uploader.destroy(reference, resource_type="image")
        except Exception:
            pass  # best-effort deletion

    def url_for(self, reference: str) -> str:
        return cloudinary.CloudinaryImage(reference).build_url(
            secure=True,
            quality="auto",
            fetch_format="auto",
        )


# ======================================================================
# Factory
# ======================================================================

def create_storage(app) -> StorageBackend:
    """
    Return the appropriate storage backend based on the app config.
    Falls back to local disk if Cloudinary credentials are absent.
    """
    cfg = app.config
    if (
        cfg.get("CLOUDINARY_CLOUD_NAME")
        and cfg.get("CLOUDINARY_API_KEY")
        and cfg.get("CLOUDINARY_API_SECRET")
    ):
        return CloudStorage(
            cfg["CLOUDINARY_CLOUD_NAME"],
            cfg["CLOUDINARY_API_KEY"],
            cfg["CLOUDINARY_API_SECRET"],
        )
    return LocalStorage(cfg["UPLOAD_FOLDER"])
