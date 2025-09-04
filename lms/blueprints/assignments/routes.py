from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from sqlalchemy import func
from helpers.auth import login_required
from helpers.utils import _save_upload
from models import db, Course, Assignment, Submission, Enrollment
from datetime import datetime

bp = Blueprint("assignments", __name__, url_prefix="/assignments")

@bp.get("/", endpoint="home")
@login_required
def index():
    uid = g.user.id
    rows = (
        db.session.query(Assignment, Course)
        .join(Course, Course.id == Assignment.course_id)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == uid)
        .order_by(Assignment.due_at.is_(None), Assignment.due_at.asc())
        .all()
    )
    subs = db.session.query(Submission).filter(Submission.user_id == uid).all()
    sub_map = {s.assignment_id: s for s in subs}
    return render_template("assignments.html", rows=rows, sub_map=sub_map)

@bp.post("/submit/<int:aid>")
@login_required
def submit(aid: int):
    uid = g.user.id
    # 내 과제 여부 확인
    enrolled = (
        db.session.query(Assignment.id, Assignment.due_at)
        .join(Course, Assignment.course_id == Course.id)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == uid, Assignment.id == aid)
        .first()
    )
    if not enrolled:
        abort(403)

    file = request.files.get("file")
    comment = (request.form.get("comment") or "").strip()

    file_url = _save_upload(file, prefix=f"u{uid}_a{aid}") if file else None
    if file and not file_url:
        flash("허용되지 않은 파일 형식입니다.", "error")
        return redirect(url_for("assignments.index"))

    # upsert
    sub = db.session.query(Submission).filter_by(assignment_id=aid, user_id=uid).first()
    now = datetime.utcnow()
    if not sub:
        sub = Submission(assignment_id=aid, user_id=uid)
        db.session.add(sub)
    if file_url:
        sub.file_url = file_url
    if comment:
        sub.comment = comment
    sub.submitted_at = now
    sub.updated_at = now
    db.session.commit()

    due_at = enrolled.due_at
    flash("제출되었습니다. (지각 제출)" if (due_at and now > due_at) else "제출되었습니다.", "success")
    return redirect(url_for("assignments.index"))