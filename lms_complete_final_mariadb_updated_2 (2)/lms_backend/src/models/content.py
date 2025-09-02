from src.models.user import db
from datetime import datetime

class ContentCategory(db.Model):
    __tablename__ = 'content_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('content_categories.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    parent = db.relationship('ContentCategory', remote_side=[id], backref='children')
    contents = db.relationship('CourseContent', back_populates='category')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CourseContent(db.Model):
    __tablename__ = 'course_contents'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    content_type = db.Column(db.String(50), nullable=False)  # video, pdf, ppt, scorm, xapi, link
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    duration = db.Column(db.Integer)  # 동영상 길이 (초)
    category_id = db.Column(db.Integer, db.ForeignKey('content_categories.id'))
    week_number = db.Column(db.Integer)
    lesson_order = db.Column(db.Integer)
    is_published = db.Column(db.Boolean, default=False)
    access_start_date = db.Column(db.DateTime)
    access_end_date = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = db.Column(db.Integer, default=1)
    
    # Relationships
    course = db.relationship('Course', back_populates='contents')
    category = db.relationship('ContentCategory', back_populates='contents')
    creator = db.relationship('User', foreign_keys=[created_by])
    versions = db.relationship('ContentVersion', back_populates='content', cascade='all, delete-orphan')
    access_logs = db.relationship('ContentAccessLog', back_populates='content', cascade='all, delete-orphan')
    user_progress = db.relationship('UserProgress', back_populates='content', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CourseContent {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'content_type': self.content_type,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'duration': self.duration,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'week_number': self.week_number,
            'lesson_order': self.lesson_order,
            'is_published': self.is_published,
            'access_start_date': self.access_start_date.isoformat() if self.access_start_date else None,
            'access_end_date': self.access_end_date.isoformat() if self.access_end_date else None,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version
        }

class ContentVersion(db.Model):
    __tablename__ = 'content_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('course_contents.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    change_description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    content = db.relationship('CourseContent', back_populates='versions')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    __table_args__ = (db.UniqueConstraint('content_id', 'version_number'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content_id': self.content_id,
            'version_number': self.version_number,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'change_description': self.change_description,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ContentAccessLog(db.Model):
    __tablename__ = 'content_access_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('course_contents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    access_time = db.Column(db.DateTime, default=datetime.utcnow)
    duration_seconds = db.Column(db.Integer)
    completion_percentage = db.Column(db.Numeric(5, 2), default=0.00)
    device_type = db.Column(db.String(20))  # desktop, mobile, tablet
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    
    # Relationships
    content = db.relationship('CourseContent', back_populates='access_logs')
    user = db.relationship('User')
    
    def to_dict(self):
        return {
            'id': self.id,
            'content_id': self.content_id,
            'user_id': self.user_id,
            'access_time': self.access_time.isoformat() if self.access_time else None,
            'duration_seconds': self.duration_seconds,
            'completion_percentage': float(self.completion_percentage) if self.completion_percentage else 0.0,
            'device_type': self.device_type,
            'ip_address': self.ip_address
        }

