# blueprints/dashboard/routes.py — 학생 대시보드(임시 공용)
from __future__ import annotations
from flask import Blueprint, render_template
from sqlalchemy import func
from extensions import db
from models import Course, Enrollment, Assignment, Submission
from helpers.auth import login_required, _session_uid
from services.metrics import (
    assignment_progress_for_user,
    average_score_for_user,
    recent_activities_for_user,
)

bp = Blueprint("dashboard", __name__)

@bp.get("/", endpoint="home")  # ✅ 엔드포인트: dashboard.home (루트는 항상 "/")
@login_required
def dashboard():
    uid = _session_uid() or 1

    # 상단 카드 메트릭
    course_count = db.session.query(Enrollment).filter_by(user_id=uid).count()
    progress_pct, submitted_cnt, total_cnt = assignment_progress_for_user(uid)
    avg_score = average_score_for_user(uid)

    # 내가 수강 중인 코스 목록
    courses = db.session.execute(
        db.select(Course.id, Course.title)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.user_id == uid)
    ).all()
    course_ids = [cid for cid, _ in courses]

    # 코스별 과제 총수
    total_by_course = {}
    if course_ids:
        total_by_course = {
            cid: cnt
            for cid, cnt in db.session.execute(
                db.select(Assignment.course_id, func.count(Assignment.id))
                .where(Assignment.course_id.in_(course_ids))
                .group_by(Assignment.course_id)
            ).all()
        }

    # 코스별 내가 제출한 과제 수(제출 완료 기준)
    submitted_by_course = {}
    if course_ids:
        submitted_by_course = {
            cid: cnt
            for cid, cnt in db.session.execute(
                db.select(Assignment.course_id, func.count(Submission.id))
                .join(Assignment, Assignment.id == Submission.assignment_id)
                .where(
                    Assignment.course_id.in_(course_ids),
                    Submission.user_id == uid,
                    Submission.submitted_at.isnot(None),
                )
                .group_by(Assignment.course_id)
            ).all()
        }

    # 진행률 바 데이터
    bars = []
    for cid, title in courses:
        total_c = int(total_by_course.get(cid, 0))
        submitted_c = int(submitted_by_course.get(cid, 0))
        pct = int((submitted_c / total_c) * 100) if total_c else 0
        bars.append({"course": {"id": cid, "title": title}, "pct": pct})

    # 예정/최근 활동
    upcoming = []  # TODO: 필요 시 구현
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