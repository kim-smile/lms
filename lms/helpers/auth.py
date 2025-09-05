# helpers/auth.py — 세션 로그인/권한 데코레이터 (수정본)
from __future__ import annotations
from datetime import datetime
from functools import wraps
from typing import Optional, Callable
from flask import session, flash, redirect, url_for, request, abort, g
from extensions import db
from models import User
from config import Config

DEMO_USER_ID = Config.DEMO_USER_ID


def _login(user_id: int):
    session["uid"] = user_id
    session.permanent = True
    session["ts"] = datetime.utcnow().isoformat()


def _logout():
    session.pop("uid", None)
    session.pop("ts", None)


def _session_uid() -> Optional[int]:
    uid = session.get("uid")
    if isinstance(uid, int):
        return uid
    try:
        return int(uid) if uid is not None else None
    except Exception:
        return None


def _current_user() -> Optional[User]:
    uid = _session_uid() or DEMO_USER_ID
    return db.session.get(User, uid)


def login_required(view: Callable):
    @wraps(view)
    def _wrapped(*args, **kwargs):
        uid = _session_uid()
        if not uid:
            flash("로그인이 필요합니다.", "error")
            # ✅ 로그인 엔드포인트명 수정: auth.home
            return redirect(url_for("auth.home", next=request.full_path))
        # 인증 통과 시 g.user 보장
        g.user = _current_user()
        return view(*args, **kwargs)
    return _wrapped


def roles_required(*roles: str):
    def deco(view: Callable):
        @wraps(view)
        def _wrapped(*args, **kwargs):
            uid = _session_uid()
            if not uid:
                flash("로그인이 필요합니다.", "error")
                # ✅ 로그인 엔드포인트명 수정: auth.home
                return redirect(url_for("auth.home", next=request.full_path))
            u = _current_user()
            g.user = u  # 역할 검사 전에 g.user 세팅
            role = (u.role or "student") if u else "student"
            if role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return _wrapped
    return deco