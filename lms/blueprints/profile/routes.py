from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from sqlalchemy import func
from helpers.auth import login_required
from models import db, User, Enrollment, Submission, UserSetting

bp = Blueprint("profile", __name__, url_prefix="/profile")

@bp.get("/", endpoint="home")  # ✅ 엔드포인트: profile.home
@login_required
def page():
    user = g.user
    uid = user.id

    enrolled_cnt = db.session.query(Enrollment).filter_by(user_id=uid).count()
    submitted_cnt = (
        db.session.query(Submission)
        .filter(Submission.user_id == uid, Submission.submitted_at.isnot(None))
        .count()
    )
    avg_score = db.session.scalar(
        db.select(func.avg(Submission.score)).where(
            Submission.user_id == uid, Submission.score.isnot(None)
        )
    )
    avg_score = round(float(avg_score), 1) if avg_score is not None else None

    return render_template(
        "profile.html",
        user=user,
        enrolled_cnt=enrolled_cnt,
        submitted_cnt=submitted_cnt,
        avg_score=avg_score,
    )

@bp.post("/update")
@login_required
def update():
    user = g.user
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    username = (request.form.get("username") or "").strip()

    errors = []
    if not name:
        errors.append("이름은 필수입니다.")
    if not email:
        errors.append("이메일은 필수입니다.")
    else:
        # 대소문자 무시 중복 체크
        exists = (
            db.session.query(User)
            .filter(func.lower(User.email) == email.lower(), User.id != user.id)
            .first()
        )
        if exists:
            errors.append("이미 사용 중인 이메일입니다.")

    if errors:
        flash(" / ".join(errors), "error")
        return redirect(url_for("profile.home"))  # ✅ 엔드포인트 일치

    user.name = name
    user.email = email
    user.phone = phone or None
    user.username = username or None
    db.session.commit()
    flash("프로필이 저장되었습니다.", "success")
    return redirect(url_for("profile.home"))  # ✅

@bp.get("/settings", endpoint="settings_page")  # 명시적으로 고정
@login_required
def settings_page():
    uid = g.user.id
    s = db.session.query(UserSetting).filter_by(user_id=uid).first()
    if not s:
        s = UserSetting(user_id=uid)
        db.session.add(s)
        db.session.commit()
    return render_template("settings.html", s=s)

@bp.post("/settings/update")
@login_required
def settings_update():
    uid = g.user.id
    s = db.session.query(UserSetting).filter_by(user_id=uid).first()
    if not s:
        s = UserSetting(user_id=uid)
        db.session.add(s)

    s.language = (request.form.get("language") or "ko").strip()
    s.theme = (request.form.get("theme") or "light").strip()
    s.timezone = (request.form.get("timezone") or "Asia/Seoul").strip()
    s.email_notifications = bool(request.form.get("email_notifications"))
    s.push_notifications = bool(request.form.get("push_notifications"))
    s.updated_at = __import__("datetime").datetime.utcnow()

    db.session.commit()
    flash("설정이 저장되었습니다.", "success")
    return redirect(url_for("profile.settings_page"))  # 그대로 유지