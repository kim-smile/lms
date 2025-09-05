# config.py — 환경설정
import os

class Config:
    # DB
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://wsuser:wsuser!@127.0.0.1:3306/lms_db?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

    # 경로
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "static", "uploads"))

    # 업로드 허용 확장자
    ALLOWED_EXTS = {
        "pdf","zip","doc","docx","ppt","pptx","xlsx","csv","ipynb","py","txt","md","rar",
        "jpg","jpeg","png","gif"  # 필요 시 이미지 확장자도 허용
    }

    # 데모 사용자(로그인 없을 때 g.user 바인딩 대비)
    DEMO_USER_ID = int(os.environ.get("DEMO_USER_ID", 1))

    # 날짜 포맷
    DATE_ONLY = "%Y-%m-%d"
    DATE_HM = "%Y-%m-%d %H:%M"
    DATE_T = "%Y-%m-%dT%H:%M"