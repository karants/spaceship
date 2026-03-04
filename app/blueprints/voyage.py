"""
Spaceship — Voyage Blueprint

Public-facing routes.  No authentication required.
    /                → launch pad (landing page)
    /mission-log     → identity / about
    /our-earth       → photography gallery with pagination
"""

import math

from flask import Blueprint, current_app, render_template, request

voyage_bp = Blueprint("voyage", __name__)


@voyage_bp.route("/")
def launchpad():
    """Landing page with navigation cards."""
    mission = current_app.extensions["mission_log_model"].get()
    return render_template("voyage/launchpad.html", mission=mission)


@voyage_bp.route("/mission-log")
def mission_log():
    """The 'Who Am I' page — personal identity transmission."""
    mission = current_app.extensions["mission_log_model"].get()
    storage = current_app.extensions["storage"]
    return render_template(
        "voyage/mission_log.html", mission=mission, storage=storage,
    )


@voyage_bp.route("/our-earth")
def our_earth():
    """Photography gallery with server-side pagination."""
    photo_model = current_app.extensions["earth_photo_model"]
    storage = current_app.extensions["storage"]
    per_page = current_app.config["PHOTOS_PER_PAGE"]

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    total = photo_model.count()
    total_pages = max(1, math.ceil(total / per_page))
    page = min(page, total_pages)
    photos = photo_model.paginate(page, per_page)

    return render_template(
        "voyage/our_earth.html",
        photos=photos,
        page=page,
        total_pages=total_pages,
        storage=storage,
    )
