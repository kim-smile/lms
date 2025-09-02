from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, case

from src.models import db, User, Role, UserRole, Course, CourseEnrollment, CourseContent, ContentAccessLog, UserProgress, Attendance, LearningActivity, ActivitySubmission, QuizAttempt, LearningAnalytics, SystemLog, RiskAlert, CourseStatistics, UserStatistics, Quiz

analytics_bp = Blueprint("analytics", __name__)

# System Log Endpoints (Admin only)
@analytics_bp.route("/system_logs", methods=["GET"])
@jwt_required()
def get_system_logs():
    """시스템 로그 조회 (관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        if "admin" not in user.get_roles():
            return jsonify({"error": "Insufficient permissions"}), 403

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        search = request.args.get("search", "")
        action_type = request.args.get("action_type", "")

        query = SystemLog.query

        if search:
            query = query.filter(
                (SystemLog.action.contains(search)) |
                (SystemLog.resource_type.contains(search)) |
                (SystemLog.ip_address.contains(search))
            )
        if action_type:
            query = query.filter(SystemLog.action == action_type)

        logs = query.order_by(SystemLog.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            "logs": [log.to_dict() for log in logs.items],
            "total": logs.total,
            "pages": logs.pages,
            "current_page": page
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# User Learning Analytics
@analytics_bp.route("/analytics/users/<int:user_id>/progress_report", methods=["GET"])
@jwt_required()
def get_user_progress_report(user_id):
    """사용자 학습 진도 및 성취도 리포트 (관리자/교수/본인용)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get_or_404(current_user_id)

        if not (current_user_id == user_id or "admin" in current_user.get_roles() or "instructor" in current_user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        target_user = User.query.get_or_404(user_id)

        # Total enrolled courses
        total_enrolled_courses = CourseEnrollment.query.filter_by(student_id=user_id, status="enrolled").count()

        # Completed courses (simplified: all content completed)
        completed_courses_subquery = db.session.query(CourseContent.course_id).distinct().filter(
            CourseContent.id.in_(
                db.session.query(UserProgress.content_id).filter(
                    UserProgress.user_id == user_id,
                    UserProgress.completion_status == "completed"
                )
            )
        ).subquery()
        completed_courses_count = db.session.query(Course).filter(Course.id.in_(completed_courses_subquery)).count()

        # Average progress across all contents
        avg_progress = db.session.query(func.avg(UserProgress.progress_percentage)).filter_by(user_id=user_id).scalar()
        avg_progress = round(avg_progress, 2) if avg_progress else 0

        # Quiz performance
        total_quiz_attempts = QuizAttempt.query.filter_by(student_id=user_id).count()
        avg_quiz_score = db.session.query(func.avg(QuizAttempt.score)).filter_by(student_id=user_id, status="completed").scalar()
        avg_quiz_score = round(avg_quiz_score, 2) if avg_quiz_score else 0

        # Activity submission rate
        total_activities = LearningActivity.query.join(Course).join(CourseEnrollment).filter(
            CourseEnrollment.student_id == user_id,
            CourseEnrollment.status == "enrolled"
        ).count()
        submitted_activities = ActivitySubmission.query.filter_by(student_id=user_id).count()
        submission_rate = round((submitted_activities / total_activities) * 100, 2) if total_activities > 0 else 0

        report = {
            "user_id": target_user.id,
            "username": target_user.username,
            "total_enrolled_courses": total_enrolled_courses,
            "completed_courses_count": completed_courses_count,
            "average_content_progress": avg_progress,
            "total_quiz_attempts": total_quiz_attempts,
            "average_quiz_score": avg_quiz_score,
            "activity_submission_rate": submission_rate
        }

        return jsonify(report), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Course Analytics
@analytics_bp.route("/analytics/courses/<int:course_id>/statistics", methods=["GET"])
@jwt_required()
def get_course_statistics(course_id):
    """강좌 통계 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        course = Course.query.get_or_404(course_id)

        if not ("admin" in user.get_roles() or course.instructor_id == user_id):
            return jsonify({"error": "Insufficient permissions"}), 403

        # Total enrolled students
        total_students = CourseEnrollment.query.filter_by(course_id=course_id, status="enrolled").count()

        # Average course progress
        avg_course_progress = db.session.query(func.avg(UserProgress.progress_percentage)).filter_by(course_id=course_id).scalar()
        avg_course_progress = round(avg_course_progress, 2) if avg_course_progress else 0

        # Content access frequency
        content_access_counts = db.session.query(
            CourseContent.title, func.count(ContentAccessLog.id)
        ).join(ContentAccessLog).filter(
            CourseContent.course_id == course_id
        ).group_by(CourseContent.title).all()
        content_access_data = [{ "title": title, "access_count": count } for title, count in content_access_counts]

        # Quiz average scores for the course
        quiz_avg_scores = db.session.query(
            Quiz.title, func.avg(QuizAttempt.score)
        ).join(QuizAttempt).filter(
            Quiz.course_id == course_id,
            QuizAttempt.status == "completed"
        ).group_by(Quiz.title).all()
        quiz_scores_data = [{ "title": title, "average_score": round(score, 2) } for title, score in quiz_avg_scores]

        # Activity submission rates for the course
        activity_submission_counts = db.session.query(
            LearningActivity.title, func.count(ActivitySubmission.id)
        ).join(ActivitySubmission).filter(
            LearningActivity.course_id == course_id
        ).group_by(LearningActivity.title).all()
        activity_submission_data = [{ "title": title, "submission_count": count } for title, count in activity_submission_counts]

        statistics = {
            "course_id": course.id,
            "course_title": course.title,
            "total_enrolled_students": total_students,
            "average_course_progress": avg_course_progress,
            "content_access_frequency": content_access_data,
            "quiz_average_scores": quiz_scores_data,
            "activity_submission_counts": activity_submission_data
        }

        return jsonify(statistics), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Risk Alert System (Admin/Instructor only)
@analytics_bp.route("/analytics/risk_alerts", methods=["GET"])
@jwt_required()
def get_risk_alerts():
    """위험군(학습 부진자) 조기 경고 목록 조회 (관리자/교수용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        if not ("admin" in user.get_roles() or "instructor" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        # Example logic for identifying at-risk students:
        # 1. Low average content progress (e.g., < 50%)
        # 2. Low quiz scores (e.g., avg < 60%)
        # 3. Low activity submission rate (e.g., < 50%)
        # 4. Infrequent content access

        at_risk_students = []

        # Get all enrolled students
        all_students = db.session.query(User).join(UserRole).join(Role).filter(Role.name == "student").all()

        for student in all_students:
            # Calculate metrics for each student
            avg_progress = db.session.query(func.avg(UserProgress.progress_percentage)).filter_by(user_id=student.id).scalar()
            avg_progress = round(avg_progress, 2) if avg_progress else 0

            avg_quiz_score = db.session.query(func.avg(QuizAttempt.score)).filter_by(student_id=student.id, status="completed").scalar()
            avg_quiz_score = round(avg_quiz_score, 2) if avg_quiz_score else 0

            total_activities = LearningActivity.query.join(Course).join(CourseEnrollment).filter(
                CourseEnrollment.student_id == student.id,
                CourseEnrollment.status == "enrolled"
            ).count()
            submitted_activities = ActivitySubmission.query.filter_by(student_id=student.id).count()
            submission_rate = round((submitted_activities / total_activities) * 100, 2) if total_activities > 0 else 0

            # Define risk criteria
            is_at_risk = False
            reasons = []

            if avg_progress < 50:
                is_at_risk = True
                reasons.append(f"Low content progress ({avg_progress}%)")
            if avg_quiz_score < 60:
                is_at_risk = True
                reasons.append(f"Low average quiz score ({avg_quiz_score}%)")
            if submission_rate < 50:
                is_at_risk = True
                reasons.append(f"Low activity submission rate ({submission_rate}%)")

            if is_at_risk:
                at_risk_students.append({
                    "student_id": student.id,
                    "username": student.username,
                    "email": student.email,
                    "reasons": reasons,
                    "metrics": {
                        "avg_progress": avg_progress,
                        "avg_quiz_score": avg_quiz_score,
                        "submission_rate": submission_rate
                    }
                })
        return jsonify(at_risk_students), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

