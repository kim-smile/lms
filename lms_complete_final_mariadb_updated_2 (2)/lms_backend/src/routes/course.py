from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from src.models import db, User
from src.models import Course, CourseSection, CourseEnrollment, CourseMaterial, CourseSyllabus
from src.models import SystemLog

course_bp = Blueprint('course', __name__)

# Course management endpoints
@course_bp.route('/courses', methods=['GET'])
@jwt_required()
def get_courses():
    """강좌 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        semester = request.args.get('semester', '')
        year = request.args.get('year', type=int)
        
        query = Course.query
        
        # 역할에 따른 필터링
        if 'instructor' in user.get_roles():
            # 교수는 자신이 담당하는 강좌만 조회
            query = query.filter(Course.instructor_id == user_id)
        elif 'student' in user.get_roles():
            # 학생은 수강 중인 강좌만 조회
            query = query.join(CourseEnrollment).filter(
                CourseEnrollment.student_id == user_id,
                CourseEnrollment.status == 'enrolled'
            )
        
        # 검색 필터
        if search:
            query = query.filter(
                (Course.title.contains(search)) |
                (Course.course_code.contains(search)) |
                (Course.description.contains(search))
            )
        
        # 학기 필터
        if semester:
            query = query.filter(Course.semester == semester)
        
        # 연도 필터
        if year:
            query = query.filter(Course.year == year)
        
        # 활성 강좌만 조회
        query = query.filter(Course.is_active == True)
        
        courses = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'courses': [course.to_dict() for course in courses.items],
            'total': courses.total,
            'pages': courses.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@course_bp.route('/courses', methods=['POST'])
@jwt_required()
def create_course():
    """강좌 생성 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        # 권한 확인
        if not ('instructor' in user.get_roles() or 'admin' in user.get_roles()):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.json
        
        # 필수 필드 검증
        required_fields = ['course_code', 'title', 'semester', 'year']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # 중복 강좌 코드 확인
        if Course.query.filter_by(course_code=data['course_code']).first():
            return jsonify({'error': 'Course code already exists'}), 400
        
        # 새 강좌 생성
        course = Course(
            course_code=data['course_code'],
            title=data['title'],
            description=data.get('description'),
            credits=data.get('credits', 3),
            max_students=data.get('max_students'),
            instructor_id=user_id,
            semester=data['semester'],
            year=data['year'],
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None
        )
        
        db.session.add(course)
        db.session.commit()
        
        # 시스템 로그 기록
        log = SystemLog(
            user_id=user_id,
            action='course_create',
            resource_type='course',
            resource_id=course.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify(course.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/courses/<int:course_id>', methods=['GET'])
@jwt_required()
def get_course(course_id):
    """특정 강좌 조회"""
    try:
        user_id = get_jwt_identity()
        course = Course.query.get_or_404(course_id)
        
        # 접근 권한 확인
        user = User.query.get_or_404(user_id)
        if not ('admin' in user.get_roles() or 
                course.instructor_id == user_id or
                CourseEnrollment.query.filter_by(
                    course_id=course_id, student_id=user_id, status='enrolled'
                ).first()):
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify(course.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@course_bp.route('/courses/<int:course_id>', methods=['PUT'])
@jwt_required()
def update_course(course_id):
    """강좌 정보 수정"""
    try:
        user_id = get_jwt_identity()
        course = Course.query.get_or_404(course_id)
        user = User.query.get_or_404(user_id)
        
        # 권한 확인 (강좌 담당 교수 또는 관리자)
        if not ('admin' in user.get_roles() or course.instructor_id == user_id):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.json
        
        # 업데이트 가능한 필드들
        updatable_fields = [
            'title', 'description', 'credits', 'max_students',
            'semester', 'year', 'start_date', 'end_date', 'is_active'
        ]
        
        for field in updatable_fields:
            if field in data:
                if field in ['start_date', 'end_date'] and data[field]:
                    setattr(course, field, datetime.fromisoformat(data[field]))
                else:
                    setattr(course, field, data[field])
        
        course.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 시스템 로그 기록
        log = SystemLog(
            user_id=user_id,
            action='course_update',
            resource_type='course',
            resource_id=course.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify(course.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/courses/<int:course_id>', methods=['DELETE'])
@jwt_required()
def delete_course(course_id):
    """강좌 삭제"""
    try:
        user_id = get_jwt_identity()
        course = Course.query.get_or_404(course_id)
        user = User.query.get_or_404(user_id)
        
        # 권한 확인 (강좌 담당 교수 또는 관리자)
        if not ('admin' in user.get_roles() or course.instructor_id == user_id):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        db.session.delete(course)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Course enrollment endpoints
@course_bp.route('/courses/<int:course_id>/enroll', methods=['POST'])
@jwt_required()
def enroll_course(course_id):
    """강좌 수강 신청"""
    try:
        user_id = get_jwt_identity()
        course = Course.query.get_or_404(course_id)
        
        # 이미 수강 중인지 확인
        existing_enrollment = CourseEnrollment.query.filter_by(
            course_id=course_id, student_id=user_id
        ).first()
        
        if existing_enrollment:
            if existing_enrollment.status == 'enrolled':
                return jsonify({'error': 'Already enrolled in this course'}), 400
            else:
                # 재수강 신청
                existing_enrollment.status = 'enrolled'
                existing_enrollment.enrollment_date = datetime.utcnow()
        else:
            # 새 수강 신청
            enrollment = CourseEnrollment(
                course_id=course_id,
                student_id=user_id,
                status='enrolled'
            )
            db.session.add(enrollment)
        
        db.session.commit()
        
        # 시스템 로그 기록
        log = SystemLog(
            user_id=user_id,
            action='course_enroll',
            resource_type='course',
            resource_id=course_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'message': 'Successfully enrolled in course'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/courses/<int:course_id>/drop', methods=['POST'])
@jwt_required()
def drop_course(course_id):
    """강좌 수강 취소"""
    try:
        user_id = get_jwt_identity()
        
        enrollment = CourseEnrollment.query.filter_by(
            course_id=course_id, student_id=user_id, status='enrolled'
        ).first_or_404()
        
        enrollment.status = 'dropped'
        db.session.commit()
        
        # 시스템 로그 기록
        log = SystemLog(
            user_id=user_id,
            action='course_drop',
            resource_type='course',
            resource_id=course_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'message': 'Successfully dropped from course'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/courses/<int:course_id>/students', methods=['GET'])
@jwt_required()
def get_course_students(course_id):
    """강좌 수강생 목록 조회"""
    try:
        user_id = get_jwt_identity()
        course = Course.query.get_or_404(course_id)
        user = User.query.get_or_404(user_id)
        
        # 권한 확인 (강좌 담당 교수 또는 관리자)
        if not ('admin' in user.get_roles() or course.instructor_id == user_id):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        enrollments = CourseEnrollment.query.filter_by(
            course_id=course_id, status='enrolled'
        ).all()
        
        students = []
        for enrollment in enrollments:
            student_data = enrollment.student.to_dict()
            student_data['enrollment_date'] = enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None
            student_data['final_grade'] = enrollment.final_grade
            students.append(student_data)
        
        return jsonify({
            'course_id': course_id,
            'course_title': course.title,
            'students': students,
            'total_students': len(students)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Course materials endpoints
@course_bp.route('/courses/<int:course_id>/materials', methods=['GET'])
@jwt_required()
def get_course_materials(course_id):
    """강좌 교재 목록 조회"""
    try:
        user_id = get_jwt_identity()
        course = Course.query.get_or_404(course_id)
        
        # 접근 권한 확인
        user = User.query.get_or_404(user_id)
        if not ('admin' in user.get_roles() or 
                course.instructor_id == user_id or
                CourseEnrollment.query.filter_by(
                    course_id=course_id, student_id=user_id, status='enrolled'
                ).first()):
            return jsonify({'error': 'Access denied'}), 403
        
        materials = CourseMaterial.query.filter_by(course_id=course_id).all()
        
        return jsonify([material.to_dict() for material in materials]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@course_bp.route('/courses/<int:course_id>/materials', methods=['POST'])
@jwt_required()
def add_course_material(course_id):
    """강좌 교재 추가"""
    try:
        user_id = get_jwt_identity()
        course = Course.query.get_or_404(course_id)
        user = User.query.get_or_404(user_id)
        
        # 권한 확인 (강좌 담당 교수 또는 관리자)
        if not ('admin' in user.get_roles() or course.instructor_id == user_id):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.json
        
        # 필수 필드 검증
        if not data.get('title'):
            return jsonify({'error': 'title is required'}), 400
        
        material = CourseMaterial(
            course_id=course_id,
            title=data['title'],
            author=data.get('author'),
            publisher=data.get('publisher'),
            isbn=data.get('isbn'),
            material_type=data.get('material_type', 'textbook'),
            is_required=data.get('is_required', True)
        )
        
        db.session.add(material)
        db.session.commit()
        
        return jsonify(material.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@course_bp.route('/courses/<int:course_id>/syllabus', methods=['GET'])
@jwt_required()
def get_course_syllabus(course_id):
    """강의계획서 조회"""
    try:
        user_id = get_jwt_identity()
        course = Course.query.get_or_404(course_id)
        
        # 접근 권한 확인
        user = User.query.get_or_404(user_id)
        if not ('admin' in user.get_roles() or 
                course.instructor_id == user_id or
                CourseEnrollment.query.filter_by(
                    course_id=course_id, student_id=user_id, status='enrolled'
                ).first()):
            return jsonify({'error': 'Access denied'}), 403
        
        syllabus_list = CourseSyllabus.query.filter_by(course_id=course_id).order_by(
            CourseSyllabus.version.desc()
        ).all()
        
        return jsonify([syllabus.to_dict() for syllabus in syllabus_list]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

