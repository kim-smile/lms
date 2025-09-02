from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from datetime import datetime
from src.models import db, User, Role, UserRole
from src.models import SystemLog

user_bp = Blueprint('user', __name__)

# Authentication endpoints
@user_bp.route('/auth/register', methods=['POST'])
def register():
    """사용자 회원가입"""
    try:
        data = request.json
        
        # 필수 필드 검증
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # 중복 사용자 확인
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # 새 사용자 생성
        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            is_verified=False
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # 기본 역할 할당 (학생)
        student_role = Role.query.filter_by(name='student').first()
        if student_role:
            user_role = UserRole(user_id=user.id, role_id=student_role.id)
            db.session.add(user_role)
        
        db.session.commit()
        
        # 시스템 로그 기록
        log = SystemLog(
            user_id=user.id,
            action='user_register',
            resource_type='user',
            resource_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/auth/login', methods=['POST'])
def login():
    """사용자 로그인"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # 사용자 확인 (username 또는 email로 로그인 가능)
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # 마지막 로그인 시간 업데이트
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # JWT 토큰 생성
        access_token = create_access_token(identity=user.id)
        
        # 시스템 로그 기록
        log = SystemLog(
            user_id=user.id,
            action='user_login',
            resource_type='user',
            resource_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """현재 사용자 프로필 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/auth/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """현재 사용자 프로필 수정"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        data = request.json
        
        # 업데이트 가능한 필드들
        updatable_fields = ['first_name', 'last_name', 'phone', 'profile_image_url']
        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 시스템 로그 기록
        log = SystemLog(
            user_id=user.id,
            action='profile_update',
            resource_type='user',
            resource_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """비밀번호 변경"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        data = request.json
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 시스템 로그 기록
        log = SystemLog(
            user_id=user.id,
            action='password_change',
            resource_type='user',
            resource_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# User management endpoints (Admin only)
@user_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """사용자 목록 조회 (관리자용)"""
    try:
        # TODO: 관리자 권한 확인 로직 추가
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        role = request.args.get('role', '')
        
        query = User.query
        
        # 검색 필터
        if search:
            query = query.filter(
                (User.username.contains(search)) |
                (User.email.contains(search)) |
                (User.first_name.contains(search)) |
                (User.last_name.contains(search))
            )
        
        # 역할 필터
        if role:
            query = query.join(UserRole).join(Role).filter(Role.name == role)
        
        users = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """특정 사용자 조회"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """사용자 정보 수정 (관리자용)"""
    try:
        # TODO: 관리자 권한 확인 로직 추가
        user = User.query.get_or_404(user_id)
        data = request.json
        
        # 업데이트 가능한 필드들
        updatable_fields = [
            'username', 'email', 'first_name', 'last_name', 
            'phone', 'is_active', 'is_verified'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """사용자 삭제 (관리자용)"""
    try:
        # TODO: 관리자 권한 확인 로직 추가
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Role management endpoints
@user_bp.route('/roles', methods=['GET'])
@jwt_required()
def get_roles():
    """역할 목록 조회"""
    try:
        roles = Role.query.all()
        return jsonify([role.to_dict() for role in roles]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<int:user_id>/roles', methods=['POST'])
@jwt_required()
def assign_role(user_id):
    """사용자에게 역할 할당"""
    try:
        # TODO: 관리자 권한 확인 로직 추가
        current_user_id = get_jwt_identity()
        data = request.json
        role_id = data.get('role_id')
        
        if not role_id:
            return jsonify({'error': 'role_id is required'}), 400
        
        # 중복 확인
        existing = UserRole.query.filter_by(
            user_id=user_id, role_id=role_id
        ).first()
        
        if existing:
            return jsonify({'error': 'Role already assigned'}), 400
        
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=current_user_id
        )
        
        db.session.add(user_role)
        db.session.commit()
        
        return jsonify(user_role.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<int:user_id>/roles/<int:role_id>', methods=['DELETE'])
@jwt_required()
def remove_role(user_id, role_id):
    """사용자에게서 역할 제거"""
    try:
        # TODO: 관리자 권한 확인 로직 추가
        user_role = UserRole.query.filter_by(
            user_id=user_id, role_id=role_id
        ).first_or_404()
        
        db.session.delete(user_role)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
