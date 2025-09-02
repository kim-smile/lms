from src.models.db import db
from src.models.user import User
from src.models.role import Role
from src.models.user_role import UserRole
from src.models.permission import Permission

from src.models.course import Course, CourseSection, CourseEnrollment, CourseMaterial, CourseSyllabus
from src.models.content import ContentCategory, CourseContent, ContentVersion, ContentAccessLog
from src.models.progress import UserProgress, Attendance, LearningActivity, ActivitySubmission
from src.models.assessment import (
    QuestionBank, Question, QuestionOption, Quiz, QuizQuestion, 
    QuizAttempt, QuizResponse, Rubric, RubricCriterion, RubricLevel
)
from src.models.communication import (
    Announcement, Message, MessageRecipient, DiscussionForum, 
    DiscussionTopic, DiscussionPost, ProjectGroup, GroupMember
)
from src.models.analytics import (
    LearningAnalytics, SystemLog, RiskAlert, CourseStatistics, UserStatistics
)

__all__ = [
    'db',
    # User models
    'User', 'Role', 'UserRole', 'Permission',
    # Course models
    'Course', 'CourseSection', 'CourseEnrollment', 'CourseMaterial', 'CourseSyllabus',
    # Content models
    'ContentCategory', 'CourseContent', 'ContentVersion', 'ContentAccessLog',
    # Progress models
    'UserProgress', 'Attendance', 'LearningActivity', 'ActivitySubmission',
    # Assessment models
    'QuestionBank', 'Question', 'QuestionOption', 'Quiz', 'QuizQuestion',
    'QuizAttempt', 'QuizResponse', 'Rubric', 'RubricCriterion', 'RubricLevel',
    # Communication models
    'Announcement', 'Message', 'MessageRecipient', 'DiscussionForum',
    'DiscussionTopic', 'DiscussionPost', 'ProjectGroup', 'GroupMember',
    # Analytics models
    'LearningAnalytics', 'SystemLog', 'RiskAlert', 'CourseStatistics', 'UserStatistics'
]


