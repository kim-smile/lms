# helpers/context.py — g.user 바인딩, 공통 컨텍스트, 에러핸들러 (정리본)
from __future__ import annotations
from flask import g, request, url_for, render_template
from extensions import db
from models import Enrollment, Submission
from helpers.auth import _current_user
from services.metrics import average_score_for_user, recent_activities_for_user

def register_context_hooks(app):
    @app.before_request
    def _bind_user_to_g():
        # 로그인 여부와 무관하게 현재 사용자(데모 포함)를 g.user에 바인딩
        g.user = _current_user()

    @app.context_processor
    def inject_helpers():
        def active_exact(endpoint_or_path: str = "/"):
            p = request.path
            if endpoint_or_path.startswith("/"):
                return p == endpoint_or_path
            try:
                return p == url_for(endpoint_or_path)
            except Exception:
                return False

        def active_prefix(path_prefix: str):
            return request.path.startswith(path_prefix)

        def has_role(role: str) -> bool:
            u = g.get("user")
            return bool(u and (u.role or "student") == role)

        def any_role(*roles: str) -> bool:
            u = g.get("user")
            r = (u.role or "student") if u else "student"
            return r in roles

        def _sidebar_bundle():
            try:
                u = g.get("user")
                if not u:
                    return {"sb_stats": {"courses": 0, "completed": 0, "avg_score": None}, "sb_recent": []}

                uid = u.id
                course_count = db.session.query(Enrollment).filter_by(user_id=uid).count()
                completed_cnt = (
                    db.session.query(Submission)
                    .filter(Submission.user_id == uid, Submission.submitted_at.isnot(None))
                    .count()
                )
                avg_score = average_score_for_user(uid)
                recent = recent_activities_for_user(uid, limit=5)
                return {"sb_stats": {"courses": course_count, "completed": completed_cnt, "avg_score": avg_score},
                        "sb_recent": recent}
            except Exception:
                # 실패 시 안전한 기본값
                return {"sb_stats": {"courses": 0, "completed": 0, "avg_score": None}, "sb_recent": []}

        bundle = _sidebar_bundle()

        return dict(
            active_exact=active_exact,
            active_prefix=active_prefix,
            sb_stats=bundle["sb_stats"],
            sb_recent=bundle["sb_recent"],
            has_role=has_role,
            any_role=any_role,
            current_user=g.get("user"),
        )

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html", e=e), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html", e=e), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html", e=e), 500
