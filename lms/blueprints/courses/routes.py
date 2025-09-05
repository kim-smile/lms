from flask import Blueprint, render_template, request, g
from sqlalchemy import func
from helpers.auth import login_required
from models import db, Course, Enrollment, Assignment, Submission

bp = Blueprint("courses", __name__, url_prefix="/courses")

@bp.get("/", endpoint="home")  # ✅ 엔드포인트: courses.home
@login_required
def index():
    uid = g.user.id
    q_raw = (request.args.get("q") or "").strip()
    q = q_raw.lower()

    # 내가 수강 중인 강좌
    base_q = (
        db.session.query(Course.id, Course.title)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == uid)
    )
    if q:
        base_q = base_q.filter(func.lower(Course.title).like(f"%{q}%"))
    courses = base_q.all()

    if not courses:
        return render_template("courses.html", courses=[], q=q_raw)

    course_ids = [cid for cid, _ in courses]

    # 강좌별 과제 수 (한 번에)
    total_by_course = {
        cid: cnt
        for cid, cnt in db.session.execute(
            db.select(Assignment.course_id, func.count(Assignment.id))
            .where(Assignment.course_id.in_(course_ids))
            .group_by(Assignment.course_id)
        ).all()
    }

    # 내 제출 수(강좌별) (한 번에)
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

    # 카드 구성
    cards = []
    for cid, title in courses:
        total = int(total_by_course.get(cid, 0))
        submitted = int(submitted_by_course.get(cid, 0))
        pct = int((submitted / total) * 100) if total else 0
        # 템플릿에서 course 객체를 기대한다면 최소 필드만 채운 얕은 객체로 대체해도 됨.
        # 여기선 id/title만 쓰는 가정으로 dict로 전달
        cards.append({
            "course": {"id": cid, "title": title},
            "total": total,
            "submitted": submitted,
            "progress": pct,
        })

    return render_template("courses.html", courses=cards, q=q_raw)