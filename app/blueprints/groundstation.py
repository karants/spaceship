"""
Spaceship — Ground Station Blueprint

Protected control panel at /groundstation.
Uses file-based hashed key authentication (no env-var passwords).

Routes:
    /groundstation/              → login
    /groundstation/command-deck  → dashboard
    /groundstation/logout        → end session
    /groundstation/mission-log/edit
    /groundstation/gallery/add
    /groundstation/gallery/<id>/edit
    /groundstation/gallery/<id>/delete
"""

import os

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..security import (
    allowed_file,
    crew_only,
    sanitise,
    secure_filename,
    validate_csrf_token,
    verify_access_key,
)

groundstation_bp = Blueprint(
    "groundstation",
    __name__,
    template_folder="../templates/groundstation",
)


# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------

@groundstation_bp.route("/", methods=["GET", "POST"])
def login():
    if session.get("crew_authenticated"):
        return redirect(url_for("groundstation.command_deck"))

    error = None
    if request.method == "POST":
        validate_csrf_token()
        key = request.form.get("key", "")
        if verify_access_key(key):
            session["crew_authenticated"] = True
            session.permanent = True
            return redirect(url_for("groundstation.command_deck"))
        error = "Access denied — invalid key."

    return render_template("groundstation/login.html", error=error)


@groundstation_bp.route("/logout")
@crew_only
def logout():
    session.clear()
    return redirect(url_for("groundstation.login"))


# ------------------------------------------------------------------
# Command Deck (Dashboard)
# ------------------------------------------------------------------

@groundstation_bp.route("/command-deck")
@crew_only
def command_deck():
    mission = current_app.extensions["mission_log_model"].get()
    photos = current_app.extensions["earth_photo_model"].get_all()
    storage = current_app.extensions["storage"]
    return render_template(
        "groundstation/command_deck.html",
        mission=mission,
        photos=photos,
        storage=storage,
    )


# ------------------------------------------------------------------
# Mission Log Management
# ------------------------------------------------------------------

@groundstation_bp.route("/mission-log/edit", methods=["GET", "POST"])
@crew_only
def edit_mission_log():
    model = current_app.extensions["mission_log_model"]
    storage = current_app.extensions["storage"]

    if request.method == "POST":
        validate_csrf_token()
        heading = sanitise(request.form.get("heading", ""))
        body = sanitise(request.form.get("body", ""), max_length=10000)

        photo_ref = None
        file = request.files.get("photo")
        if file and file.filename:
            exts = current_app.config["ALLOWED_EXTENSIONS"]
            if not allowed_file(file.filename, exts):
                flash("Invalid file type.", "error")
                return redirect(url_for("groundstation.edit_mission_log"))
            fname = secure_filename(file.filename)
            # Delete old photo if replacing
            old = model.get()
            if old.get("photo_ref"):
                storage.delete(old["photo_ref"])
            photo_ref = storage.save(file, fname)

        model.update(heading, body, photo_ref)
        flash("Mission Log updated.", "success")
        return redirect(url_for("groundstation.command_deck"))

    mission = model.get()
    return render_template("groundstation/edit_mission_log.html", mission=mission)


# ------------------------------------------------------------------
# Gallery CRUD
# ------------------------------------------------------------------

@groundstation_bp.route("/gallery/add", methods=["GET", "POST"])
@crew_only
def add_photo():
    storage = current_app.extensions["storage"]

    if request.method == "POST":
        validate_csrf_token()
        file = request.files.get("photo")
        if not file or not file.filename:
            flash("No file selected.", "error")
            return redirect(url_for("groundstation.add_photo"))

        exts = current_app.config["ALLOWED_EXTENSIONS"]
        if not allowed_file(file.filename, exts):
            flash("Invalid file type.", "error")
            return redirect(url_for("groundstation.add_photo"))

        fname = secure_filename(file.filename)
        reference = storage.save(file, fname)

        caption = sanitise(request.form.get("caption", ""))
        try:
            sort_order = int(request.form.get("sort_order", 0))
        except ValueError:
            sort_order = 0

        current_app.extensions["earth_photo_model"].create(
            reference, caption, sort_order,
        )
        flash("Photo transmitted to gallery.", "success")
        return redirect(url_for("groundstation.command_deck"))

    return render_template("groundstation/photo_form.html", photo=None, action="Transmit")


@groundstation_bp.route("/gallery/<int:photo_id>/edit", methods=["GET", "POST"])
@crew_only
def edit_photo(photo_id: int):
    photo_model = current_app.extensions["earth_photo_model"]
    storage = current_app.extensions["storage"]
    photo = photo_model.get(photo_id)
    if not photo:
        flash("Photo not found.", "error")
        return redirect(url_for("groundstation.command_deck"))

    if request.method == "POST":
        validate_csrf_token()
        caption = sanitise(request.form.get("caption", ""))
        try:
            sort_order = int(request.form.get("sort_order", 0))
        except ValueError:
            sort_order = 0

        new_ref = None
        file = request.files.get("photo")
        if file and file.filename:
            exts = current_app.config["ALLOWED_EXTENSIONS"]
            if not allowed_file(file.filename, exts):
                flash("Invalid file type.", "error")
                return redirect(
                    url_for("groundstation.edit_photo", photo_id=photo_id)
                )
            fname = secure_filename(file.filename)
            new_ref = storage.save(file, fname)
            storage.delete(photo["reference"])

        photo_model.update(photo_id, caption, sort_order, new_ref)
        flash("Photo updated.", "success")
        return redirect(url_for("groundstation.command_deck"))

    return render_template(
        "groundstation/photo_form.html", photo=photo, action="Update",
    )


@groundstation_bp.route("/gallery/<int:photo_id>/delete", methods=["POST"])
@crew_only
def delete_photo(photo_id: int):
    validate_csrf_token()
    photo_model = current_app.extensions["earth_photo_model"]
    storage = current_app.extensions["storage"]
    old_ref = photo_model.delete(photo_id)
    if old_ref:
        storage.delete(old_ref)
    flash("Photo removed from gallery.", "success")
    return redirect(url_for("groundstation.command_deck"))
