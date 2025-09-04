# helpers/utils.py — 업로드/날짜파싱/Jinja 필터
from __future__ import annotations
import os
from datetime import datetime, date
from typing import Optional
from flask import Flask, current_app
from werkzeug.utils import secure_filename
from config import Config

ALLOWED_EXTS = Config.ALLOWED_EXTS
UPLOAD_DIR = Config.UPLOAD_DIR
DATE_ONLY = Config.DATE_ONLY
DATE_HM = Config.DATE_HM
DATE_T = Config.DATE_T

os.makedirs(UPLOAD_DIR, exist_ok=True)


def allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS


def parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    for fmt in (DATE_T, DATE_HM, DATE_ONLY):
        try:
            dt = datetime.strptime(s, fmt)
            if fmt == DATE_ONLY:
                dt = dt.replace(hour=0, minute=0)
            return dt
        except Exception:
            continue
    return None


def save_upload(file_storage, *, prefix: str) -> Optional[str]:
    if not file_storage or not file_storage.filename:
        return None
    if not allowed(file_storage.filename):
        return None
    fname = secure_filename(file_storage.filename)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    uniq = f"{prefix}_{ts}_{fname}"
    file_storage.save(os.path.join(UPLOAD_DIR, uniq))
    return f"/static/uploads/{uniq}"


def register_jinja_filters(app: Flask) -> None:
    @app.template_filter('timeago_kr')
    def timeago_kr(dt):
        if not dt:
            return ''
        now = datetime.utcnow()
        diff = now - dt
        s = int(diff.total_seconds())
        if s < 60:
            return f"{s}초 전" if s > 0 else "방금"
        m = s // 60
        if m < 60:
            return f"{m}분 전"
        h = m // 60
        if h < 24:
            return f"{h}시간 전"
        d = h // 24
        return f"{d}일 전"

    @app.template_filter("dt_kr")
    def dt_kr(v, fmt="%Y-%m-%d %H:%M"):
        if v is None:
            return ""
        try:
            if isinstance(v, (datetime, date)):
                return v.strftime(fmt)
            return str(v)
        except Exception:
            return ""

    @app.template_filter("ymd_kr")
    def ymd_kr(v):
        return dt_kr(v, "%Y-%m-%d")

    @app.template_filter("ymd_hm_kr")
    def ymd_hm_kr(v):
        return dt_kr(v, "%Y-%m-%d %H:%M")


# --------------------------------------------------------------------
# 멘토링 블루프린트에서 사용하는 간단 업로드 도우미 (_save_upload)
# --------------------------------------------------------------------
def _save_upload(file_storage, subdir: str = "uploads"):
    """
    파일 업로드 저장 도우미.
    file_storage: Flask의 request.files['file'] 같은 객체
    subdir: 저장할 하위 디렉토리명 (기본 'uploads')
    """
    if not file_storage or not file_storage.filename:
        return None

    # 안전한 파일명 확보
    filename = secure_filename(file_storage.filename)

    # 저장 경로 준비
    upload_dir = os.path.join(current_app.root_path, "static", subdir)
    os.makedirs(upload_dir, exist_ok=True)

    # 실제 저장
    save_path = os.path.join(upload_dir, filename)
    file_storage.save(save_path)

    # 웹에서 접근 가능한 경로 반환
    return f"/static/{subdir}/{filename}"

_parse_dt = parse_dt