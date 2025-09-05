# app.py — 앱 팩토리 + 블루프린트 등록
from flask import Flask, redirect, url_for, request, session
from config import Config
from extensions import db
from helpers.utils import register_jinja_filters
from helpers.context import register_context_hooks

# 블루프린트 import
from blueprints.auth.routes import bp as auth_bp
from blueprints.dashboard.routes import bp as dashboard_bp
from blueprints.courses.routes import bp as courses_bp
from blueprints.course_detail.routes import bp as course_detail_bp
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

    # 1) 로그인/인증 블루프린트 먼저
    app.register_blueprint(auth_bp)

    # 2) 나머지 기능들
    app.register_blueprint(dashboard_bp)          # "/" (대시보드)
    app.register_blueprint(courses_bp)
    app.register_blueprint(course_detail_bp)
    app.register_blueprint(mentoring_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(assignments_bp)
    app.register_blueprint(grades_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(settings_bp)

    # --- ✅ 루트 접근 시: 로그인 여부에 따라 분기 ---
    @app.route("/")
    def _root_redirect():
        if session.get("uid"):
            return redirect(url_for("dashboard.home"))
        return redirect(url_for("auth.home"))

    # --- ✅ 전역 가드: auth.* / static 제외 모두 로그인 필요 ---
    @app.before_request
    def _require_login_globally():
        # 정적 파일은 통과
        if request.endpoint == "static":
            return

        # 허용 엔드포인트 화이트리스트
        allowed = {
            "auth.home",          # GET /login
            "auth.login_post",    # POST /login
            "auth.logout_get",   # ✅ 추가
            "auth.logout",        # GET /logout
            "auth.init_demo",     # GET /init_demo
        }

        ep = (request.endpoint or "").strip()

        # 로그인 페이지/인증 관련은 허용
        if ep in allowed or ep.startswith("auth."):
            return

        # 그 외는 모두 로그인 필요
        if not session.get("uid"):
            # next 파라미터로 원래 가려던 곳 전달
            nxt = request.full_path if request.query_string else request.path
            return redirect(url_for("auth.home", next=nxt))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5004, use_reloader=False)