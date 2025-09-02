from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from src.models import db, User
from src.models import Course, CourseEnrollment
from src.models import (
    QuestionBank, Question, QuestionOption, Quiz, QuizQuestion,
    QuizAttempt, QuizResponse, Rubric, RubricCriterion, RubricLevel
)
from src.models import SystemLog

assessment_bp = Blueprint("assessment", __name__)

# Question Bank Endpoints
@assessment_bp.route("/question_banks", methods=["GET"])
@jwt_required()
def get_question_banks():
    """문제 은행 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        # Only instructor/admin can view all question banks
        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        banks = QuestionBank.query.all()
        return jsonify([bank.to_dict() for bank in banks]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@assessment_bp.route("/question_banks", methods=["POST"])
@jwt_required()
def create_question_bank():
    """문제 은행 생성 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        if not data.get("name"):
            return jsonify({"error": "Name is required"}), 400

        bank = QuestionBank(
            name=data["name"],
            description=data.get("description"),
            created_by=user_id
        )
        db.session.add(bank)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="create_question_bank",
            resource_type="question_bank",
            resource_id=bank.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(bank.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Question Endpoints
@assessment_bp.route("/question_banks/<int:bank_id>/questions", methods=["GET"])
@jwt_required()
def get_questions_in_bank(bank_id):
    """문제 은행 내 문제 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        bank = QuestionBank.query.get_or_404(bank_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        questions = Question.query.filter_by(bank_id=bank_id).all()
        return jsonify([q.to_dict() for q in questions]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@assessment_bp.route("/question_banks/<int:bank_id>/questions", methods=["POST"])
@jwt_required()
def create_question(bank_id):
    """문제 생성 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        bank = QuestionBank.query.get_or_404(bank_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        required_fields = ["question_text", "question_type"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        question = Question(
            bank_id=bank_id,
            question_text=data["question_text"],
            question_type=data["question_type"],
            correct_answer=data.get("correct_answer"),
            points=data.get("points", 1),
            created_by=user_id
        )
        db.session.add(question)
        db.session.flush() # To get question.id

        if data["question_type"] == "multiple_choice" and "options" in data:
            for option_data in data["options"]:
                option = QuestionOption(
                    question_id=question.id,
                    option_text=option_data["option_text"],
                    is_correct=option_data.get("is_correct", False)
                )
                db.session.add(option)

        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="create_question",
            resource_type="question",
            resource_id=question.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(question.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Quiz Endpoints
@assessment_bp.route("/quizzes", methods=["GET"])
@jwt_required()
def get_quizzes():
    """퀴즈 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        # Instructors/Admins can see all quizzes, students only quizzes for their enrolled courses
        if "student" in user.get_roles():
            quizzes = Quiz.query.join(Course).join(CourseEnrollment).filter(
                CourseEnrollment.student_id == user_id,
                CourseEnrollment.status == "enrolled"
            ).all()
        else:
            quizzes = Quiz.query.all()

        return jsonify([q.to_dict() for q in quizzes]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@assessment_bp.route("/quizzes", methods=["POST"])
@jwt_required()
def create_quiz():
    """퀴즈 생성 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        required_fields = ["title", "course_id"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        quiz = Quiz(
            title=data["title"],
            course_id=data["course_id"],
            description=data.get("description"),
            quiz_type=data.get("quiz_type", "quiz"),
            max_attempts=data.get("max_attempts"),
            time_limit_minutes=data.get("time_limit_minutes"),
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            is_published=data.get("is_published", False),
            created_by=user_id
        )
        db.session.add(quiz)
        db.session.flush() # To get quiz.id

        if "question_ids" in data:
            for q_id in data["question_ids"]:
                quiz_question = QuizQuestion(
                    quiz_id=quiz.id,
                    question_id=q_id
                )
                db.session.add(quiz_question)

        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="create_quiz",
            resource_type="quiz",
            resource_id=quiz.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(quiz.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Quiz Attempt Endpoints
@assessment_bp.route("/quizzes/<int:quiz_id>/start_attempt", methods=["POST"])
@jwt_required()
def start_quiz_attempt(quiz_id):
    """퀴즈 응시 시작"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        quiz = Quiz.query.get_or_404(quiz_id)

        # Check if student is enrolled in the course
        if not CourseEnrollment.query.filter_by(course_id=quiz.course_id, student_id=user_id, status="enrolled").first():
            return jsonify({"error": "Not enrolled in this course"}), 403

        # Check max attempts
        if quiz.max_attempts and QuizAttempt.query.filter_by(quiz_id=quiz_id, student_id=user_id).count() >= quiz.max_attempts:
            return jsonify({"error": "Maximum attempts reached"}), 400

        # Check time window
        now = datetime.utcnow()
        if quiz.start_time and now < quiz.start_time:
            return jsonify({"error": "Quiz has not started yet"}), 400
        if quiz.end_time and now > quiz.end_time:
            return jsonify({"error": "Quiz has ended"}), 400

        attempt = QuizAttempt(
            quiz_id=quiz_id,
            student_id=user_id,
            start_time=now
        )
        db.session.add(attempt)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="start_quiz_attempt",
            resource_type="quiz_attempt",
            resource_id=attempt.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(attempt.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@assessment_bp.route("/quiz_attempts/<int:attempt_id>/submit", methods=["POST"])
@jwt_required()
def submit_quiz_attempt(attempt_id):
    """퀴즈 응시 제출 및 자동 채점"""
    try:
        user_id = get_jwt_identity()
        attempt = QuizAttempt.query.get_or_404(attempt_id)

        if attempt.student_id != user_id:
            return jsonify({"error": "Access denied"}), 403
        if attempt.end_time is not None: # Already submitted
            return jsonify({"error": "Quiz attempt already submitted"}), 400

        attempt.end_time = datetime.utcnow()
        data = request.json
        responses = data.get("responses", [])

        total_score = 0
        max_score = 0

        for response_data in responses:
            question_id = response_data.get("question_id")
            answer_text = response_data.get("answer_text")
            selected_option_ids = response_data.get("selected_option_ids", [])

            question = Question.query.get(question_id)
            if not question:
                continue

            max_score += question.points

            is_correct = False
            if question.question_type == "multiple_choice":
                correct_options = [opt.id for opt in question.options if opt.is_correct]
                if sorted(selected_option_ids) == sorted(correct_options):
                    is_correct = True
            elif question.question_type == "true_false":
                if answer_text.lower() == question.correct_answer.lower():
                    is_correct = True
            elif question.question_type == "short_answer":
                # For short answer, simple exact match for auto-grading, or manual grading needed
                if answer_text and question.correct_answer and answer_text.lower() == question.correct_answer.lower():
                    is_correct = True

            if is_correct:
                total_score += question.points

            quiz_response = QuizResponse(
                attempt_id=attempt.id,
                question_id=question_id,
                answer_text=answer_text,
                is_correct=is_correct,
                score_earned=question.points if is_correct else 0
            )
            db.session.add(quiz_response)

        attempt.score = total_score
        attempt.max_score = max_score
        attempt.status = "completed"

        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="submit_quiz_attempt",
            resource_type="quiz_attempt",
            resource_id=attempt.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(attempt.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Rubric Endpoints
@assessment_bp.route("/rubrics", methods=["POST"])
@jwt_required()
def create_rubric():
    """루브릭 생성 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        required_fields = ["name", "course_id"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        rubric = Rubric(
            name=data["name"],
            course_id=data["course_id"],
            description=data.get("description"),
            created_by=user_id
        )
        db.session.add(rubric)
        db.session.flush()

        if "criteria" in data:
            for criterion_data in data["criteria"]:
                criterion = RubricCriterion(
                    rubric_id=rubric.id,
                    name=criterion_data["name"],
                    description=criterion_data.get("description"),
                    max_points=criterion_data.get("max_points"),
                    order=criterion_data.get("order")
                )
                db.session.add(criterion)
                db.session.flush()

                if "levels" in criterion_data:
                    for level_data in criterion_data["levels"]:
                        level = RubricLevel(
                            criterion_id=criterion.id,
                            name=level_data["name"],
                            description=level_data.get("description"),
                            points=level_data.get("points"),
                            order=level_data.get("order")
                        )
                        db.session.add(level)

        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="create_rubric",
            resource_type="rubric",
            resource_id=rubric.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(rubric.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

