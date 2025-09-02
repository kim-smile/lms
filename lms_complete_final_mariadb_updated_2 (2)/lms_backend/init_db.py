
#!/usr/bin/env python3
"""
Database initialization script for LMS
Creates tables and inserts sample data
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.main import create_app
from src.models import db, User, Course, CourseEnrollment
from src.models.role import Role
from src.models.user_role import UserRole
from werkzeug.security import generate_password_hash
from datetime import datetime

def init_database():
    """Initialize database with sample data"""
    app = create_app()
    
    with app.app_context():
        # Drop all tables and recreate
        db.drop_all()
        db.create_all()
        
        # Create roles
        roles_data = [
            {'name': 'admin', 'description': 'System Administrator'},
            {'name': 'instructor', 'description': 'Course Instructor'},
            {'name': 'teaching_assistant', 'description': 'Teaching Assistant'},
            {'name': 'student', 'description': 'Student'}
        ]
        
        roles = {}
        for role_data in roles_data:
            role = Role(name=role_data['name'], description=role_data['description'])
            db.session.add(role)
            roles[role_data['name']] = role
        
        db.session.flush()  # Get role IDs
        
        # Create users
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@university.edu',
                'password': 'admin123',
                'first_name': '관리자',
                'last_name': '시스템',
                'roles': ['admin']
            },
            {
                'username': 'instructor',
                'email': 'instructor@university.edu',
                'password': 'instructor123',
                'first_name': '철수',
                'last_name': '김',
                'roles': ['instructor']
            },
            {
                'username': 'student',
                'email': 'student@university.edu',
                'password': 'student123',
                'first_name': '영희',
                'last_name': '이',
                'roles': ['student']
            }
        ]
        
        users = {}
        for user_data in users_data:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=generate_password_hash(user_data['password']),
                first_name=user_data['first_name'],
                last_name=user_data['last_name']
            )
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Assign roles
            for role_name in user_data['roles']:
                user_role = UserRole(user_id=user.id, role_id=roles[role_name].id)
                db.session.add(user_role)
            
            users[user_data['username']] = user
        
        # Create sample courses
        courses_data = [
            {
                'title': '웹 프로그래밍',
                'course_code': 'CS301',
                'description': 'HTML, CSS, JavaScript를 활용한 웹 개발 기초',
                'instructor': users['instructor'],
                'semester': '2024-1',
                'year': 2024,
                'credits': 3,
                'max_students': 50
            },
            {
                'title': '데이터베이스 시스템',
                'course_code': 'CS302',
                'description': '관계형 데이터베이스 설계 및 SQL 활용',
                'instructor': users['instructor'],
                'semester': '2024-1',
                'year': 2024,
                'credits': 3,
                'max_students': 40
            }
        ]
        
        for course_data in courses_data:
            course = Course(
                title=course_data['title'],
                course_code=course_data['course_code'],
                description=course_data['description'],
                instructor_id=course_data['instructor'].id,
                semester=course_data['semester'],
                year=course_data['year'],
                credits=course_data['credits'],
                max_students=course_data['max_students']
            )
            db.session.add(course)
            db.session.flush()
            
            # Enroll student in courses
            enrollment = CourseEnrollment(
                course_id=course.id,
                student_id=users['student'].id,
                status='enrolled'
            )
            db.session.add(enrollment)
        
        # Commit all changes
        db.session.commit()
        
        print("Database initialized successfully!")
        print("\nTest accounts created:")
        print("Admin: admin / admin123")
        print("Instructor: instructor / instructor123")
        print("Student: student / student123")

if __name__ == '__main__':
    init_database()



