# config.py — 환경설정
import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://wsuser:wsuser!@127.0.0.1:3306/lms_db?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

    # 업로드
    BASE_DIR = os.path.dirname(__file__)
    UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_EXTS = {
        "pdf","zip","doc","docx","ppt","pptx","xlsx","csv","ipynb","py","txt","md","rar",
    }

    # 데모 사용자(로그인 없을 때 g.user 바인딩 대비)
    DEMO_USER_ID = int(os.environ.get("DEMO_USER_ID", 1))

    # 날짜 포맷
    DATE_ONLY = "%Y-%m-%d"
    DATE_HM = "%Y-%m-%d %H:%M"
    DATE_T = "%Y-%m-%dT%H:%M"