from src.models.user import db
from datetime import datetime

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('course_contents.id'), nullable=False)
    progress_percentage = db.Column(db.Numeric(5, 2), default=0.00)
    completion_status = db.Column(db.String(20), default='not_started')  # not_started, in_progress, completed
    first_accessed_at = db.Column(db.DateTime)
    last_accessed_at = db.Column(db.DateTime)
    total_time_spent = db.Column(db.Integer, default=0)  # 총 학습 시간 (초)
    
    # Relationships
    user = db.relationship('User')
    course = db.relationship('Course')
    content = db.relationship('CourseContent', back_populates='user_progress')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'content_id'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'content_id': self.content_id,
            'progress_percentage': float(self.progress_percentage) if self.progress_percentage else 0.0,
            'completion_status': self.completion_status,
            'first_accessed_at': self.first_accessed_at.isoformat() if self.first_accessed_at else None,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'total_time_spent': self.total_time_spent
        }

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='present')  # present, absent, late, excused
    attendance_type = db.Column(db.String(20), default='manual')  # manual, code, time_based, activity_based
    attendance_code = db.Column(db.String(10))
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course')
    section = db.relationship('CourseSection')
    student = db.relationship('User', foreign_keys=[student_id])
    recorder = db.relationship('User', foreign_keys=[recorded_by])
    
    __table_args__ = (db.UniqueConstraint('course_id', 'student_id', 'attendance_date'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'section_id': self.section_id,
            'student_id': self.student_id,
            'student_name': f"{self.student.first_name} {self.student.last_name}" if self.student else None,
            'attendance_date': self.attendance_date.isoformat() if self.attendance_date else None,
            'status': self.status,
            'attendance_type': self.attendance_type,
            'attendance_code': self.attendance_code,
            'recorded_by': self.recorded_by,
            'recorder_name': f"{self.recorder.first_name} {self.recorder.last_name}" if self.recorder else None,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }

class LearningActivity(db.Model):
    __tablename__ = 'learning_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    activity_type = db.Column(db.String(50), nullable=False)  # assignment, quiz, discussion, project
    due_date = db.Column(db.DateTime)
    max_points = db.Column(db.Numeric(8, 2), default=0.00)
    is_published = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', back_populates='activities')
    creator = db.relationship('User', foreign_keys=[created_by])
    submissions = db.relationship('ActivitySubmission', back_populates='activity', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<LearningActivity {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'activity_type': self.activity_type,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'max_points': float(self.max_points) if self.max_points else 0.0,
            'is_published': self.is_published,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ActivitySubmission(db.Model):
    __tablename__ = 'activity_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('learning_activities.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submission_text = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='submitted')  # submitted, graded, returned
    score = db.Column(db.Numeric(8, 2))
    feedback = db.Column(db.Text)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    graded_at = db.Column(db.DateTime)
    
    # Relationships
    activity = db.relationship('LearningActivity', back_populates='submissions')
    student = db.relationship('User', foreign_keys=[student_id])
    grader = db.relationship('User', foreign_keys=[graded_by])
    
    __table_args__ = (db.UniqueConstraint('activity_id', 'student_id'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'activity_id': self.activity_id,
            'student_id': self.student_id,
            'student_name': f"{self.student.first_name} {self.student.last_name}" if self.student else None,
            'submission_text': self.submission_text,
            'file_path': self.file_path,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'status': self.status,
            'score': float(self.score) if self.score else None,
            'feedback': self.feedback,
            'graded_by': self.graded_by,
            'grader_name': f"{self.grader.first_name} {self.grader.last_name}" if self.grader else None,
            'graded_at': self.graded_at.isoformat() if self.graded_at else None
        }

