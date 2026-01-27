from flask import Blueprint, session, redirect, url_for, render_template, request
from db import get_db_connection

student_bp = Blueprint("student", __name__)

@student_bp.route("/dashboard")
def dashboard():
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch active upcoming events
    cur.execute("""
        SELECT id, title, category, mode, event_datetime, team_size
        FROM events
        WHERE is_active = TRUE AND event_datetime > now()
        ORDER BY event_datetime;
    """)
    events = cur.fetchall()

    # Events user has joined
    cur.execute("""
        SELECT event_id
        FROM participations
        WHERE user_uid = %s;
    """, (session["uid"],))
    joined_events = {row[0] for row in cur.fetchall()}

    cur.close()
    conn.close()

    return render_template(
        "student_dashboard.html",
        events=events,
        joined_events=joined_events
    )


@student_bp.route("/participate/<int:event_id>", methods=["POST"])
def participate(event_id):
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # Insert participation (ignore duplicates safely)
    cur.execute("""
        INSERT INTO participations (user_uid, event_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING;
    """, (session["uid"], event_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("student.dashboard"))


@student_bp.route("/unenroll/<int:event_id>", methods=["POST"])
def unenroll(event_id):
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM participations
        WHERE user_uid = %s AND event_id = %s;
    """, (session["uid"], event_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("student.dashboard"))
