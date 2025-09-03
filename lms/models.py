from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()

# -----------------------------------
# 핵심 테이블
# -----------------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False)

    # 사용자 관리 화면용 필드
    role = db.Column(db.String(20), nullable=False, default='student')  # student | instructor | admin
    username = db.Column(db.String(50))
    phone = db.Column(db.String(30))
    is_active = db.Column(db.Boolean, nullable=False, default=True)

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

    # ▼ 추가
    file_url = db.Column(db.String(255))
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime)
    graded_at = db.Column(db.DateTime)

    assignment = db.relationship('Assignment', back_populates='submissions')
    user = db.relationship('User', back_populates='submissions')

    @property
    def is_late(self):
        if not self.submitted_at or not self.assignment or not self.assignment.due_at:
            return False
        return self.submitted_at > self.assignment.due_at

# -----------------------------
# 대시보드 유틸
# -----------------------------
def assignment_progress_for_user(user_id: int):
    total = db.session.scalar(
        db.select(func.count(Assignment.id))
        .join(Course, Course.id == Assignment.course_id)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.user_id == user_id)
    ) or 0

    submitted = db.session.scalar(
        db.select(func.count(func.distinct(Submission.assignment_id)))
        .where(Submission.user_id == user_id, Submission.submitted_at.isnot(None))
    ) or 0

    pct = int((submitted / total) * 100) if total else 0
    return pct, submitted, total


def average_score_for_user(user_id: int):
    avg = db.session.scalar(
        db.select(func.avg(Submission.score))
        .where(Submission.user_id == user_id, Submission.score.isnot(None))
    )
    return round(float(avg), 1) if avg is not None else None


def recent_activities_for_user(user_id: int, limit: int = 5):
    sub_rows = (
        db.session.query(Submission.submitted_at, Assignment.title)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(Submission.user_id == user_id, Submission.submitted_at.isnot(None))
        .all()
    )
    sub_acts = [(ts, f"과제 제출 · {title}") for ts, title in sub_rows]

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

# ========== Mentoring / Projects / Competitions ==========
class MentoringTeam(db.Model):
    __tablename__ = 'mentoring_teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 팀장
    is_solo = db.Column(db.Boolean, nullable=False, default=False)  # 개인 단독 참여 팀 플래그
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', foreign_keys=[owner_user_id])
    members = db.relationship('MentoringTeamMember', back_populates='team', cascade="all,delete")

class MentoringTeamMember(db.Model):
    __tablename__ = 'mentoring_team_members'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('mentoring_teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(40), default='member')  # member|leader|mentor
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship('MentoringTeam', back_populates='members')
    user = db.relationship('User')

class MentoringReport(db.Model):
    __tablename__ = 'mentoring_reports'
    id = db.Column(db.Integer, primary_key=True)
    author_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('mentoring_teams.id'))  # 팀 없으면 NULL(개인)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)              # 텍스트 보고서
    file_url = db.Column(db.String(255))      # 업로드 파일 경로(간단히 URL 문자열)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')
    team = db.relationship('MentoringTeam')

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    team_id = db.Column(db.Integer, db.ForeignKey('mentoring_teams.id'))  # 팀/개인 모두 가능
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))      # 개인 프로젝트면 소유자
    mentor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))     # 멘토 지정(선택)
    status = db.Column(db.String(30), default='ongoing')                  # ongoing|done|paused
    github_repo_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship('MentoringTeam')
    owner = db.relationship('User', foreign_keys=[owner_user_id])
    mentor = db.relationship('User', foreign_keys=[mentor_user_id])
    tasks = db.relationship('ProjectTask', back_populates='project', cascade="all,delete")

class ProjectTask(db.Model):
    __tablename__ = 'project_tasks'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    due_at = db.Column(db.DateTime)
    assignee_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='todo')  # todo|doing|done

    project = db.relationship('Project', back_populates='tasks')
    assignee = db.relationship('User')

class Competition(db.Model):
    __tablename__ = 'competitions'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    host = db.Column(db.String(120))
    url = db.Column(db.String(255))
    apply_deadline = db.Column(db.DateTime)
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)

class CompetitionEntry(db.Model):
    __tablename__ = 'competition_entries'
    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('mentoring_teams.id'))   # 팀 없으면 NULL
    applicant_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))   # 개인 신청자
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    status = db.Column(db.String(20), default='draft')  # draft|submitted|accepted|rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    competition = db.relationship('Competition')
    team = db.relationship('MentoringTeam')
    applicant = db.relationship('User')
    project = db.relationship('Project')

    # ----- 메시지 모델 -----
class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

    @property
    def is_read(self):
        return self.read_at is not None
    
    # ----- 캘린더 일정 -----
class CalendarEvent(db.Model):
    __tablename__ = 'calendar_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))    # NULL = 공개/공용
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    title = db.Column(db.String(200), nullable=False)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    kind = db.Column(db.String(20), default='event')              # event|mentoring|exam|meeting...
    description = db.Column(db.Text)
    source = db.Column(db.String(20), default='manual')           # manual|system
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')
    course = db.relationship('Course')

    # ----- 사용자 환경설정 -----
class UserSetting(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    language = db.Column(db.String(10), default='ko')
    theme = db.Column(db.String(10), default='light')  # light|dark
    timezone = db.Column(db.String(50), default='Asia/Seoul')
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)
    push_notifications = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime)

    user = db.relationship('User')