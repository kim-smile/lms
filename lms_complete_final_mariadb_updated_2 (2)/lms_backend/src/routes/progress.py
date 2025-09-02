from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from src.models import db, User
from src.models import Course, CourseEnrollment, CourseSection
from src.models import CourseContent
from src.models import UserProgress, Attendance, LearningActivity, ActivitySubmission
from src.models import SystemLog

progress_bp = Blueprint("progress", __name__)

# User Progress Endpoints
@progress_bp.route("/users/<int:user_id>/progress", methods=["GET"])
@jwt_required()
def get_user_progress(user_id):
    """특정 사용자의 학습 진도 조회"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get_or_404(current_user_id)

        # Only allow user to view their own progress or admin/instructor to view others
        if not (current_user_id == user_id or "admin" in current_user.get_roles() or "instructor" in current_user.get_roles()):
            return jsonify({"error": "Access denied"}), 403

        progress_records = UserProgress.query.filter_by(user_id=user_id).all()
        return jsonify([p.to_dict() for p in progress_records]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@progress_bp.route("/contents/<int:content_id>/progress", methods=["POST"])
@jwt_required()
def update_content_progress(content_id):
    """콘텐츠 학습 진도 업데이트"""
    try:
        user_id = get_jwt_identity()
        data = request.json

        progress_percentage = data.get("progress_percentage", type=float)
        completion_status = data.get("completion_status")
        total_time_spent = data.get("total_time_spent", type=int)

        if progress_percentage is None or not (0 <= progress_percentage <= 100):
            return jsonify({"error": "progress_percentage must be between 0 and 100"}), 400

        content = CourseContent.query.get_or_404(content_id)
        course_id = content.course_id

        user_progress = UserProgress.query.filter_by(user_id=user_id, content_id=content_id).first()

        if not user_progress:
            user_progress = UserProgress(
                user_id=user_id,
                course_id=course_id,
                content_id=content_id,
                first_accessed_at=datetime.utcnow()
            )
            db.session.add(user_progress)

        user_progress.progress_percentage = progress_percentage
        user_progress.completion_status = completion_status or user_progress.completion_status
        user_progress.last_accessed_at = datetime.utcnow()
        user_progress.total_time_spent = total_time_spent or user_progress.total_time_spent

        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="update_content_progress",
            resource_type="user_progress",
            resource_id=user_progress.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(user_progress.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Attendance Endpoints
@progress_bp.route("/courses/<int:course_id>/attendance", methods=["GET"])
@jwt_required()
def get_course_attendance(course_id):
    """강좌 출석 기록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        course = Course.query.get_or_404(course_id)

        # Access control: instructor, admin, or enrolled student (only their own records)
        if "student" in user.get_roles() and not CourseEnrollment.query.filter_by(course_id=course_id, student_id=user_id, status="enrolled").first():
            return jsonify({"error": "Access denied"}), 403

        if "student" in user.get_roles():
            attendance_records = Attendance.query.filter_by(course_id=course_id, student_id=user_id).all()
        else:
            attendance_records = Attendance.query.filter_by(course_id=course_id).all()

        return jsonify([a.to_dict() for a in attendance_records]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@progress_bp.route("/courses/<int:course_id>/attendance", methods=["POST"])
@jwt_required()
def record_attendance(course_id):
    """출석 기록 (교수/관리자용 또는 코드 기반)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        course = Course.query.get_or_404(course_id)

        data = request.json
        student_id = data.get("student_id", user_id) # For students, their own ID; for instructors, student ID
        attendance_date_str = data.get("attendance_date", datetime.utcnow().isoformat())
        attendance_date = datetime.fromisoformat(attendance_date_str).date()
        status = data.get("status", "present")
        attendance_type = data.get("attendance_type", "manual")
        attendance_code = data.get("attendance_code")
        section_id = data.get("section_id")

        # Instructor/Admin can record for others, or student can record for themselves with code
        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            if attendance_type == "code" and attendance_code:
                # TODO: Validate attendance code against a generated one for the course/session
                # For now, just check if it's provided
                if not attendance_code:
                    return jsonify({"error": "Attendance code is required for code-based attendance"}), 400
                if student_id != user_id: # Students can only record their own attendance via code
                    return jsonify({"error": "Students can only record their own attendance"}), 403
            else:
                return jsonify({"error": "Insufficient permissions to record attendance"}), 403

        existing_attendance = Attendance.query.filter_by(
            course_id=course_id, student_id=student_id, attendance_date=attendance_date
        ).first()

        if existing_attendance:
            return jsonify({"error": "Attendance already recorded for this student on this date"}), 400

        attendance = Attendance(
            course_id=course_id,
            section_id=section_id,
            student_id=student_id,
            attendance_date=attendance_date,
            status=status,
            attendance_type=attendance_type,
            attendance_code=attendance_code,
            recorded_by=user_id
        )
        db.session.add(attendance)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="record_attendance",
            resource_type="attendance",
            resource_id=attendance.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(attendance.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Learning Activity Endpoints
@progress_bp.route("/courses/<int:course_id>/activities", methods=["GET"])
@jwt_required()
def get_learning_activities(course_id):
    """강좌 학습 활동 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        course = Course.query.get_or_404(course_id)

        # Access control: instructor, admin, or enrolled student
        if not ("admin" in user.get_roles() or
                course.instructor_id == user_id or
                CourseEnrollment.query.filter_by(course_id=course_id, student_id=user_id, status="enrolled").first()):
            return jsonify({"error": "Access denied"}), 403

        activities = LearningActivity.query.filter_by(course_id=course_id).order_by(LearningActivity.due_date).all()
        return jsonify([a.to_dict() for a in activities]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@progress_bp.route("/courses/<int:course_id>/activities", methods=["POST"])
@jwt_required()
def create_learning_activity(course_id):
    """학습 활동 생성 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        course = Course.query.get_or_404(course_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        required_fields = ["title", "activity_type"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        activity = LearningActivity(
            course_id=course_id,
            title=data["title"],
            description=data.get("description"),
            activity_type=data["activity_type"],
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            max_points=data.get("max_points"),
            is_published=data.get("is_published", False),
            created_by=user_id
        )
        db.session.add(activity)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="create_learning_activity",
            resource_type="learning_activity",
            resource_id=activity.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(activity.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@progress_bp.route("/activities/<int:activity_id>", methods=["GET"])
@jwt_required()
def get_learning_activity(activity_id):
    """특정 학습 활동 상세 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        activity = LearningActivity.query.get_or_404(activity_id)
        course = Course.query.get_or_404(activity.course_id)

        # Access control: instructor, admin, or enrolled student
        if not ("admin" in user.get_roles() or
                course.instructor_id == user_id or
                CourseEnrollment.query.filter_by(course_id=course.id, student_id=user_id, status="enrolled").first()):
            return jsonify({"error": "Access denied"}), 403

        return jsonify(activity.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@progress_bp.route("/activities/<int:activity_id>", methods=["PUT"])
@jwt_required()
def update_learning_activity(activity_id):
    """학습 활동 수정 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        activity = LearningActivity.query.get_or_404(activity_id)
        course = Course.query.get_or_404(activity.course_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        updatable_fields = [
            "title", "description", "activity_type", "due_date",
            "max_points", "is_published"
        ]

        for field in updatable_fields:
            if field in data:
                if field == "due_date" and data[field]:
                    setattr(activity, field, datetime.fromisoformat(data[field]))
                else:
                    setattr(activity, field, data[field])

        activity.updated_at = datetime.utcnow()
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="update_learning_activity",
            resource_type="learning_activity",
            resource_id=activity.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(activity.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@progress_bp.route("/activities/<int:activity_id>", methods=["DELETE"])
@jwt_required()
def delete_learning_activity(activity_id):
    """학습 활동 삭제 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        activity = LearningActivity.query.get_or_404(activity_id)
        course = Course.query.get_or_404(activity.course_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        db.session.delete(activity)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="delete_learning_activity",
            resource_type="learning_activity",
            resource_id=activity.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return "", 204
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Activity Submission Endpoints
@progress_bp.route("/activities/<int:activity_id>/submissions", methods=["GET"])
@jwt_required()
def get_activity_submissions(activity_id):
    """학습 활동 제출 목록 조회 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        activity = LearningActivity.query.get_or_404(activity_id)
        course = Course.query.get_or_404(activity.course_id)

        # Access control: instructor, admin, or student (only their own submission)
        if "student" in user.get_roles():
            submission = ActivitySubmission.query.filter_by(activity_id=activity_id, student_id=user_id).first()
            return jsonify([submission.to_dict()]) if submission else jsonify([]), 200
        elif not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        submissions = ActivitySubmission.query.filter_by(activity_id=activity_id).all()
        return jsonify([s.to_dict() for s in submissions]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@progress_bp.route("/activities/<int:activity_id>/submit", methods=["POST"])
@jwt_required()
def submit_activity(activity_id):
    """학습 활동 제출"""
    try:
        user_id = get_jwt_identity()
        activity = LearningActivity.query.get_or_404(activity_id)

        # Check if already submitted
        existing_submission = ActivitySubmission.query.filter_by(activity_id=activity_id, student_id=user_id).first()
        if existing_submission:
            return jsonify({"error": "Activity already submitted"}), 400

        data = request.json
        submission_text = data.get("submission_text")
        file_path = data.get("file_path") # Assuming file is already uploaded and path is provided

        if not submission_text and not file_path:
            return jsonify({"error": "Submission text or file path is required"}), 400

        submission = ActivitySubmission(
            activity_id=activity_id,
            student_id=user_id,
            submission_text=submission_text,
            file_path=file_path
        )
        db.session.add(submission)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="submit_activity",
            resource_type="activity_submission",
            resource_id=submission.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(submission.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@progress_bp.route("/submissions/<int:submission_id>/grade", methods=["PUT"])
@jwt_required()
def grade_submission(submission_id):
    """제출된 학습 활동 채점 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        submission = ActivitySubmission.query.get_or_404(submission_id)
        activity = LearningActivity.query.get_or_404(submission.activity_id)
        course = Course.query.get_or_404(activity.course_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        score = data.get("score", type=float)
        feedback = data.get("feedback")

        if score is None:
            return jsonify({"error": "Score is required"}), 400

        submission.score = score
        submission.feedback = feedback
        submission.status = "graded"
        submission.graded_by = user_id
        submission.graded_at = datetime.utcnow()

        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="grade_submission",
            resource_type="activity_submission",
            resource_id=submission.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(submission.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

