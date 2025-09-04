from flask import Blueprint, render_template, request, g
from sqlalchemy import func
from helpers.auth import login_required
from models import db, Course, Enrollment, Assignment, Submission

bp = Blueprint("courses", __name__, url_prefix="/courses")

@bp.get("/", endpoint="home")
@login_required
def index():
    q = (request.args.get("q") or "").strip()
    uid = g.user.id
    query = (
        db.session.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == uid)
    )
    if q:
        like = f"%{q}%"
        query = query.filter(Course.title.like(like))
    rows = query.all()

    cards = []
    for c in rows:
        total = db.session.query(Assignment).filter_by(course_id=c.id).count()
        submitted = (
            db.session.query(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .filter(
                Submission.user_id == uid,
                Assignment.course_id == c.id,
                Submission.submitted_at.isnot(None),
            ).count()
        )
        pct = int((submitted / total) * 100) if total else 0
        cards.append({"course": c, "total": total, "submitted": submitted, "progress": pct})

    return render_template("courses.html", courses=cards, q=q)