from flask import Blueprint, session, redirect, url_for, render_template, request, flash
from db import get_db_connection

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/")
def list_notifications():
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, message, type, is_read, created_at
        FROM notifications
        WHERE user_uid = %s
        ORDER BY created_at DESC
        LIMIT 50;
    """, (session["uid"],))
    notifications = cur.fetchall()

    # Unread count
    cur.execute("""
        SELECT COUNT(*) FROM notifications
        WHERE user_uid = %s AND is_read = FALSE;
    """, (session["uid"],))
    notif_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template("notifications.html",
                           notifications=notifications,
                           notif_count=notif_count)


@notifications_bp.route("/read/<int:notif_id>", methods=["POST"])
def mark_read(notif_id):
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE notifications SET is_read = TRUE
        WHERE id = %s AND user_uid = %s;
    """, (notif_id, session["uid"]))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("notifications.list_notifications"))


@notifications_bp.route("/read-all", methods=["POST"])
def mark_all_read():
    if "uid" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE notifications SET is_read = TRUE
        WHERE user_uid = %s AND is_read = FALSE;
    """, (session["uid"],))

    conn.commit()
    cur.close()
    conn.close()

    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications.list_notifications"))
