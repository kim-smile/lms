from src.models.user import db
from datetime import datetime

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    credits = db.Column(db.Integer, default=3)
    max_students = db.Column(db.Integer)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    semester = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instructor = db.relationship('User', back_populates='created_courses', foreign_keys=[instructor_id])
    sections = db.relationship('CourseSection', back_populates='course', cascade='all, delete-orphan')
    enrollments = db.relationship('CourseEnrollment', back_populates='course', cascade='all, delete-orphan')
    materials = db.relationship('CourseMaterial', back_populates='course', cascade='all, delete-orphan')
    syllabus = db.relationship('CourseSyllabus', back_populates='course', cascade='all, delete-orphan')
    contents = db.relationship('CourseContent', back_populates='course', cascade='all, delete-orphan')
    activities = db.relationship('LearningActivity', back_populates='course', cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', back_populates='course', cascade='all, delete-orphan')
    forums = db.relationship('DiscussionForum', back_populates='course', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Course {self.course_code}: {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_code': self.course_code,
            'title': self.title,
            'description': self.description,
            'credits': self.credits,
            'max_students': self.max_students,
            'instructor_id': self.instructor_id,
            'instructor_name': f"{self.instructor.first_name} {self.instructor.last_name}" if self.instructor else None,
            'semester': self.semester,
            'year': self.year,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CourseSection(db.Model):
    __tablename__ = 'course_sections'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    section_number = db.Column(db.String(10), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    max_students = db.Column(db.Integer)
    schedule_days = db.Column(db.String(20))  # 'MON,WED,FRI'
    schedule_time_start = db.Column(db.Time)
    schedule_time_end = db.Column(db.Time)
    classroom = db.Column(db.String(50))
    
    # Relationships
    course = db.relationship('Course', back_populates='sections')
    instructor = db.relationship('User', foreign_keys=[instructor_id])
    enrollments = db.relationship('CourseEnrollment', back_populates='section')
    
    __table_args__ = (db.UniqueConstraint('course_id', 'section_number'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'section_number': self.section_number,
            'instructor_id': self.instructor_id,
            'instructor_name': f"{self.instructor.first_name} {self.instructor.last_name}" if self.instructor else None,
            'max_students': self.max_students,
            'schedule_days': self.schedule_days,
            'schedule_time_start': self.schedule_time_start.isoformat() if self.schedule_time_start else None,
            'schedule_time_end': self.schedule_time_end.isoformat() if self.schedule_time_end else None,
            'classroom': self.classroom
        }

class CourseEnrollment(db.Model):
    __tablename__ = 'course_enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='enrolled')  # enrolled, dropped, completed
    final_grade = db.Column(db.String(5))
    
    # Relationships
    course = db.relationship('Course', back_populates='enrollments')
    section = db.relationship('CourseSection', back_populates='enrollments')
    student = db.relationship('User', back_populates='course_enrollments')
    
    __table_args__ = (db.UniqueConstraint('course_id', 'student_id'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'section_id': self.section_id,
            'student_id': self.student_id,
            'student_name': f"{self.student.first_name} {self.student.last_name}" if self.student else None,
            'enrollment_date': self.enrollment_date.isoformat() if self.enrollment_date else None,
            'status': self.status,
            'final_grade': self.final_grade
        }

class CourseMaterial(db.Model):
    __tablename__ = 'course_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100))
    publisher = db.Column(db.String(100))
    isbn = db.Column(db.String(20))
    material_type = db.Column(db.String(20), default='textbook')  # textbook, reference, online
    is_required = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', back_populates='materials')
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'author': self.author,
            'publisher': self.publisher,
            'isbn': self.isbn,
            'material_type': self.material_type,
            'is_required': self.is_required,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CourseSyllabus(db.Model):
    __tablename__ = 'course_syllabus'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    version = db.Column(db.Integer, default=1)
    
    # Relationships
    course = db.relationship('Course', back_populates='syllabus')
    uploader = db.relationship('User', foreign_keys=[uploaded_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'uploaded_by': self.uploaded_by,
            'uploader_name': f"{self.uploader.first_name} {self.uploader.last_name}" if self.uploader else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'version': self.version
        }

