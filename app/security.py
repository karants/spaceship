"""
Spaceship — Security Layer

CSRF tokens, input sanitisation, file-based key authentication,
secure filename generation, and HTTP security headers.
"""

import functools
import hashlib
import hmac
import html
import os
import secrets
import time
from typing import Callable

from flask import (
    Response,
    abort,
    current_app,
    redirect,
    request,
    session,
    url_for,
)


# ======================================================================
# CSRF Protection
# ======================================================================

def generate_csrf_token() -> str:
    """Return a per-session CSRF token, creating one if absent."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf_token() -> None:
    """Abort 403 when the submitted token doesn't match the session."""
    token = request.form.get("_csrf_token", "")
    expected = session.get("_csrf_token", "")
    if not expected or not hmac.compare_digest(token, expected):
        abort(403, "CSRF validation failed.")


# ======================================================================
# Input Sanitisation
# ======================================================================

def sanitise(value: str, max_length: int = 5000) -> str:
    """HTML-escape user input and clamp to *max_length* characters."""
    return html.escape(value[:max_length], quote=True)


def allowed_file(filename: str, allowed: set[str]) -> bool:
    """Return True if *filename* has an extension in *allowed*."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def secure_filename(filename: str) -> str:
    """
    Replace the original filename with a hash to prevent path traversal.
    Preserves the lowercase extension only.
    """
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()
    unique = hashlib.sha256(
        f"{time.time()}{secrets.token_hex(8)}".encode()
    ).hexdigest()[:16]
    return f"{unique}{ext}"


# ======================================================================
# File-Based Key Authentication
# ======================================================================

def _read_key_file() -> tuple[str, str] | None:
    """Read salt:hash from the key file.  Returns (salt, hash) or None."""
    key_path = current_app.config["KEY_FILE"]
    if not os.path.isfile(key_path):
        return None
    with open(key_path) as f:
        line = f.readline().strip()
    if ":" not in line:
        return None
    salt, digest = line.split(":", 1)
    return salt, digest


def verify_access_key(plaintext: str) -> bool:
    """
    Compare *plaintext* against the stored salted SHA-256 hash.
    Uses hmac.compare_digest to prevent timing attacks.
    """
    pair = _read_key_file()
    if pair is None:
        return False
    salt, expected_hash = pair
    candidate = hashlib.sha256((salt + plaintext).encode("utf-8")).hexdigest()
    return hmac.compare_digest(candidate, expected_hash)


def crew_only(f: Callable) -> Callable:
    """Decorator — redirects to the Ground Station login if unauthenticated."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("crew_authenticated"):
            return redirect(url_for("groundstation.login"))
        return f(*args, **kwargs)
    return decorated


# ======================================================================
# Security Headers
# ======================================================================

def apply_security_headers(response: Response) -> Response:
    """Attach hardened HTTP headers to every response."""
    h = response.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["X-XSS-Protection"] = "1; mode=block"
    h["Referrer-Policy"] = "strict-origin-when-cross-origin"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    h["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://res.cloudinary.com; "
        "frame-ancestors 'none';"
    )
    return response
