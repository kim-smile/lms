from flask import Blueprint, render_template, request
from sqlalchemy import or_, func
from helpers.auth import roles_required
from models import db, User

bp = Blueprint("users", __name__, url_prefix="/users")

@bp.get("/", endpoint="home")  # ✅ 엔드포인트: users.home
# @roles_required("admin")
def page():
    q_raw = (request.args.get("q") or "").strip()
    q = q_raw.lower()
    role = request.args.get("role", "all")

    query = db.session.query(User)
    if role in ("student", "instructor", "admin"):
        query = query.filter(User.role == role)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                func.lower(User.name).like(like),
                func.lower(User.username).like(like),
                func.lower(User.email).like(like),
                func.lower(User.phone).like(like),
            )
        )

    users = query.order_by(User.created_at.desc()).all()

    # 집계 쿼리: 전체/역할별
    role_counts = dict(
        db.session.execute(
            db.select(User.role, func.count(User.id)).group_by(User.role)
        ).all()
    )
    total_cnt = sum(role_counts.values())
    student_cnt = role_counts.get("student", 0)
    instructor_cnt = role_counts.get("instructor", 0)
    admin_cnt = role_counts.get("admin", 0)

    return render_template(
        "users.html",
        users=users,
        total_cnt=total_cnt,
        student_cnt=student_cnt,
        instructor_cnt=instructor_cnt,
        admin_cnt=admin_cnt,
        q=q_raw,
        role=role,
    )