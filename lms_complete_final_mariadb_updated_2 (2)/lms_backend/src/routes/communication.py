from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from src.models import db, User
from src.models import Course, CourseEnrollment
from src.models import (
    Announcement, Message, MessageRecipient, DiscussionForum,
    DiscussionTopic, DiscussionPost, ProjectGroup, GroupMember
)
from src.models import SystemLog

communication_bp = Blueprint("communication", __name__)

# Announcement Endpoints
@communication_bp.route("/announcements", methods=["GET"])
@jwt_required()
def get_announcements():
    """공지사항 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        # Filter announcements based on user's enrolled courses or admin status
        if "admin" in user.get_roles():
            announcements = Announcement.query.all()
        else:
            enrolled_course_ids = [e.course_id for e in CourseEnrollment.query.filter_by(student_id=user_id, status="enrolled").all()]
            announcements = Announcement.query.filter(
                (Announcement.course_id.in_(enrolled_course_ids)) | (Announcement.course_id == None) # General announcements
            ).all()

        return jsonify([a.to_dict() for a in announcements]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@communication_bp.route("/announcements", methods=["POST"])
@jwt_required()
def create_announcement():
    """공지사항 생성 (교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        if not ("instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        required_fields = ["title", "content"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        announcement = Announcement(
            title=data["title"],
            content=data["content"],
            course_id=data.get("course_id"), # Optional: for course-specific announcements
            created_by=user_id
        )
        db.session.add(announcement)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="create_announcement",
            resource_type="announcement",
            resource_id=announcement.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(announcement.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Message Endpoints
@communication_bp.route("/messages", methods=["GET"])
@jwt_required()
def get_messages():
    """사용자 메시지 목록 조회"""
    try:
        user_id = get_jwt_identity()
        messages = Message.query.join(MessageRecipient).filter(
            MessageRecipient.recipient_id == user_id
        ).order_by(Message.sent_at.desc()).all()

        return jsonify([m.to_dict() for m in messages]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@communication_bp.route("/messages", methods=["POST"])
@jwt_required()
def send_message():
    """메시지 전송"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        required_fields = ["subject", "content", "recipient_ids"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        message = Message(
            sender_id=user_id,
            subject=data["subject"],
            content=data["content"]
        )
        db.session.add(message)
        db.session.flush() # To get message.id

        for recipient_id in data["recipient_ids"]:
            recipient = MessageRecipient(
                message_id=message.id,
                recipient_id=recipient_id
            )
            db.session.add(recipient)

        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="send_message",
            resource_type="message",
            resource_id=message.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(message.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Discussion Forum Endpoints
@communication_bp.route("/discussion_forums", methods=["GET"])
@jwt_required()
def get_discussion_forums():
    """토론 포럼 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        # Filter forums based on user's enrolled courses or admin status
        if "admin" in user.get_roles():
            forums = DiscussionForum.query.all()
        else:
            enrolled_course_ids = [e.course_id for e in CourseEnrollment.query.filter_by(student_id=user_id, status="enrolled").all()]
            forums = DiscussionForum.query.filter(
                (DiscussionForum.course_id.in_(enrolled_course_ids)) | (DiscussionForum.course_id == None) # General forums
            ).all()

        return jsonify([f.to_dict() for f in forums]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@communication_bp.route("/discussion_forums/<int:forum_id>/topics", methods=["GET"])
@jwt_required()
def get_discussion_topics(forum_id):
    """토론 포럼 내 토픽 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        forum = DiscussionForum.query.get_or_404(forum_id)

        # Access control: check if user has access to the course associated with the forum
        if forum.course_id:
            course = Course.query.get_or_404(forum.course_id)
            if not ("admin" in user.get_roles() or
                    course.instructor_id == user_id or
                    CourseEnrollment.query.filter_by(course_id=course.id, student_id=user_id, status="enrolled").first()):
                return jsonify({"error": "Access denied"}), 403

        topics = DiscussionTopic.query.filter_by(forum_id=forum_id).order_by(DiscussionTopic.created_at.desc()).all()
        return jsonify([t.to_dict() for t in topics]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@communication_bp.route("/discussion_topics/<int:topic_id>/posts", methods=["GET"])
@jwt_required()
def get_discussion_posts(topic_id):
    """토론 토픽 내 게시글 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        topic = DiscussionTopic.query.get_or_404(topic_id)
        forum = DiscussionForum.query.get_or_404(topic.forum_id)

        # Access control: check if user has access to the course associated with the forum
        if forum.course_id:
            course = Course.query.get_or_404(forum.course_id)
            if not ("admin" in user.get_roles() or
                    course.instructor_id == user_id or
                    CourseEnrollment.query.filter_by(course_id=course.id, student_id=user_id, status="enrolled").first()):
                return jsonify({"error": "Access denied"}), 403

        posts = DiscussionPost.query.filter_by(topic_id=topic_id).order_by(DiscussionPost.created_at.asc()).all()
        return jsonify([p.to_dict() for p in posts]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@communication_bp.route("/discussion_topics/<int:topic_id>/posts", methods=["POST"])
@jwt_required()
def create_discussion_post(topic_id):
    """토론 게시글 생성"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        topic = DiscussionTopic.query.get_or_404(topic_id)
        forum = DiscussionForum.query.get_or_404(topic.forum_id)

        # Access control: check if user has access to the course associated with the forum
        if forum.course_id:
            course = Course.query.get_or_404(forum.course_id)
            if not ("admin" in user.get_roles() or
                    course.instructor_id == user_id or
                    CourseEnrollment.query.filter_by(course_id=course.id, student_id=user_id, status="enrolled").first()):
                return jsonify({"error": "Access denied"}), 403

        data = request.json
        if not data.get("content"):
            return jsonify({"error": "Content is required"}), 400

        post = DiscussionPost(
            topic_id=topic_id,
            author_id=user_id,
            content=data["content"],
            parent_post_id=data.get("parent_post_id")
        )
        db.session.add(post)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="create_discussion_post",
            resource_type="discussion_post",
            resource_id=post.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(post.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Project Group Endpoints
@communication_bp.route("/project_groups", methods=["GET"])
@jwt_required()
def get_project_groups():
    """프로젝트 그룹 목록 조회"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        # Only show groups the user is a member of, or all for admin/instructor
        if "admin" in user.get_roles() or "instructor" in user.get_roles():
            groups = ProjectGroup.query.all()
        else:
            groups = ProjectGroup.query.join(GroupMember).filter(GroupMember.member_id == user_id).all()

        return jsonify([g.to_dict() for g in groups]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@communication_bp.route("/project_groups", methods=["POST"])
@jwt_required()
def create_project_group():
    """프로젝트 그룹 생성 (교수/관리자용)"""
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

        group = ProjectGroup(
            name=data["name"],
            course_id=data["course_id"],
            description=data.get("description"),
            created_by=user_id
        )
        db.session.add(group)
        db.session.flush()

        # Add creator as a member
        member = GroupMember(
            group_id=group.id,
            member_id=user_id,
            role="leader"
        )
        db.session.add(member)

        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="create_project_group",
            resource_type="project_group",
            resource_id=group.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(group.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@communication_bp.route("/project_groups/<int:group_id>/members", methods=["POST"])
@jwt_required()
def add_group_member(group_id):
    """프로젝트 그룹에 멤버 추가 (그룹 리더/교수/관리자용)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        group = ProjectGroup.query.get_or_404(group_id)

        # Check permissions: group leader, instructor, or admin
        is_leader = GroupMember.query.filter_by(group_id=group_id, member_id=user_id, role="leader").first()
        if not (is_leader or "instructor" in user.get_roles() or "admin" in user.get_roles()):
            return jsonify({"error": "Insufficient permissions"}), 403

        data = request.json
        member_to_add_id = data.get("member_id")
        member_role = data.get("role", "member")

        if not member_to_add_id:
            return jsonify({"error": "member_id is required"}), 400

        if GroupMember.query.filter_by(group_id=group_id, member_id=member_to_add_id).first():
            return jsonify({"error": "User is already a member of this group"}), 400

        member = GroupMember(
            group_id=group_id,
            member_id=member_to_add_id,
            role=member_role
        )
        db.session.add(member)
        db.session.commit()

        log = SystemLog(
            user_id=user_id,
            action="add_group_member",
            resource_type="group_member",
            resource_id=member.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        db.session.add(log)
        db.session.commit()

        return jsonify(member.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

