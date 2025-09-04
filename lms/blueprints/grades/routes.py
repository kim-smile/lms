from flask import Blueprint, render_template, g
from sqlalchemy import func
from helpers.auth import login_required
from models import db, Course, Assignment, Submission, Enrollment
from typing import Dict, Any, Optional

bp = Blueprint("grades", __name__, url_prefix="/grades")

@bp.get("/", endpoint="home")
@login_required
def page():
    uid = g.user.id
    courses = (
        db.session.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == uid)
        .order_by(Course.title.asc())
        .all()
    )

    course_cards = []
    details: Dict[int, list[Dict[str, Any]]] = {}
    overall_avgs = []

    for c in courses:
        assigns = (
            db.session.query(Assignment)
            .filter(Assignment.course_id == c.id)
            .order_by(func.isnull(Assignment.due_at), Assignment.due_at.asc())
            .all()
        )
        subs = (
            db.session.query(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .filter(Submission.user_id == uid, Assignment.course_id == c.id)
            .all()
        )
        sub_map = {s.assignment_id: s for s in subs}

        total = len(assigns)
        submitted = len([s for s in subs if s.submitted_at is not None])
        graded = [s for s in subs if s.score is not None]
        graded_cnt = len(graded)

        ontime = late = 0
        for s in graded:
            if s.assignment and s.assignment.due_at and s.submitted_at:
                if s.submitted_at > s.assignment.due_at:
                    late += 1
                else:
                    ontime += 1

        avg_pct: Optional[float] = None
        if graded_cnt:
            acc = 0.0
            for s in graded:
                total_score = s.assignment.total_score or 100
                acc += (float(s.score) / float(total_score)) * 100.0
            avg_pct = round(acc / graded_cnt, 1)
            overall_avgs.append(avg_pct)

        completion = int(round(100 * submitted / total)) if total else 0

        def letter(p: Optional[float]) -> str:
            if p is None: return "-"
            return "A" if p >= 90 else "B" if p >= 80 else "C" if p >= 70 else "D" if p >= 60 else "F"

        course_cards.append(
            {
                "course": c,
                "total": total,
                "submitted": submitted,
                "graded": graded_cnt,
                "ontime": ontime,
                "late": late,
                "missing": max(total - submitted, 0),
                "avg_pct": avg_pct,
                "letter": letter(avg_pct),
                "completion": completion,
            }
        )

        rows = []
        for a in assigns:
            s = sub_map.get(a.id)
            status = "미제출"
            pct = None
            late_badge = None
            if s and s.submitted_at:
                status = "제출"
                if a.due_at and s.submitted_at > a.due_at:
                    late_badge = "지각"
            if s and s.score is not None:
                pct = round((s.score / float(a.total_score or 100)) * 100.0, 1)
            rows.append({"a": a, "s": s, "status": status, "pct": pct, "late_badge": late_badge})
        details[c.id] = rows

    overall_avg = round(sum(overall_avgs) / len(overall_avgs), 1) if overall_avgs else None
    return render_template("grades.html", cards=course_cards, details=details, overall_avg=overall_avg)