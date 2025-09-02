from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()

# -----------------------------------
# 핵심 테이블(대시보드에 필요한 최소만)
# -----------------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship('Enrollment', back_populates='user')
    submissions = db.relationship('Submission', back_populates='user')


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship('Enrollment', back_populates='course')
    assignments = db.relationship('Assignment', back_populates='course')


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    due_at = db.Column(db.DateTime, nullable=True)
    total_score = db.Column(db.Integer, default=100)

    course = db.relationship('Course', back_populates='assignments')
    submissions = db.relationship('Submission', back_populates='assignment')


class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer, nullable=True)

    assignment = db.relationship('Assignment', back_populates='submissions')
    user = db.relationship('User', back_populates='submissions')


# -----------------------------
# 대시보드 유틸 (progress, 평균점수 등)
# -----------------------------
def assignment_progress_for_user(user_id: int):
    """
    진행률 = (제출한 과제 수 / 전체 과제 수) * 100
    """
    # 내가 수강 중인 강좌의 전체 과제 수
    total = db.session.scalar(
        db.select(func.count(Assignment.id))
        .join(Course, Course.id == Assignment.course_id)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.user_id == user_id)
    ) or 0

    # 내가 제출한 과제(과제별 1회만 카운트)
    submitted = db.session.scalar(
        db.select(func.count(func.distinct(Submission.assignment_id)))
        .where(Submission.user_id == user_id, Submission.submitted_at.isnot(None))
    ) or 0

    pct = int((submitted / total) * 100) if total else 0
    return pct, submitted, total


def average_score_for_user(user_id: int):
    """
    제출/채점된 과제의 평균 점수
    """
    avg = db.session.scalar(
        db.select(func.avg(Submission.score))
        .where(Submission.user_id == user_id, Submission.score.isnot(None))
    )
    return round(float(avg), 1) if avg is not None else None


def recent_activities_for_user(user_id: int, limit: int = 5):
    """
    최근 활동 간단 버전:
    - 제출: '과제 제출 · {과제제목}'
    - 수강신청(대시보드 채우기용): '강의 시작 · {강좌명}'
    """
    # 제출 활동
    sub_rows = (
        db.session.query(Submission.submitted_at, Assignment.title)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(Submission.user_id == user_id, Submission.submitted_at.isnot(None))
        .all()
    )
    sub_acts = [(ts, f"과제 제출 · {title}") for ts, title in sub_rows]

    # 수강신청을 활동처럼 표시
    enr_rows = (
        db.session.query(Enrollment.created_at, Course.title)
        .join(Course, Course.id == Enrollment.course_id)
        .filter(Enrollment.user_id == user_id)
        .all()
    )
    enr_acts = [(ts, f"강의 시작 · {title}") for ts, title in enr_rows]

    merged = sub_acts + enr_acts
    merged.sort(key=lambda x: (x[0] or datetime.min), reverse=True)
    return merged[:limit]


def upcoming_items_for_user(user_id: int, within_days: int = 14):
    """
    다가오는 마감(과제) 목록: (과제제목, 강좌명, 마감일)
    """
    now = datetime.utcnow()
    until = now + timedelta(days=within_days)
    rows = (
        db.session.query(Assignment.title, Course.title, Assignment.due_at)
        .join(Course, Course.id == Assignment.course_id)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.user_id == user_id,
            Assignment.due_at.isnot(None),
            Assignment.due_at >= now,
            Assignment.due_at <= until,
        )
        .order_by(Assignment.due_at.asc())
        .all()
    )
    return rows