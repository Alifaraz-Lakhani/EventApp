from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from db import get_db_connection

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uid_input = request.form.get("uid").strip()
        name = request.form.get("name").strip()
        email = request.form.get("email").strip()
        phone = request.form.get("phone").strip()

        # Decide role and internal UID
        if uid_input.isdigit():
            role = "student"
            uid = f"STU_{uid_input}"
        else:
            role = "admin"
            uid = uid_input  # e.g. ADM_0001

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if user exists
        cur.execute("SELECT uid FROM users WHERE uid = %s;", (uid,))
        exists = cur.fetchone()

        if not exists:
            # Insert new user
            cur.execute(
                """
                INSERT INTO users (uid, name, email, phone, role)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (uid, name, email, phone, role)
            )
        else:
            # Update details on every login
            cur.execute(
                """
                UPDATE users
                SET name = %s,
                    email = %s,
                    phone = %s
                WHERE uid = %s;
                """,
                (name, email, phone, uid)
            )

        conn.commit()
        cur.close()
        conn.close()

        # Store session
        session["uid"] = uid
        session["name"] = name
        session["role"] = role

        flash("Logged in successfully!", "success")

        # Redirect
        if role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        else:
            return redirect(url_for("student.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
