from flask import Blueprint, session, redirect, url_for, render_template, request, flash
from db import get_db_connection
from datetime import datetime

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
def admin_dashboard():
    if "uid" not in session or session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT e.id, e.title, e.category, e.event_datetime, e.is_active,
               COUNT(p.id) AS participant_count
        FROM events e
        LEFT JOIN participations p ON e.id = p.event_id
        GROUP BY e.id
        ORDER BY e.event_datetime;
    """)
    events = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin_dashboard.html", events=events)


# Add event
@admin_bp.route("/event/add", methods=["GET", "POST"])
def add_event():
    if "uid" not in session or session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        category = request.form.get("category")
        mode = request.form.get("mode")
        event_datetime = request.form.get("event_datetime")
        team_size = request.form.get("team_size")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO events (title, description, category, mode, event_datetime, team_size, created_by, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE);
        """, (title, description, category, mode, event_datetime, team_size, session["uid"]))

        conn.commit()
        cur.close()
        conn.close()

        flash("Event created successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))

    return render_template("admin_add_event.html")


# Edit event
@admin_bp.route("/event/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    if "uid" not in session or session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        category = request.form.get("category")
        mode = request.form.get("mode")
        event_datetime = request.form.get("event_datetime")
        team_size = request.form.get("team_size")

        cur.execute("""
            UPDATE events
            SET title=%s,
                description=%s,
                category=%s,
                mode=%s,
                event_datetime=%s,
                team_size=%s
            WHERE id=%s;
        """, (title, description, category, mode, event_datetime, team_size, event_id))

        conn.commit()
        cur.close()
        conn.close()

        flash("Event updated successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))

    # GET – load existing event
    cur.execute("SELECT id, title, description, category, mode, event_datetime, team_size FROM events WHERE id = %s;", (event_id,))
    event = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("admin_edit_event.html", event=event)


# Delete event (soft delete)
@admin_bp.route("/event/delete/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    if "uid" not in session or session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE events
        SET is_active = FALSE
        WHERE id = %s;
    """, (event_id,))

    conn.commit()
    cur.close()
    conn.close()

    flash("Event deleted.", "info")
    return redirect(url_for("admin.admin_dashboard"))
