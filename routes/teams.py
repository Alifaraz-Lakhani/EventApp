from flask import Blueprint, session, redirect, url_for, render_template, request, flash
from db import get_db_connection

teams_bp = Blueprint("teams", __name__)


@teams_bp.route("/<int:event_id>")
def team_pool(event_id):
    """Browse the team pool for a specific event."""
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # Get event info
    cur.execute("SELECT id, title, team_size FROM events WHERE id = %s;", (event_id,))
    event = cur.fetchone()

    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("student.dashboard"))

    # Get all pool entries for this event
    cur.execute("""
        SELECT tp.id, tp.user_uid, u.name, tp.skills, tp.looking_for_role, tp.current_team_size, tp.created_at
        FROM team_pool tp
        JOIN users u ON tp.user_uid = u.uid
        WHERE tp.event_id = %s
        ORDER BY tp.created_at DESC;
    """, (event_id,))
    pool = cur.fetchall()

    # Check if current user is already in the pool
    cur.execute("""
        SELECT id FROM team_pool
        WHERE event_id = %s AND user_uid = %s;
    """, (event_id, session["uid"]))
    user_in_pool = cur.fetchone()

    # Get pending requests sent by this user for this event
    cur.execute("""
        SELECT to_user_uid FROM team_requests
        WHERE from_user_uid = %s AND event_id = %s AND status = 'pending';
    """, (session["uid"], event_id))
    sent_requests = {row[0] for row in cur.fetchall()}

    # Get incoming requests for this user for this event
    cur.execute("""
        SELECT tr.id, tr.from_user_uid, u.name, tr.status, tr.created_at
        FROM team_requests tr
        JOIN users u ON tr.from_user_uid = u.uid
        WHERE tr.to_user_uid = %s AND tr.event_id = %s
        ORDER BY tr.created_at DESC;
    """, (session["uid"], event_id))
    incoming_requests = cur.fetchall()

    # Unread notification count
    cur.execute("""
        SELECT COUNT(*) FROM notifications
        WHERE user_uid = %s AND is_read = FALSE;
    """, (session["uid"],))
    notif_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template("team_pool.html",
                           event=event,
                           pool=pool,
                           user_in_pool=user_in_pool,
                           sent_requests=sent_requests,
                           incoming_requests=incoming_requests,
                           notif_count=notif_count)


@teams_bp.route("/join/<int:event_id>", methods=["POST"])
def join_pool(event_id):
    """Add current user to the team pool for an event."""
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    skills = request.form.get("skills", "").strip()
    looking_for_role = request.form.get("looking_for_role", "").strip()
    current_team_size = request.form.get("current_team_size", 1)

    conn = get_db_connection()
    cur = conn.cursor()

    # Check if already in pool
    cur.execute("""
        SELECT id FROM team_pool WHERE event_id = %s AND user_uid = %s;
    """, (event_id, session["uid"]))

    if cur.fetchone():
        flash("You're already in the team pool for this event.", "info")
    else:
        cur.execute("""
            INSERT INTO team_pool (event_id, user_uid, current_team_size, skills, looking_for_role)
            VALUES (%s, %s, %s, %s, %s);
        """, (event_id, session["uid"], current_team_size, skills, looking_for_role))
        flash("You've joined the team pool!", "success")

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("teams.team_pool", event_id=event_id))


@teams_bp.route("/leave/<int:event_id>", methods=["POST"])
def leave_pool(event_id):
    """Remove current user from the team pool."""
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM team_pool WHERE event_id = %s AND user_uid = %s;
    """, (event_id, session["uid"]))

    conn.commit()
    cur.close()
    conn.close()

    flash("You've left the team pool.", "info")
    return redirect(url_for("teams.team_pool", event_id=event_id))


@teams_bp.route("/request/<int:pool_id>", methods=["POST"])
def send_request(pool_id):
    """Send a team-up request to another user in the pool."""
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # Get the pool entry to find the target user and event
    cur.execute("""
        SELECT user_uid, event_id FROM team_pool WHERE id = %s;
    """, (pool_id,))
    pool_entry = cur.fetchone()

    if not pool_entry:
        flash("Pool entry not found.", "error")
        cur.close()
        conn.close()
        return redirect(url_for("student.dashboard"))

    to_user_uid = pool_entry[0]
    event_id = pool_entry[1]

    if to_user_uid == session["uid"]:
        flash("You can't send a request to yourself.", "error")
        cur.close()
        conn.close()
        return redirect(url_for("teams.team_pool", event_id=event_id))

    # Check for existing pending request
    cur.execute("""
        SELECT id FROM team_requests
        WHERE from_user_uid = %s AND to_user_uid = %s AND event_id = %s AND status = 'pending';
    """, (session["uid"], to_user_uid, event_id))

    if cur.fetchone():
        flash("You've already sent a request to this user.", "info")
    else:
        cur.execute("""
            INSERT INTO team_requests (from_user_uid, to_user_uid, event_id, status)
            VALUES (%s, %s, %s, 'pending');
        """, (session["uid"], to_user_uid, event_id))

        # Send notification to the target user
        cur.execute("SELECT name FROM users WHERE uid = %s;", (session["uid"],))
        sender_name = cur.fetchone()[0]

        cur.execute("SELECT title FROM events WHERE id = %s;", (event_id,))
        event_title = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO notifications (user_uid, title, message, type, is_read)
            VALUES (%s, %s, %s, 'team_request', FALSE);
        """, (
            to_user_uid,
            f"🤝 Team Request for {event_title}",
            f"{sender_name} wants to team up with you for {event_title}!"
        ))

        flash("Team request sent!", "success")

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("teams.team_pool", event_id=event_id))


@teams_bp.route("/respond/<int:request_id>", methods=["POST"])
def respond_request(request_id):
    """Accept or reject a team-up request."""
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    action = request.form.get("action")  # 'accept' or 'reject'

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT from_user_uid, to_user_uid, event_id FROM team_requests WHERE id = %s;
    """, (request_id,))
    req = cur.fetchone()

    if not req or req[1] != session["uid"]:
        flash("Invalid request.", "error")
        cur.close()
        conn.close()
        return redirect(url_for("student.dashboard"))

    from_user_uid = req[0]
    event_id = req[2]

    new_status = "accepted" if action == "accept" else "rejected"
    cur.execute("""
        UPDATE team_requests SET status = %s WHERE id = %s;
    """, (new_status, request_id))

    # Notify the requester
    cur.execute("SELECT name FROM users WHERE uid = %s;", (session["uid"],))
    responder_name = cur.fetchone()[0]

    cur.execute("SELECT title FROM events WHERE id = %s;", (event_id,))
    event_title = cur.fetchone()[0]

    emoji = "✅" if action == "accept" else "❌"
    cur.execute("""
        INSERT INTO notifications (user_uid, title, message, type, is_read)
        VALUES (%s, %s, %s, 'team_response', FALSE);
    """, (
        from_user_uid,
        f"{emoji} Team Request {new_status.title()}",
        f"{responder_name} has {new_status} your team request for {event_title}."
    ))

    conn.commit()
    cur.close()
    conn.close()

    flash(f"Request {new_status}.", "success" if action == "accept" else "info")
    return redirect(url_for("teams.team_pool", event_id=event_id))
