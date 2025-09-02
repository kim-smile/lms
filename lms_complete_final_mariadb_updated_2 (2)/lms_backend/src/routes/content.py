from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from src.models import db, User
from src.models import Course, CourseEnrollment
from src.models import ContentCategory, CourseContent, ContentVersion, ContentAccessLog
from src.models import SystemLog

content_bp = Blueprint("content", __name__)

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

# Content Category Endpoints
@content_bp.route("/content/categories", methods=["GET"])
@jwt_required()
def get_content_categories():
    """콘텐츠 카테고리 목록 조회"""
    try:
        categories = ContentCategory.query.all()
        return jsonify([category.to_dict() for category in categories]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.route("/content/categories", methods=["POST"])
@jwt_required()
def create_content_category():
    """콘텐츠 카테고리 생성 (관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        if "admin" not in user.get_roles():
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        if not data.get("name"):
            return jsonify({"error": "Category name is required"}), 400

        if ContentCategory.query.filter_by(name=data["name"]).first():
            return jsonify({"error": "Category with this name already exists"}), 400

        category = ContentCategory(
            name=data["name"],
            description=data.get("description"),
            parent_id=data.get("parent_id")
        )
        db.session.add(category)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="create_content_category",
            resource_type="content_category",
            resource_id=category.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(category.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Course Content Endpoints
@content_bp.route("/courses/<int:course_id>/contents", methods=["GET"])
@jwt_required()
def get_course_contents(course_id):
    """강좌 콘텐츠 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        course = Course.query.get_or_404(course_id)

        # Access control: instructor, admin, or enrolled student
        if not ("admin" in user.get_roles() or
                course.instructor_id == user_id or
                CourseEnrollment.query.filter_by(course_id=course_id, student_id=user_id, status="enrolled").first()):
            return jsonify({"error": "Access denied"}), 403

        contents = CourseContent.query.filter_by(course_id=course_id).order_by(CourseContent.week_number, CourseContent.lesson_order).all()
        return jsonify([content.to_dict() for content in contents]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.route("/courses/<int:course_id>/contents", methods=["POST"])
@jwt_required()
def upload_course_content(course_id):
    """강좌 콘텐츠 업로드 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        course = Course.query.get_or_404(course_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        # Check if the post request has the file part
        if "file" not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, current_app.config["UPLOAD_FOLDER"], str(course_id))
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            # Get other form data
            title = request.form.get("title")
            description = request.form.get("description")
            content_type = request.form.get("content_type")
            category_id = request.form.get("category_id", type=int)
            week_number = request.form.get("week_number", type=int)
            lesson_order = request.form.get("lesson_order", type=int)
            is_published = request.form.get("is_published", "false").lower() == "true"
            access_start_date = request.form.get("access_start_date")
            access_end_date = request.form.get("access_end_date")

            content = CourseContent(
                course_id=course_id,
                title=title or filename,
                description=description,
                content_type=content_type or "file",
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                category_id=category_id,
                week_number=week_number,
                lesson_order=lesson_order,
                is_published=is_published,
                access_start_date=datetime.fromisoformat(access_start_date) if access_start_date else None,
                access_end_date=datetime.fromisoformat(access_end_date) if access_end_date else None,
                created_by=user_id
            )
            db.session.add(content)
            db.session.commit()

            # Record initial version
            content_version = ContentVersion(
                content_id=content.id,
                version_number=1,
                file_path=content.file_path,
                file_size=content.file_size,
                change_description="Initial upload",
                created_by=user_id
            )
            db.session.add(content_version)
            db.session.commit()

            log = SystemLog(
                user_id=user_id,
                action="upload_course_content",
                resource_type="course_content",
                resource_id=content.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
            )
            db.session.add(log)
            db.session.commit()

            return jsonify(content.to_dict()), 201
        else:
            return jsonify({"error": "File type not allowed"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@content_bp.route("/contents/<int:content_id>", methods=["GET"])
@jwt_required()
def get_content_details(content_id):
    """특정 콘텐츠 상세 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        content = CourseContent.query.get_or_404(content_id)
        course = Course.query.get_or_404(content.course_id)

        # Access control: instructor, admin, or enrolled student
        if not ("admin" in user.get_roles() or
                course.instructor_id == user_id or
                CourseEnrollment.query.filter_by(course_id=course.id, student_id=user_id, status="enrolled").first()):
            return jsonify({"error": "Access denied"}), 403

        # Record content access log
        log = ContentAccessLog(
            content_id=content.id,
            user_id=user_id,
            device_type=request.user_agent.platform,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(content.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.route("/contents/<int:content_id>", methods=["PUT"])
@jwt_required()
def update_course_content(content_id):
    """강좌 콘텐츠 정보 수정 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        content = CourseContent.query.get_or_404(content_id)
        course = Course.query.get_or_404(content.course_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json

        updatable_fields = [
            "title", "description", "content_type", "category_id",
            "week_number", "lesson_order", "is_published",
            "access_start_date", "access_end_date", "duration"
        ]

        for field in updatable_fields:
            if field in data:
                if field in ["access_start_date", "access_end_date"] and data[field]:
                    setattr(content, field, datetime.fromisoformat(data[field]))
                else:
                    setattr(content, field, data[field])

        content.updated_at = datetime.utcnow()
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="update_course_content",
            resource_type="course_content",
            resource_id=content.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(content.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@content_bp.route("/contents/<int:content_id>", methods=["DELETE"])
@jwt_required()
def delete_course_content(content_id):
    """강좌 콘텐츠 삭제 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        content = CourseContent.query.get_or_404(content_id)
        course = Course.query.get_or_404(content.course_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        # Delete associated file if exists
        if content.file_path and os.path.exists(content.file_path):
            os.remove(content.file_path)

        db.session.delete(content)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="delete_course_content",
            resource_type="course_content",
            resource_id=content.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return "", 204
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Content Versioning Endpoints
@content_bp.route("/contents/<int:content_id>/versions", methods=["GET"])
@jwt_required()
def get_content_versions(content_id):
    """콘텐츠 버전 이력 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        content = CourseContent.query.get_or_404(content_id)
        course = Course.query.get_or_404(content.course_id)

        # Access control: instructor, admin, or enrolled student
        if not ("admin" in user.get_roles() or
                course.instructor_id == user_id or
                CourseEnrollment.query.filter_by(course_id=course.id, student_id=user_id, status="enrolled").first()):
            return jsonify({"error": "Access denied"}), 403

        versions = ContentVersion.query.filter_by(content_id=content_id).order_by(ContentVersion.version_number.desc()).all()
        return jsonify([version.to_dict() for version in versions]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@content_bp.route("/contents/<int:content_id>/versions", methods=["POST"])
@jwt_required()
def create_content_version(content_id):
    """콘텐츠 새 버전 생성 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        content = CourseContent.query.get_or_404(content_id)
        course = Course.query.get_or_404(content.course_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        if "file" not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, current_app.config["UPLOAD_FOLDER"], str(course.id))
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            # Update current content record
            content.file_path = file_path
            content.file_size = os.path.getsize(file_path)
            content.version += 1
            content.updated_at = datetime.utcnow()

            # Create new version record
            content_version = ContentVersion(
                content_id=content.id,
                version_number=content.version,
                file_path=file_path,
                file_size=content.file_size,
                change_description=request.form.get("change_description", "Updated content"),
                created_by=user_id
            )
            db.session.add(content_version)
            db.session.commit()

            log = SystemLog(
                user_id=user_id,
                action="create_content_version",
                resource_type="content_version",
                resource_id=content_version.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
            )
            db.session.add(log)
            db.session.commit()

            return jsonify(content.to_dict()), 201
        else:
            return jsonify({"error": "File type not allowed"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@content_bp.route("/contents/<int:content_id>/versions/<int:version_number>/restore", methods=["POST"])
@jwt_required()
def restore_content_version(content_id, version_number):
    """콘텐츠 이전 버전으로 복원 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        content = CourseContent.query.get_or_404(content_id)
        course = Course.query.get_or_404(content.course_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        version_to_restore = ContentVersion.query.filter_by(
            content_id=content_id, version_number=version_number
        ).first_or_404()

        # Update current content with old version data
        content.file_path = version_to_restore.file_path
        content.file_size = version_to_restore.file_size
        content.version = version_to_restore.version_number
        content.updated_at = datetime.utcnow()

        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="restore_content_version",
            resource_type="content_version",
            resource_id=version_to_restore.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(content.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

