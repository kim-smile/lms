from flask import Blueprint, render_template, request
from sqlalchemy import or_, func
from helpers.auth import roles_required
from models import db, User

bp = Blueprint("users", __name__, url_prefix="/users")

@bp.get("/", endpoint="home")
@roles_required("admin")
def page():
    q = (request.args.get("q") or "").strip()
    role = request.args.get("role", "all")
    query = db.session.query(User)
    if role in ("student", "instructor", "admin"):
        query = query.filter(User.role == role)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.name.like(like), User.username.like(like), User.email.like(like), User.phone.like(like)))
    users = query.order_by(User.created_at.desc()).all()
    total_cnt = db.session.scalar(db.select(func.count(User.id))) or 0
    student_cnt = db.session.scalar(db.select(func.count(User.id)).where(User.role == "student")) or 0
    instructor_cnt = db.session.scalar(db.select(func.count(User.id)).where(User.role == "instructor")) or 0
    admin_cnt = db.session.scalar(db.select(func.count(User.id)).where(User.role == "admin")) or 0
    return render_template(
        "users.html",
        users=users,
        total_cnt=total_cnt,
        student_cnt=student_cnt,
        instructor_cnt=instructor_cnt,
        admin_cnt=admin_cnt,
        q=q,
        role=role,
    )