from src.models.user import db
from datetime import datetime

class LearningAnalytics(db.Model):
    __tablename__ = 'learning_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Numeric(10, 2))
    metric_date = db.Column(db.Date, default=datetime.utcnow().date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User')
    course = db.relationship('Course')
    
    def __repr__(self):
        return f'<LearningAnalytics {self.metric_name}: {self.metric_value}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'metric_name': self.metric_name,
            'metric_value': float(self.metric_value) if self.metric_value else None,
            'metric_date': self.metric_date.isoformat() if self.metric_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.JSON)  # PostgreSQL JSON field
    
    # Relationships
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<SystemLog {self.action} by {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name}" if self.user else None,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'details': self.details
        }

class RiskAlert(db.Model):
    __tablename__ = 'risk_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # low_progress, low_attendance, low_grades
    severity = db.Column(db.String(20), default='medium')  # low, medium, high
    description = db.Column(db.Text)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course')
    resolver = db.relationship('User', foreign_keys=[resolved_by])
    
    def __repr__(self):
        return f'<RiskAlert {self.alert_type} for {self.student_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': f"{self.student.first_name} {self.student.last_name}" if self.student else None,
            'course_id': self.course_id,
            'course_title': self.course.title if self.course else None,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'description': self.description,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'resolver_name': f"{self.resolver.first_name} {self.resolver.last_name}" if self.resolver else None
        }

class CourseStatistics(db.Model):
    __tablename__ = 'course_statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    stat_date = db.Column(db.Date, default=datetime.utcnow().date)
    total_students = db.Column(db.Integer, default=0)
    active_students = db.Column(db.Integer, default=0)
    avg_progress = db.Column(db.Numeric(5, 2), default=0.00)
    avg_attendance = db.Column(db.Numeric(5, 2), default=0.00)
    avg_grade = db.Column(db.Numeric(5, 2), default=0.00)
    content_views = db.Column(db.Integer, default=0)
    forum_posts = db.Column(db.Integer, default=0)
    assignment_submissions = db.Column(db.Integer, default=0)
    quiz_attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course')
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'course_title': self.course.title if self.course else None,
            'stat_date': self.stat_date.isoformat() if self.stat_date else None,
            'total_students': self.total_students,
            'active_students': self.active_students,
            'avg_progress': float(self.avg_progress) if self.avg_progress else 0.0,
            'avg_attendance': float(self.avg_attendance) if self.avg_attendance else 0.0,
            'avg_grade': float(self.avg_grade) if self.avg_grade else 0.0,
            'content_views': self.content_views,
            'forum_posts': self.forum_posts,
            'assignment_submissions': self.assignment_submissions,
            'quiz_attempts': self.quiz_attempts,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UserStatistics(db.Model):
    __tablename__ = 'user_statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stat_date = db.Column(db.Date, default=datetime.utcnow().date)
    total_login_time = db.Column(db.Integer, default=0)  # 총 로그인 시간 (분)
    content_views = db.Column(db.Integer, default=0)
    forum_posts = db.Column(db.Integer, default=0)
    assignments_submitted = db.Column(db.Integer, default=0)
    quizzes_taken = db.Column(db.Integer, default=0)
    avg_quiz_score = db.Column(db.Numeric(5, 2), default=0.00)
    courses_enrolled = db.Column(db.Integer, default=0)
    courses_completed = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name}" if self.user else None,
            'stat_date': self.stat_date.isoformat() if self.stat_date else None,
            'total_login_time': self.total_login_time,
            'content_views': self.content_views,
            'forum_posts': self.forum_posts,
            'assignments_submitted': self.assignments_submitted,
            'quizzes_taken': self.quizzes_taken,
            'avg_quiz_score': float(self.avg_quiz_score) if self.avg_quiz_score else 0.0,
            'courses_enrolled': self.courses_enrolled,
            'courses_completed': self.courses_completed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

