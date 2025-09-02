from src.models.user import db
from datetime import datetime

class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    is_published = db.Column(db.Boolean, default=False)
    publish_date = db.Column(db.DateTime)
    expire_date = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', back_populates='announcements')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<Announcement {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'content': self.content,
            'priority': self.priority,
            'is_published': self.is_published,
            'publish_date': self.publish_date.isoformat() if self.publish_date else None,
            'expire_date': self.expire_date.isoformat() if self.expire_date else None,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='private')  # private, group
    parent_message_id = db.Column(db.Integer, db.ForeignKey('messages.id'))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id])
    parent_message = db.relationship('Message', remote_side=[id], backref='replies')
    recipients = db.relationship('MessageRecipient', back_populates='message', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Message {self.subject}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'sender_name': f"{self.sender.first_name} {self.sender.last_name}" if self.sender else None,
            'subject': self.subject,
            'content': self.content,
            'message_type': self.message_type,
            'parent_message_id': self.parent_message_id,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'is_read': self.is_read,
            'recipients': [recipient.to_dict() for recipient in self.recipients]
        }

class MessageRecipient(db.Model):
    __tablename__ = 'message_recipients'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relationships
    message = db.relationship('Message', back_populates='recipients')
    recipient = db.relationship('User', foreign_keys=[recipient_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'recipient_id': self.recipient_id,
            'recipient_name': f"{self.recipient.first_name} {self.recipient.last_name}" if self.recipient else None,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'is_deleted': self.is_deleted
        }

class DiscussionForum(db.Model):
    __tablename__ = 'discussion_forums'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    forum_type = db.Column(db.String(20), default='general')  # general, qa, assignment
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', back_populates='forums')
    creator = db.relationship('User', foreign_keys=[created_by])
    topics = db.relationship('DiscussionTopic', back_populates='forum', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DiscussionForum {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'forum_type': self.forum_type,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'topic_count': len(self.topics)
        }

class DiscussionTopic(db.Model):
    __tablename__ = 'discussion_topics'
    
    id = db.Column(db.Integer, primary_key=True)
    forum_id = db.Column(db.Integer, db.ForeignKey('discussion_forums.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    forum = db.relationship('DiscussionForum', back_populates='topics')
    creator = db.relationship('User', foreign_keys=[created_by])
    posts = db.relationship('DiscussionPost', back_populates='topic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DiscussionTopic {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'forum_id': self.forum_id,
            'title': self.title,
            'content': self.content,
            'is_pinned': self.is_pinned,
            'is_locked': self.is_locked,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'post_count': len(self.posts)
        }

class DiscussionPost(db.Model):
    __tablename__ = 'discussion_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('discussion_topics.id'), nullable=False)
    parent_post_id = db.Column(db.Integer, db.ForeignKey('discussion_posts.id'))
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    topic = db.relationship('DiscussionTopic', back_populates='posts')
    parent_post = db.relationship('DiscussionPost', remote_side=[id], backref='replies')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<DiscussionPost {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'topic_id': self.topic_id,
            'parent_post_id': self.parent_post_id,
            'content': self.content,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ProjectGroup(db.Model):
    __tablename__ = 'project_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    group_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    max_members = db.Column(db.Integer, default=5)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course')
    creator = db.relationship('User', foreign_keys=[created_by])
    members = db.relationship('GroupMember', back_populates='group', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ProjectGroup {self.group_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'group_name': self.group_name,
            'description': self.description,
            'max_members': self.max_members,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'current_members': len(self.members),
            'members': [member.to_dict() for member in self.members]
        }

class GroupMember(db.Model):
    __tablename__ = 'group_members'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('project_groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # leader, member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group = db.relationship('ProjectGroup', back_populates='members')
    user = db.relationship('User')
    
    __table_args__ = (db.UniqueConstraint('group_id', 'user_id'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name}" if self.user else None,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None
        }

