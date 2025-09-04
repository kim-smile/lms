# blueprints/dashboard/routes.py — 학생 대시보드(임시 공용)
from __future__ import annotations
from flask import Blueprint, render_template
from sqlalchemy import func
from extensions import db
from models import Course, Enrollment, Assignment, Submission
from helpers.auth import login_required, _session_uid
from services.metrics import assignment_progress_for_user, average_score_for_user, recent_activities_for_user

bp = Blueprint("dashboard", __name__)

@bp.route("")
@login_required
def dashboard():
    uid = _session_uid() or 1

    course_count = db.session.query(Enrollment).filter_by(user_id=uid).count()
    progress_pct, submitted_cnt, total_cnt = assignment_progress_for_user(uid)
    avg_score = average_score_for_user(uid)

    # 코스별 진행률 바
    bars = []
    courses = (
        db.session.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == uid)
        .all()
    )
    for c in courses:
        total_c = db.session.query(Assignment).filter_by(course_id=c.id).count()
        submitted_c = (
            db.session.query(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .filter(
                Submission.user_id == uid,
                Assignment.course_id == c.id,
                Submission.submitted_at.isnot(None),
            )
            .count()
        )
        pct = int((submitted_c / total_c) * 100) if total_c else 0
        bars.append({"course": c, "pct": pct})

    upcoming = []  # 필요 시 추가
    recent = recent_activities_for_user(uid, limit=5)

    return render_template(
        "dashboard.html",
        course_count=course_count,
        progress_pct=progress_pct,
        submitted_cnt=submitted_cnt,
        total_cnt=total_cnt,
        avg_score=avg_score,
        bars=bars,
        upcoming=upcoming,
        recent=recent,
    )