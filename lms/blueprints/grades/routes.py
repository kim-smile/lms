from flask import Blueprint, render_template, g
from sqlalchemy import func
from helpers.auth import login_required
from models import db, Course, Assignment, Submission, Enrollment
from typing import Dict, Any, Optional, List

bp = Blueprint("grades", __name__, url_prefix="/grades")

@bp.get("/", endpoint="home")  # ✅ 엔드포인트: grades.home
@login_required
def page():
    uid = g.user.id

    # 내가 수강 중인 강좌 (한 번에)
    courses: List[Course] = (
        db.session.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == uid)
        .order_by(Course.title.asc())
        .all()
    )
    if not courses:
        return render_template("grades.html", cards=[], details={}, overall_avg=None)

    course_ids = [c.id for c in courses]

    # 강좌별 과제 목록 (한 번에) — 마감일 오름차순, 마감일 없는 건 뒤로
    assigns_all: List[Assignment] = (
        db.session.query(Assignment)
        .filter(Assignment.course_id.in_(course_ids))
        .order_by(Assignment.course_id.asc(), Assignment.due_at.is_(None), Assignment.due_at.asc())
        .all()
    )
    assigns_by_course: Dict[int, List[Assignment]] = {}
    for a in assigns_all:
        assigns_by_course.setdefault(a.course_id, []).append(a)

    # 내 제출 목록 (한 번에) — 과제와 조인
    subs_all: List[Submission] = (
        db.session.query(Submission)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(
            Submission.user_id == uid,
            Assignment.course_id.in_(course_ids),
        )
        .all()
    )
    # 과제ID -> 제출
    sub_by_aid: Dict[int, Submission] = {s.assignment_id: s for s in subs_all}
    # 강좌ID -> 제출 리스트
    subs_by_course: Dict[int, List[Submission]] = {}
    for s in subs_all:
        cid = s.assignment.course_id if s.assignment else None
        if cid is not None:
            subs_by_course.setdefault(cid, []).append(s)

    course_cards: List[Dict[str, Any]] = []
    details: Dict[int, List[Dict[str, Any]]] = {}
    overall_avgs: List[float] = []

    for c in courses:
        assigns = assigns_by_course.get(c.id, [])
        subs = subs_by_course.get(c.id, [])

        total = len(assigns)
        submitted_cnt = sum(1 for s in subs if s.submitted_at is not None)
        graded = [s for s in subs if s.score is not None]
        graded_cnt = len(graded)

        # 지각/정시
        ontime = late = 0
        for s in graded:
            a = s.assignment
            if a and a.due_at and s.submitted_at:
                if s.submitted_at > a.due_at:
                    late += 1
                else:
                    ontime += 1

        # 과목 평균(%) — 각 과제 만점 대비 환산 후 평균
        avg_pct: Optional[float] = None
        if graded_cnt:
            acc = 0.0
            for s in graded:
                a = s.assignment
                total_score = (a.total_score if a and a.total_score is not None else 100)
                acc += (float(s.score) / float(total_score)) * 100.0
            avg_pct = round(acc / graded_cnt, 1)
            overall_avgs.append(avg_pct)

        completion = int(round(100 * submitted_cnt / total)) if total else 0

        def letter(p: Optional[float]) -> str:
            if p is None:
                return "-"
            return "A" if p >= 90 else "B" if p >= 80 else "C" if p >= 70 else "D" if p >= 60 else "F"

        course_cards.append(
            {
                "course": c,
                "total": total,
                "submitted": submitted_cnt,
                "graded": graded_cnt,
                "ontime": ontime,
                "late": late,
                "missing": max(total - submitted_cnt, 0),
                "avg_pct": avg_pct,
                "letter": letter(avg_pct),
                "completion": completion,
            }
        )

        # 상세 표 데이터 (한 과목의 모든 과제에 대해, 내 제출을 붙여서)
        rows: List[Dict[str, Any]] = []
        for a in assigns:
            s = sub_by_aid.get(a.id)
            status = "미제출"
            pct = None
            late_badge = None

            if s and s.submitted_at:
                status = "제출"
                if a.due_at and s.submitted_at > a.due_at:
                    late_badge = "지각"

            if s and s.score is not None:
                total_score = (a.total_score if a.total_score is not None else 100)
                pct = round((float(s.score) / float(total_score)) * 100.0, 1)

            rows.append({"a": a, "s": s, "status": status, "pct": pct, "late_badge": late_badge})

        details[c.id] = rows

    overall_avg = round(sum(overall_avgs) / len(overall_avgs), 1) if overall_avgs else None
    return render_template("grades.html", cards=course_cards, details=details, overall_avg=overall_avg)