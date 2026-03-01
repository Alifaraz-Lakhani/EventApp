from flask import Blueprint, session, redirect, url_for, jsonify
from datetime import datetime, timezone
from db import get_db_connection

interest_bp = Blueprint("interest", __name__)


@interest_bp.route("/recommendations")
def recommendations():
    """Return recommended events as JSON for AJAX calls."""
    if "uid" not in session:
        return jsonify({"error": "Not logged in"}), 401

    conn = get_db_connection()
    cur = conn.cursor()

    # Get top interest categories
    cur.execute("""
        SELECT category, score FROM interest_scores
        WHERE user_uid = %s AND score > 50
        ORDER BY score DESC
        LIMIT 5;
    """, (session["uid"],))
    scores = cur.fetchall()

    recommended = []
    if scores:
        top_categories = [s[0] for s in scores]
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

        for row in cur.fetchall():
            recommended.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "category": row[3],
                "mode": row[4],
                "event_datetime": row[5].isoformat() if row[5] else None,
                "team_size": row[6]
            })

    cur.close()
    conn.close()

    return jsonify({
        "scores": [{"category": s[0], "score": s[1]} for s in scores],
        "events": recommended
    })


@interest_bp.route("/recalculate", methods=["POST"])
def recalculate():
    """Recalculate all interest scores for the current user."""
    if "uid" not in session:
        return jsonify({"error": "Not logged in"}), 401

    conn = get_db_connection()
    cur = conn.cursor()

    user_uid = session["uid"]

    # Get all distinct categories the user has participated in
    cur.execute("""
        SELECT DISTINCT e.category, COUNT(*) as freq
        FROM participations p
        JOIN events e ON p.event_id = e.id
        WHERE p.user_uid = %s
        GROUP BY e.category;
    """, (user_uid,))
    categories = cur.fetchall()

    # Total participations
    cur.execute("SELECT COUNT(*) FROM participations WHERE user_uid = %s;", (user_uid,))
    total = cur.fetchone()[0]

    for category, freq in categories:
        # Most recent participation in this category
        cur.execute("""
            SELECT MAX(p.joined_at) FROM participations p
            JOIN events e ON p.event_id = e.id
            WHERE p.user_uid = %s AND e.category = %s;
        """, (user_uid, category))
        last_participation = cur.fetchone()[0]

        # Score components
        category_match = min(100, freq * 25)
        frequency_score = min(100, (freq / max(total, 1)) * 100)

        # Recency: higher if participated recently
        if last_participation:
            days_ago = (datetime.now(timezone.utc) - last_participation.replace(tzinfo=timezone.utc)).days
            if days_ago <= 7:
                recency_score = 100
            elif days_ago <= 30:
                recency_score = 70
            elif days_ago <= 90:
                recency_score = 40
            else:
                recency_score = 10
        else:
            recency_score = 0

        score = int(0.5 * category_match + 0.3 * frequency_score + 0.2 * recency_score)
        score = min(score, 100)

        cur.execute("""
            INSERT INTO interest_scores (user_uid, category, score, updated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (user_uid, category)
            DO UPDATE SET score = EXCLUDED.score, updated_at = now();
        """, (user_uid, category, score))

        # Notification for high score
        if score > 75:
            # Check if we already sent a recent notification
            cur.execute("""
                SELECT id FROM notifications
                WHERE user_uid = %s AND type = 'recommendation'
                  AND title LIKE %s
                  AND created_at > now() - interval '1 day';
            """, (user_uid, f"%{category}%"))

            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO notifications (user_uid, title, message, type, is_read)
                    VALUES (%s, %s, %s, 'recommendation', FALSE);
                """, (
                    user_uid,
                    f"🔥 High Interest: {category}",
                    f"Your interest score in {category} is {score}%! Check out recommended events."
                ))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "ok", "message": "Scores recalculated"})
