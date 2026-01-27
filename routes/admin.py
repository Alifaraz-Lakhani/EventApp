from flask import Blueprint, session, redirect, url_for, render_template, request
from db import get_db_connection
from datetime import datetime

admin_bp = Blueprint("admin", __name__)

# Admin dashboard – list all events
@admin_bp.route("/")
def admin_dashboard():
    if "uid" not in session or session.get("role") != "admin":
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, category, event_datetime, is_active
        FROM events
        ORDER BY event_datetime;
    """)
    events = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin_dashboard.html", events=events)


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
            WHERE id=%s AND event_datetime > now();
        """, (title, description, category, mode, event_datetime, team_size, event_id))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("admin.admin_dashboard"))

    # GET – load existing event
    cur.execute("SELECT * FROM events WHERE id = %s;", (event_id,))
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

    return redirect(url_for("admin.admin_dashboard"))
