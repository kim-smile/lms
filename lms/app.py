# app.py — 앱 팩토리 + 블루프린트 등록
from flask import Flask
from config import Config
from extensions import db
from helpers.utils import register_jinja_filters
from helpers.context import register_context_hooks

# 블루프린트
from blueprints.auth.routes import bp as auth_bp
from blueprints.dashboard.routes import bp as dashboard_bp

# ⬇️ 추가
from blueprints.courses.routes import bp as courses_bp
from blueprints.mentoring.routes import bp as mentoring_bp
from blueprints.users.routes import bp as users_bp
from blueprints.analytics.routes import bp as analytics_bp
from blueprints.messages.routes import bp as messages_bp
from blueprints.schedule.routes import bp as schedule_bp
from blueprints.assignments.routes import bp as assignments_bp
from blueprints.grades.routes import bp as grades_bp
from blueprints.profile.routes import bp as profile_bp
from blueprints.settings.routes import bp as settings_bp

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # 확장 초기화
    db.init_app(app)

    # Jinja 필터/컨텍스트
    register_jinja_filters(app)
    register_context_hooks(app)

    # 블루프린트 등록
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5004, use_reloader=False)