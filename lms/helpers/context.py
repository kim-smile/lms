# helpers/context.py — g.user 바인딩, 공통 컨텍스트, 에러핸들러
from __future__ import annotations
from flask import g, request, url_for, render_template
from sqlalchemy import func
from extensions import db
from models import Enrollment, Submission, User
from helpers.auth import _current_user, _session_uid
from services.metrics import average_score_for_user, recent_activities_for_user

def register_context_hooks(app):
    @app.before_request
    def _bind_user_to_g():
        g.user = _current_user()

    @app.context_processor
    def inject_helpers():
        def active_exact(endpoint_or_path='/'):
            p = request.path
            if endpoint_or_path.startswith('/'):
                return p == endpoint_or_path
            try:
                return p == url_for(endpoint_or_path)
            except Exception:
                return False

        def active_prefix(path_prefix):
            return request.path.startswith(path_prefix)

        def has_role(role: str) -> bool:
            u = g.get("user")
            return (u and (u.role or "student") == role)

        def any_role(*roles: str) -> bool:
            u = g.get("user")
            r = (u.role or "student") if u else "student"
            return r in roles

        def _sidebar_bundle():
            try:
                uid = _session_uid() or 1
                course_count = db.session.query(Enrollment).filter_by(user_id=uid).count()
                completed_cnt = (
                    db.session.query(Submission)
                    .filter(Submission.user_id == uid, Submission.submitted_at.isnot(None))
                    .count()
                )
                avg_score = average_score_for_user(uid)
                recent = recent_activities_for_user(uid, limit=5)
                return {"sb_stats": {"courses": course_count, "completed": completed_cnt, "avg_score": avg_score}, "sb_recent": recent}
            except Exception:
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
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500