# helpers/utils.py — 업로드/날짜파싱/Jinja 필터 (정리본)
from __future__ import annotations
import os
from datetime import datetime, date
from typing import Optional
from flask import Flask
from werkzeug.utils import secure_filename
from config import Config

ALLOWED_EXTS = {ext.lower() for ext in Config.ALLOWED_EXTS}
UPLOAD_DIR = Config.UPLOAD_DIR  # e.g., "<app_root>/static/uploads"
DATE_ONLY = Config.DATE_ONLY
DATE_HM = Config.DATE_HM
DATE_T = Config.DATE_T

# 업로드 디렉토리 보장
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------------------------------------------------
# 기본 유틸
# --------------------------------------------------------------------
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

# --------------------------------------------------------------------
# 업로드: 단일 구현으로 통일 (레거시 호환)
# - prefix: 파일명 앞에 붙일 식별자 (옵션)
# - subdir: UPLOAD_DIR 하위에 추가로 분류하고 싶을 때 사용 (옵션)
# 반환: 웹 경로 (예: "/static/uploads/<subdir?>/<filename>")
# --------------------------------------------------------------------
def save_upload(file_storage, *, prefix: Optional[str] = None, subdir: Optional[str] = None) -> Optional[str]:
    """
    file_storage: Flask의 request.files[...] 객체
    prefix: 파일명 앞에 붙일 식별자 (예: 'u1_a23')
    subdir: UPLOAD_DIR 하위 추가 디렉토리 (예: 'reports')
    """
    if not file_storage or not getattr(file_storage, "filename", None):
        return None

    if not allowed(file_storage.filename):
        return None

    # 저장 경로 계산
    base_dir = UPLOAD_DIR  # Config에서 지정한 정적 업로드 루트
    if subdir:
        base_dir = os.path.join(base_dir, subdir)
    os.makedirs(base_dir, exist_ok=True)

    # 고유 파일명 생성
    orig = secure_filename(file_storage.filename)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    name_parts = [p for p in [prefix, ts, orig] if p]
    unique_name = "_".join(name_parts)

    save_path = os.path.join(base_dir, unique_name)
    file_storage.save(save_path)

    # 웹 경로 구성: UPLOAD_DIR이 "<app_root>/static/uploads" 라는 전제
    # subdir이 있으면 "/static/uploads/<subdir>/<name>", 없으면 "/static/uploads/<name>"
    web_base = "/static/uploads"
    if subdir:
        return f"{web_base}/{subdir}/{unique_name}"
    return f"{web_base}/{unique_name}"

# 레거시 별칭 유지 (다른 블루프린트에서 _save_upload(prefix=...) 호출)
_save_upload = save_upload
_parse_dt = parse_dt

# --------------------------------------------------------------------
# Jinja 필터
# --------------------------------------------------------------------
def register_jinja_filters(app: Flask) -> None:
    @app.template_filter("timeago_kr")
    def timeago_kr(dt):
        if not dt:
            return ""
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
    def dt_kr(v, fmt: str = "%Y-%m-%d %H:%M"):
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