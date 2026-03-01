from flask import Flask, redirect, url_for, session
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY")

    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.admin import admin_bp
    from routes.notifications import notifications_bp
    from routes.teams import teams_bp
    from routes.interest import interest_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")
    app.register_blueprint(teams_bp, url_prefix="/teams")
    app.register_blueprint(interest_bp, url_prefix="/interest")

    @app.route("/")
    def index():
        if "uid" in session:
            if session.get("role") == "admin":
                return redirect(url_for("admin.admin_dashboard"))
            return redirect(url_for("student.dashboard"))
        return redirect(url_for("auth.login"))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
