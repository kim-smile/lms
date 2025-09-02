# app.py — Flask LMS (MariaDB) – Dashboard / Courses / Course Detail / Sidebar Pages

from flask import Flask, render_template, request, abort, url_for
from sqlalchemy import func
from models import (
    db, User, Course, Enrollment, Assignment, Submission,
    assignment_progress_for_user, average_score_for_user,
    recent_activities_for_user, upcoming_items_for_user
)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://wsuser:wsuser!@localhost:3306/lms_db?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 데모용: 로그인 세션 없이 user_id=1을 내 계정처럼 사용
DEMO_USER_ID = 1


# --------- 공용: 템플릿에서 사이드바 active 표시하기 위한 헬퍼 ---------
@app.context_processor
def inject_helpers():
    # 현재 경로가 '정확히' 일치할 때만 활성화
    def active_exact(endpoint_or_path='/'):
        p = request.path
        if endpoint_or_path.startswith('/'):
            return p == endpoint_or_path
        try:
            return p == url_for(endpoint_or_path)
        except Exception:
            return False

    # 현재 경로가 주어진 prefix로 시작하면 활성화
    def active_prefix(path_prefix):
        return request.path.startswith(path_prefix)

    return dict(active_exact=active_exact, active_prefix=active_prefix)

# ---------------------------------------
# 1) 대시보드
# ---------------------------------------
@app.route('/')
def dashboard():
    user = db.session.get(User, DEMO_USER_ID)
    if not user:
        return "초기 데이터가 없습니다. MariaDB에서 init_db.sql을 먼저 실행하세요.", 500

    # 수강 중인 강좌 수
    course_count = db.session.query(Enrollment).filter_by(user_id=DEMO_USER_ID).count()

    # 과제 진행률 / 평균 점수
    progress_pct, submitted_cnt, total_cnt = assignment_progress_for_user(DEMO_USER_ID)
    avg_score = average_score_for_user(DEMO_USER_ID)

    # 강좌별 진행 바 (과제 제출 비율)
    bars = []
    courses = (
        db.session.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == DEMO_USER_ID)
        .all()
    )
    for c in courses:
        total_c = db.session.query(Assignment).filter_by(course_id=c.id).count()
        submitted_c = (
            db.session.query(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .filter(
                Submission.user_id == DEMO_USER_ID,
                Assignment.course_id == c.id,
                Submission.submitted_at.isnot(None),
            )
            .count()
        )
        pct = int((submitted_c / total_c) * 100) if total_c else 0
        bars.append({'course': c, 'pct': pct})

    # 다가오는 마감 / 최근 활동
    upcoming = upcoming_items_for_user(DEMO_USER_ID, within_days=21)
    recent = recent_activities_for_user(DEMO_USER_ID, limit=5)

    return render_template(
        'dashboard.html',
        user=user,
        course_count=course_count,
        progress_pct=progress_pct,
        submitted_cnt=submitted_cnt,
        total_cnt=total_cnt,
        avg_score=avg_score,
        bars=bars,
        upcoming=upcoming,
        recent=recent,
    )


# ---------------------------------------
# 2) 강좌 목록
# ---------------------------------------
@app.route('/courses')
def courses():
    # 내가 수강 중인 강좌
    rows = (
        db.session.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == DEMO_USER_ID)
        .all()
    )

    # 카드에 쓸 진행률/집계
    cards = []
    for c in rows:
        total = db.session.query(Assignment).filter_by(course_id=c.id).count()
        submitted = (
            db.session.query(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .filter(
                Submission.user_id == DEMO_USER_ID,
                Assignment.course_id == c.id,
                Submission.submitted_at.isnot(None),
            ).count()
        )
        pct = int((submitted / total) * 100) if total else 0
        cards.append({
            'course': c,
            'total': total,
            'submitted': submitted,
            'progress': pct
        })

    return render_template('courses.html', courses=cards)


# ---------------------------------------
# 3) 강좌 상세 (탭: 강의 자료 / 과제 / 공지사항 / 토론)
#    * MariaDB 호환 정렬: func.isnull()로 NULLS LAST 대체
# ---------------------------------------
@app.route('/course/<int:course_id>')
def course_detail(course_id):
    tab = request.args.get('tab', 'materials')  # materials | assignments | notices | discussion

    course = db.session.get(Course, course_id)
    if not course:
        abort(404, description="강좌를 찾을 수 없습니다.")

    # 진행률(과제 기준)
    total = db.session.query(Assignment).filter_by(course_id=course.id).count()
    submitted = (
        db.session.query(Submission)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(
            Submission.user_id == DEMO_USER_ID,
            Assignment.course_id == course.id,
            Submission.submitted_at.isnot(None),
        ).count()
    )
    progress_pct = int((submitted / total) * 100) if total else 0

    # 과제 목록 (마감 오름차순, NULL은 뒤로) — MariaDB 대응
    assignments = (
        db.session.query(Assignment)
        .filter_by(course_id=course.id)
        .order_by(func.isnull(Assignment.due_at), Assignment.due_at.asc())
        .all()
    )

    # 과제 제출 맵 (assignment_id -> Submission)
    sub_map = {
        s.assignment_id: s
        for s in (
            db.session.query(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .filter(Submission.user_id == DEMO_USER_ID, Assignment.course_id == course.id)
            .all()
        )
    }

    # (샘플) 자료/공지/토론 — 필요 시 테이블로 분리 가능
    materials = [
        {"week": 1, "title": "1주차: HTML 기초", "duration": "45분", "status": "완료"},
        {"week": 2, "title": "2주차: CSS 스타일링", "duration": "50분", "status": "완료"},
        {"week": 3, "title": "3주차: JavaScript 기초", "duration": "60분", "status": "진행중"},
        {"week": None, "title": "실습 자료 - HTML 템플릿", "size": "2.5MB", "download": True},
    ]
    notices = [
        {"title": "중간고사 안내", "date": "2025-03-05", "pin": True},
        {"title": "실습 자료 업데이트", "date": "2025-02-28", "pin": False},
    ]
    discussion = [
        {"title": "1주차 과제 질문 스레드", "comments": 12, "updated": "2시간 전"},
        {"title": "프로젝트 팀 편성", "comments": 8, "updated": "1일 전"},
    ]

    return render_template(
        'course_detail.html',
        course=course,
        tab=tab,
        progress_pct=progress_pct,
        assignments=assignments,
        sub_map=sub_map,
        materials=materials,
        notices=notices,
        discussion=discussion,
    )


# ---------------------------------------
# 4) 사이드바의 나머지 페이지 (임시 페이지)
# ---------------------------------------
@app.route('/users')
def users_page():
    return render_template('placeholder.html', title='사용자 관리', desc='사용자/권한 관리 화면 (준비 중)')

@app.route('/analytics')
def analytics_page():
    return render_template('placeholder.html', title='분석 및 리포트', desc='학습/성과 분석 리포트 (준비 중)')

@app.route('/messages')
def messages_page():
    return render_template('placeholder.html', title='메시지', desc='강의/과제 관련 메시지함 (준비 중)')

@app.route('/schedule')
def schedule_page():
    return render_template('placeholder.html', title='일정', desc='강의/마감/캘린더 (준비 중)')

@app.route('/assignments_page')   # /assignments는 모델명과 혼동 방지용으로 별도 경로
def assignments_page():
    return render_template('placeholder.html', title='과제', desc='과제 목록/제출 관리 (준비 중)')

@app.route('/grades')
def grades_page():
    return render_template('placeholder.html', title='성적', desc='성적/평가 현황 (준비 중)')

@app.route('/profile')
def profile_page():
    return render_template('placeholder.html', title='프로필', desc='내 프로필/설정 (준비 중)')

@app.route('/settings')
def settings_page():
    return render_template('placeholder.html', title='설정', desc='환경설정 (준비 중)')


# ---------------------------------------
# 앱 실행
# ---------------------------------------
if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True, port=5004)