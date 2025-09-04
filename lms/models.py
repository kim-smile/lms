# models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func  # (일부 쿼리에서 사용될 수 있어 유지)
from extensions import db


# =============================================================================
# Core Tables
# =============================================================================
class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.Index("ix_users_role", "role"),
        db.Index("ix_users_is_active", "is_active"),
        db.UniqueConstraint("email", name="uq_users_email"),
        db.UniqueConstraint("username", name="uq_users_username"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(100), nullable=False)
    email: str = db.Column(db.String(190), nullable=False)

    # 사용자 관리/권한
    role: str = db.Column(db.String(20), nullable=False, default="student")  # student|instructor|admin
    username: Optional[str] = db.Column(db.String(50))
    phone: Optional[str] = db.Column(db.String(30))
    is_active: bool = db.Column(db.Boolean, nullable=False, default=True)

    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # 로그인 컬럼
    password_hash: Optional[str] = db.Column(db.String(255))     # 권장: 해시 보관
    password: Optional[str] = db.Column(db.String(128))          # 레거시/데모용: 평문(운영 비권장)

    # 관계
    enrollments = db.relationship("Enrollment", back_populates="user", cascade="all,delete-orphan")
    submissions = db.relationship("Submission", back_populates="user", cascade="all,delete")

    # helpers
    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        # 해시 우선, 없으면 레거시 평문 비교
        if self.password_hash:
            return check_password_hash(self.password_hash, raw)
        if self.password:
            return self.password == raw
        return False

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name!r} email={self.email!r}>"


class Course(db.Model):
    __tablename__ = "courses"
    __table_args__ = (
        db.Index("ix_courses_start_date", "start_date"),
        db.Index("ix_courses_end_date", "end_date"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    title: str = db.Column(db.String(200), nullable=False)
    start_date: Optional[datetime] = db.Column(db.Date)
    end_date: Optional[datetime] = db.Column(db.Date)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    enrollments = db.relationship("Enrollment", back_populates="course", cascade="all,delete-orphan")
    assignments = db.relationship("Assignment", back_populates="course", cascade="all,delete-orphan")

    def __repr__(self) -> str:
        return f"<Course id={self.id} title={self.title!r}>"


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    __table_args__ = (
        db.Index("ix_enrollments_user", "user_id"),
        db.Index("ix_enrollments_course", "course_id"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id: int = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="enrollments")
    course = db.relationship("Course", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<Enrollment id={self.id} user_id={self.user_id} course_id={self.course_id}>"


class Assignment(db.Model):
    __tablename__ = "assignments"
    __table_args__ = (
        db.Index("ix_assignments_course", "course_id"),
        db.Index("ix_assignments_due", "due_at"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    course_id: int = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title: str = db.Column(db.String(200), nullable=False)
    due_at: Optional[datetime] = db.Column(db.DateTime)
    total_score: int = db.Column(db.Integer, nullable=False, default=100)

    course = db.relationship("Course", back_populates="assignments")
    submissions = db.relationship("Submission", back_populates="assignment", cascade="all,delete-orphan")

    def __repr__(self) -> str:
        return f"<Assignment id={self.id} course_id={self.course_id} title={self.title!r}>"


class Submission(db.Model):
    __tablename__ = "submissions"
    __table_args__ = (
        db.Index("ix_submissions_user", "user_id"),
        db.Index("ix_submissions_assignment", "assignment_id"),
        db.Index("ix_submissions_submitted_at", "submitted_at"),
        db.UniqueConstraint("user_id", "assignment_id", name="uq_sub_user_assignment"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    assignment_id: int = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    submitted_at: Optional[datetime] = db.Column(db.DateTime)  # 제출 시점에 설정
    score: Optional[int] = db.Column(db.Integer)

    # 첨부/메타
    file_url: Optional[str] = db.Column(db.String(255))
    comment: Optional[str] = db.Column(db.Text)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = db.Column(db.DateTime, onupdate=datetime.utcnow)
    graded_at: Optional[datetime] = db.Column(db.DateTime)

    assignment = db.relationship("Assignment", back_populates="submissions")
    user = db.relationship("User", back_populates="submissions")

    @property
    def is_late(self) -> bool:
        if not self.submitted_at or not self.assignment or not self.assignment.due_at:
            return False
        return self.submitted_at > self.assignment.due_at

    def __repr__(self) -> str:
        return f"<Submission id={self.id} assignment_id={self.assignment_id} user_id={self.user_id}>"


# =============================================================================
# Mentoring / Projects / Competitions
# =============================================================================
class MentoringTeam(db.Model):
    __tablename__ = "mentoring_teams"
    __table_args__ = (db.Index("ix_mentoring_teams_owner", "owner_user_id"),)

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(120), nullable=False)
    owner_user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # 팀장
    is_solo: bool = db.Column(db.Boolean, nullable=False, default=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    owner = db.relationship("User", foreign_keys=[owner_user_id])
    members = db.relationship("MentoringTeamMember", back_populates="team", cascade="all,delete-orphan")

    def __repr__(self) -> str:
        return f"<MentoringTeam id={self.id} name={self.name!r}>"


class MentoringTeamMember(db.Model):
    __tablename__ = "mentoring_team_members"
    __table_args__ = (
        db.Index("ix_mtm_team", "team_id"),
        db.Index("ix_mtm_user", "user_id"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    team_id: int = db.Column(db.Integer, db.ForeignKey("mentoring_teams.id"), nullable=False)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role: str = db.Column(db.String(40), default="member")  # member|leader|mentor
    joined_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    team = db.relationship("MentoringTeam", back_populates="members")
    user = db.relationship("User")

    def __repr__(self) -> str:
        return f"<MentoringTeamMember id={self.id} team_id={self.team_id} user_id={self.user_id} role={self.role}>"


class MentoringReport(db.Model):
    __tablename__ = "mentoring_reports"
    __table_args__ = (
        db.Index("ix_mreports_author", "author_user_id"),
        db.Index("ix_mreports_team", "team_id"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    author_user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    team_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("mentoring_teams.id"))
    title: str = db.Column(db.String(200), nullable=False)
    content: Optional[str] = db.Column(db.Text)
    file_url: Optional[str] = db.Column(db.String(255))
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    author = db.relationship("User")
    team = db.relationship("MentoringTeam")

    def __repr__(self) -> str:
        return f"<MentoringReport id={self.id} title={self.title!r}>"


class Project(db.Model):
    __tablename__ = "projects"
    __table_args__ = (
        db.Index("ix_projects_team", "team_id"),
        db.Index("ix_projects_owner", "owner_user_id"),
        db.Index("ix_projects_status", "status"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    title: str = db.Column(db.String(200), nullable=False)
    description: Optional[str] = db.Column(db.Text)
    team_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("mentoring_teams.id"))
    owner_user_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("users.id"))
    mentor_user_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("users.id"))
    status: str = db.Column(db.String(30), default="ongoing")  # ongoing|done|paused
    github_repo_url: Optional[str] = db.Column(db.String(255))
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    team = db.relationship("MentoringTeam")
    owner = db.relationship("User", foreign_keys=[owner_user_id])
    mentor = db.relationship("User", foreign_keys=[mentor_user_id])
    tasks = db.relationship("ProjectTask", back_populates="project", cascade="all,delete-orphan")

    def __repr__(self) -> str:
        return f"<Project id={self.id} title={self.title!r} status={self.status}>"


class ProjectTask(db.Model):
    __tablename__ = "project_tasks"
    __table_args__ = (
        db.Index("ix_ptasks_project", "project_id"),
        db.Index("ix_ptasks_assignee", "assignee_user_id"),
        db.Index("ix_ptasks_due", "due_at"),
        db.Index("ix_ptasks_status", "status"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    project_id: int = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title: str = db.Column(db.String(200), nullable=False)
    due_at: Optional[datetime] = db.Column(db.DateTime)
    assignee_user_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("users.id"))
    status: str = db.Column(db.String(20), default="todo")  # todo|doing|done

    project = db.relationship("Project", back_populates="tasks")
    assignee = db.relationship("User")

    def __repr__(self) -> str:
        return f"<ProjectTask id={self.id} project_id={self.project_id} title={self.title!r}>"


class Competition(db.Model):
    __tablename__ = "competitions"
    __table_args__ = (
        db.Index("ix_competitions_deadline", "apply_deadline"),
        db.Index("ix_competitions_start", "start_at"),
        db.Index("ix_competitions_end", "end_at"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    title: str = db.Column(db.String(200), nullable=False)
    host: Optional[str] = db.Column(db.String(120))
    url: Optional[str] = db.Column(db.String(255))
    apply_deadline: Optional[datetime] = db.Column(db.DateTime)
    start_at: Optional[datetime] = db.Column(db.DateTime)
    end_at: Optional[datetime] = db.Column(db.DateTime)

    def __repr__(self) -> str:
        return f"<Competition id={self.id} title={self.title!r}>"


class CompetitionEntry(db.Model):
    __tablename__ = "competition_entries"
    __table_args__ = (
        db.Index("ix_centries_competition", "competition_id"),
        db.Index("ix_centries_team", "team_id"),
        db.Index("ix_centries_applicant", "applicant_user_id"),
        db.Index("ix_centries_project", "project_id"),
        db.Index("ix_centries_status", "status"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    competition_id: int = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    team_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("mentoring_teams.id"))
    applicant_user_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("users.id"))
    project_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("projects.id"))
    status: str = db.Column(db.String(20), default="draft")  # draft|submitted|accepted|rejected
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    competition = db.relationship("Competition")
    team = db.relationship("MentoringTeam")
    applicant = db.relationship("User")
    project = db.relationship("Project")

    def __repr__(self) -> str:
        return f"<CompetitionEntry id={self.id} competition_id={self.competition_id} status={self.status}>"


# =============================================================================
# Messaging / Calendar / Settings
# =============================================================================
class Message(db.Model):
    __tablename__ = "messages"
    __table_args__ = (
        db.Index("ix_messages_sender", "sender_id"),
        db.Index("ix_messages_receiver", "receiver_id"),
        db.Index("ix_messages_read_at", "read_at"),
        db.Index("ix_messages_created_at", "created_at"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    sender_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title: str = db.Column(db.String(200), nullable=False)
    body: Optional[str] = db.Column(db.Text)
    read_at: Optional[datetime] = db.Column(db.DateTime)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def __repr__(self) -> str:
        return f"<Message id={self.id} sender={self.sender_id} receiver={self.receiver_id}>"


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"
    __table_args__ = (
        db.Index("ix_cevents_user", "user_id"),
        db.Index("ix_cevents_course", "course_id"),
        db.Index("ix_cevents_start", "start_at"),
        db.Index("ix_cevents_kind", "kind"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("users.id"))  # NULL = 공용
    course_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("courses.id"))
    title: str = db.Column(db.String(200), nullable=False)
    start_at: datetime = db.Column(db.DateTime, nullable=False)
    end_at: Optional[datetime] = db.Column(db.DateTime)
    location: Optional[str] = db.Column(db.String(200))
    kind: str = db.Column(db.String(20), default="event")  # event|mentoring|exam|meeting...
    description: Optional[str] = db.Column(db.Text)
    source: str = db.Column(db.String(20), default="manual")  # manual|system
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")
    course = db.relationship("Course")

    def __repr__(self) -> str:
        return f"<CalendarEvent id={self.id} title={self.title!r} start_at={self.start_at}>"


class UserSetting(db.Model):
    __tablename__ = "user_settings"
    __table_args__ = (db.Index("ix_usersettings_user", "user_id"),)

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    language: str = db.Column(db.String(10), default="ko")
    theme: str = db.Column(db.String(10), default="light")  # light|dark
    timezone: str = db.Column(db.String(50), default="Asia/Seoul")
    email_notifications: bool = db.Column(db.Boolean, default=True, nullable=False)
    push_notifications: bool = db.Column(db.Boolean, default=False, nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = db.Column(db.DateTime, onupdate=datetime.utcnow)

    user = db.relationship("User")

    def __repr__(self) -> str:
        return f"<UserSetting id={self.id} user_id={self.user_id} theme={self.theme}>"