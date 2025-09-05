# blueprints/settings/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from helpers.auth import login_required
from models import db, UserSetting
from datetime import datetime

bp = Blueprint("settings", __name__, url_prefix="/settings")

@bp.get("/", endpoint="home")
@login_required
def home():
    uid = g.user.id
    s = db.session.query(UserSetting).filter_by(user_id=uid).first()
    if not s:
        s = UserSetting(user_id=uid)
        db.session.add(s)
        db.session.commit()
    return render_template("settings.html", s=s)

@bp.post("/update", endpoint="settings_update")
@login_required
def update():
    uid = g.user.id
    s = db.session.query(UserSetting).filter_by(user_id=uid).first()
    if not s:
        s = UserSetting(user_id=uid)
        db.session.add(s)

    # 폼 값 반영
    s.language = (request.form.get("language") or "ko").strip()
    s.theme = (request.form.get("theme") or "light").strip()
    s.timezone = (request.form.get("timezone") or "Asia/Seoul").strip()
    s.email_notifications = bool(request.form.get("email_notifications"))
    s.push_notifications = bool(request.form.get("push_notifications"))
    s.updated_at = datetime.utcnow()

    db.session.commit()
    flash("설정이 저장되었습니다.", "success")
    return redirect(url_for("settings.home"))