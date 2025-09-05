# blueprints/auth/routes.py — 로그인/로그아웃/데모계정 (최종)
from __future__ import annotations
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User
from helpers.auth import _login, _logout

bp = Blueprint("auth", __name__)

@bp.get("/login", endpoint="home")  # ✅ 엔드포인트: auth.home
def login():
    if session.get("uid"):
        return redirect(url_for("dashboard.home"))
    return render_template("auth_login.html")

@bp.post("/login", endpoint="login_post")  # ✅ 엔드포인트 명시
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()

    user = db.session.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        flash("이메일 또는 비밀번호가 올바르지 않습니다.", "error")
        return redirect(url_for("auth.home"))

    ok = False
    if hasattr(user, "password_hash") and user.password_hash:
        ok = check_password_hash(user.password_hash, password)
    elif hasattr(user, "password"):
        ok = (user.password == password)

    if not ok:
        flash("이메일 또는 비밀번호가 올바르지 않습니다.", "error")
        return redirect(url_for("auth.home"))

    _login(user.id)
    flash("로그인되었습니다.", "success")

    # 간단한 오픈 리다이렉트 방지: 내부 경로만 허용
    nxt = request.args.get("next")
    if not nxt or not nxt.startswith("/") or nxt.startswith("//"):
        nxt = url_for("dashboard.home")
    return redirect(nxt)

# ✅ 로그아웃: GET/POST를 엔드포인트 분리 (405 방지)
@bp.get("/logout", endpoint="logout_get")
def logout_get():
    _logout()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("auth.home"))

@bp.post("/logout", endpoint="logout_post")
def logout_post():
    _logout()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("auth.home"))

@bp.get("/init_demo", endpoint="init_demo")
def init_demo():
    """관리자/교수/학생 3계정 자동 생성 (이미 있으면 건너뜀)"""
    created = []
    demo_users = [
        ("관리자", "admin@example.com", "admin", "admin123"),
        ("김교수", "prof@example.com", "instructor", "prof123"),
        ("홍학생", "student@example.com", "student", "student123"),
    ]
    for name, email, role, pw in demo_users:
        u = db.session.query(User).filter(func.lower(User.email) == email.lower()).first()
        if not u:
            u = User(
                name=name,
                email=email,
                role=role,
                username=email.split("@")[0],
                created_at=datetime.utcnow(),
            )
            if hasattr(User, "password_hash"):
                u.password_hash = generate_password_hash(pw)
            elif hasattr(User, "password"):
                u.password = pw
            db.session.add(u)
            created.append(email)
    if created:
        db.session.commit()

    flash(f"데모 계정 준비 완료: {', '.join(created) if created else '이미 존재함'}", "success")
    return redirect(url_for("auth.home"))