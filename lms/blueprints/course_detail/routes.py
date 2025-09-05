from flask import Blueprint, render_template, request, abort, g
from sqlalchemy import func
from helpers.auth import login_required
from models import db, Course, Assignment, Submission, Enrollment

bp = Blueprint("course_detail", __name__, url_prefix="/course")

@bp.get("/<int:course_id>", endpoint="detail")  # ✅ 엔드포인트: course_detail.detail
@login_required
def detail(course_id: int):
    uid = g.user.id
    tab = (request.args.get("tab") or "materials").strip().lower()
    # 탭 화이트리스트(필요시 템플릿과 맞춰 확장)
    if tab not in {"materials", "assignments", "notices", "discussion"}:
        tab = "materials"

    # 강좌 조회 & 수강 여부 확인
    course = db.session.get(Course, course_id)
    if not course:
        abort(404, description="강좌를 찾을 수 없습니다.")

    enrolled = (
        db.session.query(Enrollment.id)
        .filter_by(user_id=uid, course_id=course.id)
        .first()
    )
    if not enrolled:
        abort(403)

    # 과제 수/제출 수 → 진행률
    total = db.session.query(Assignment).filter_by(course_id=course.id).count()
    submitted = (
        db.session.query(Submission)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(
            Submission.user_id == uid,
            Assignment.course_id == course.id,
            Submission.submitted_at.isnot(None),
        )
        .count()
    )
    progress_pct = int((submitted / total) * 100) if total else 0

    # 과제 목록 (마감일 오름차순, 마감일 없는 건 뒤로)
    assignments = (
        db.session.query(Assignment)
        .filter_by(course_id=course.id)
        .order_by(Assignment.due_at.is_(None), Assignment.due_at.asc())  # ✅ NULLS LAST 유사
        .all()
    )

    # 내 제출 맵
    subs = (
        db.session.query(Submission)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(Submission.user_id == uid, Assignment.course_id == course.id)
        .all()
    )
    sub_map = {s.assignment_id: s for s in subs}

    # 데모용 정적 섹션 (실데이터로 교체 가능)
    materials = [
        {"week": 1, "title": "1주차: HTML 기초", "duration": "45분", "status": "완료"},
        {"week": 2, "title": "2주차: CSS 스타일링", "duration": "50분", "status": "완료"},
        {"week": 3, "title": "3주차: JavaScript 기초", "duration": "60분", "status": "진행중"},
        {"week": None, "title": "실습 자료 - HTML 템플릿", "size": "2.5MB", "download": True},
    ]
    notices = [
        {"title": "중간고사 안내", "date": "2025-03-05", "pin": True},
        {"title": "실습 자료 업데이트", "date": "2025-02-28", "pin": False},
    ]
    discussion = [
        {"title": "1주차 과제 질문 스레드", "comments": 12, "updated": "2시간 전"},
        {"title": "프로젝트 팀 편성", "comments": 8, "updated": "1일 전"},
    ]

    return render_template(
        "course_detail.html",
        course=course,
        tab=tab,
        progress_pct=progress_pct,
        assignments=assignments,
        sub_map=sub_map,
        materials=materials,
        notices=notices,
        discussion=discussion,
    )