from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from sqlalchemy import or_
from helpers.auth import login_required
from helpers.utils import _parse_dt
from models import db, Course, Assignment, Enrollment, CalendarEvent

bp = Blueprint("schedule", __name__, url_prefix="/schedule")

@bp.get("/", endpoint="home")
@login_required
def page():
    uid = g.user.id
    days = int(request.args.get("days", 30))
    start_param = request.args.get("start")
    end_param = request.args.get("end")
    q = (request.args.get("q") or "").strip()
    include_assign = request.args.get("assign", "1") == "1"

    now = datetime.utcnow()
    start = _parse_dt(start_param) or now
    end = _parse_dt(end_param) or (now + timedelta(days=days))

    ev_q = (
        db.session.query(CalendarEvent)
        .filter(
            CalendarEvent.start_at >= start,
            CalendarEvent.start_at <= end,
            or_(CalendarEvent.user_id == None, CalendarEvent.user_id == uid),
        )
    )
    if q:
        like = f"%{q}%"
        ev_q = ev_q.filter(
            or_(
                CalendarEvent.title.like(like),
                CalendarEvent.location.like(like),
                CalendarEvent.description.like(like),
            )
        )
    events = ev_q.order_by(CalendarEvent.start_at.asc()).all()

    items = [{
        "id": e.id, "kind": e.kind or "event", "title": e.title,
        "course": e.course.title if e.course else None,
        "start": e.start_at, "end": e.end_at, "location": e.location, "is_event": True,
    } for e in events]

    if include_assign:
        arows = (
            db.session.query(Assignment, Course)
            .join(Course, Course.id == Assignment.course_id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(
                Enrollment.user_id == uid,
                Assignment.due_at.isnot(None),
                Assignment.due_at >= start,
                Assignment.due_at <= end,
            ).all()
        )
        for a, c in arows:
            items.append({
                "id": None, "kind": "assignment", "title": a.title, "course": c.title,
                "start": a.due_at, "end": None, "location": None, "is_event": False
            })

    items.sort(key=lambda x: (x["start"] or datetime.max))

    my_courses = (
        db.session.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == uid)
        .order_by(Course.title.asc())
        .all()
    )

    return render_template("schedule.html",
        items=items, start=start, end=end, q=q, include_assign=include_assign, courses=my_courses
    )

@bp.post("/new")
@login_required
def new():
    uid = g.user.id
    title = (request.form.get("title") or "").strip()
    start_at = request.form.get("start_at")
    end_at = request.form.get("end_at")
    location = (request.form.get("location") or "").strip()
    kind = (request.form.get("kind") or "event").strip()
    course_id = request.form.get("course_id")
    description = (request.form.get("description") or "").strip()

    if not title or not start_at:
        flash("제목과 시작 일시는 필수입니다.", "error")
        return redirect(url_for("schedule.page"))

    sdt = _parse_dt(start_at)
    edt = _parse_dt(end_at) if end_at else None
    if not sdt:
        flash("시작 일시 형식이 올바르지 않습니다.", "error")
        return redirect(url_for("schedule.page"))
    if end_at and not edt:
        flash("종료 일시 형식이 올바르지 않습니다.", "error")
        return redirect(url_for("schedule.page"))

    cid = int(course_id) if course_id and course_id.isdigit() else None

    ev = CalendarEvent(
        user_id=uid, course_id=cid, title=title, start_at=sdt, end_at=edt,
        location=location or None, kind=kind or "event",
        description=description or None, source="manual",
    )
    db.session.add(ev)
    db.session.commit()
    flash("일정이 추가되었습니다.", "success")
    return redirect(url_for("schedule.page"))

@bp.post("/delete/<int:event_id>")
@login_required
def delete(event_id: int):
    uid = g.user.id
    ev = db.session.get(CalendarEvent, event_id)
    if not ev or not (ev.user_id is None or ev.user_id == uid):
        abort(404)
    db.session.delete(ev)
    db.session.commit()
    flash("일정이 삭제되었습니다.", "success")
    return redirect(url_for("schedule.page"))