from flask import Blueprint, render_template_string
from helpers.auth import login_required  # 이미 사용 중인 인증 데코레이터

# 블루프린트 정의
bp = Blueprint("settings", __name__, url_prefix="/settings")

@bp.get("/", endpoint="home")
@login_required
def home():
    # TODO: settings.html 템플릿 만들어서 render_template로 교체하세요.
    return render_template_string("<h1>설정 페이지 (TODO)</h1>")