from flask import Blueprint, session, redirect, url_for, render_template, request, flash
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
        SELECT id, title, description, category, mode, event_datetime, team_size
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

    # Unread notification count
    cur.execute("""
        SELECT COUNT(*) FROM notifications
        WHERE user_uid = %s AND is_read = FALSE;
    """, (session["uid"],))
    notif_count = cur.fetchone()[0]

    # Interest recommendations (top scored categories > 50)
    recommendations = []
    recommended_events = []
    try:
        cur.execute("""
            SELECT category, score FROM interest_scores
            WHERE user_uid = %s AND score > 50
            ORDER BY score DESC
            LIMIT 5;
        """, (session["uid"],))
        recommendations = cur.fetchall()

        # Get recommended events based on high-score categories
        if recommendations:
            top_categories = [r[0] for r in recommendations]
            placeholders = ','.join(['%s'] * len(top_categories))
            cur.execute(f"""
                SELECT id, title, description, category, mode, event_datetime, team_size
                FROM events
                WHERE is_active = TRUE
                  AND event_datetime > now()
                  AND category IN ({placeholders})
                  AND id NOT IN (
                      SELECT event_id FROM participations WHERE user_uid = %s
                  )
                ORDER BY event_datetime
                LIMIT 6;
            """, (*top_categories, session["uid"]))
            recommended_events = cur.fetchall()
    except Exception:
        conn.rollback()  # Reset the transaction after the error

    cur.close()
    conn.close()

    return render_template(
        "student_dashboard.html",
        events=events,
        joined_events=joined_events,
        notif_count=notif_count,
        recommendations=recommendations,
        recommended_events=recommended_events
    )


@student_bp.route("/my-events")
def my_events():
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT e.id, e.title, e.description, e.category, e.mode, e.event_datetime, e.team_size
        FROM events e
        JOIN participations p ON e.id = p.event_id
        WHERE p.user_uid = %s AND e.is_active = TRUE
        ORDER BY e.event_datetime;
    """, (session["uid"],))
    events = cur.fetchall()

    # Unread notification count
    cur.execute("""
        SELECT COUNT(*) FROM notifications
        WHERE user_uid = %s AND is_read = FALSE;
    """, (session["uid"],))
    notif_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template("my_events.html", events=events, notif_count=notif_count)


@student_bp.route("/participate/<int:event_id>", methods=["POST"])
def participate(event_id):
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO participations (user_uid, event_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING;
    """, (session["uid"], event_id))

    # Update interest scores after participation (gracefully skip if table missing)
    try:
        cur.execute("SELECT category FROM events WHERE id = %s;", (event_id,))
        row = cur.fetchone()
        if row:
            category = row[0]
            _update_interest_score(cur, session["uid"], category)
    except Exception:
        conn.rollback()

    conn.commit()
    cur.close()
    conn.close()

    flash("You have registered for the event!", "success")
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

    flash("You have unenrolled from the event.", "info")
    return redirect(url_for("student.dashboard"))


def _update_interest_score(cur, user_uid, category):
    """Recalculate interest score for a specific category after participation."""
    # Count participations in this category
    cur.execute("""
        SELECT COUNT(*) FROM participations p
        JOIN events e ON p.event_id = e.id
        WHERE p.user_uid = %s AND e.category = %s;
    """, (user_uid, category))
    freq = cur.fetchone()[0]

    # Total participations across all categories
    cur.execute("""
        SELECT COUNT(*) FROM participations WHERE user_uid = %s;
    """, (user_uid,))
    total = cur.fetchone()[0]

    # Score: category_match (50%) + frequency (30%) + recency bonus (20%)
    category_match = min(100, freq * 25)  # each participation adds 25, caps at 100
    frequency_score = min(100, (freq / max(total, 1)) * 100)
    recency_score = 80  # recent participation gets a flat bonus

    score = int(0.5 * category_match + 0.3 * frequency_score + 0.2 * recency_score)
    score = min(score, 100)

    # Upsert into interest_scores
    cur.execute("""
        INSERT INTO interest_scores (user_uid, category, score, updated_at)
        VALUES (%s, %s, %s, now())
        ON CONFLICT (user_uid, category)
        DO UPDATE SET score = EXCLUDED.score, updated_at = now();
    """, (user_uid, category, score))

    # If score > 75, create a notification
    if score > 75:
        cur.execute("""
            INSERT INTO notifications (user_uid, title, message, type, is_read)
            VALUES (%s, %s, %s, 'recommendation', FALSE);
        """, (
            user_uid,
            f"🔥 High Interest: {category}",
            f"Your interest score in {category} is {score}%! Check out recommended events."
        ))
