from src.models.user import db
from datetime import datetime

class QuestionBank(db.Model):
    __tablename__ = 'question_banks'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course')
    creator = db.relationship('User', foreign_keys=[created_by])
    questions = db.relationship('Question', back_populates='bank', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'question_count': len(self.questions)
        }

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey('question_banks.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # multiple_choice, true_false, short_answer, essay
    points = db.Column(db.Numeric(8, 2), default=1.00)
    difficulty_level = db.Column(db.String(20), default='medium')  # easy, medium, hard
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bank = db.relationship('QuestionBank', back_populates='questions')
    creator = db.relationship('User', foreign_keys=[created_by])
    options = db.relationship('QuestionOption', back_populates='question', cascade='all, delete-orphan')
    quiz_questions = db.relationship('QuizQuestion', back_populates='question', cascade='all, delete-orphan')
    responses = db.relationship('QuizResponse', back_populates='question', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'bank_id': self.bank_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'points': float(self.points) if self.points else 1.0,
            'difficulty_level': self.difficulty_level,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'options': [option.to_dict() for option in self.options]
        }

class QuestionOption(db.Model):
    __tablename__ = 'question_options'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    option_order = db.Column(db.Integer)
    
    # Relationships
    question = db.relationship('Question', back_populates='options')
    responses = db.relationship('QuizResponse', back_populates='selected_option')
    
    def to_dict(self):
        return {
            'id': self.id,
            'question_id': self.question_id,
            'option_text': self.option_text,
            'is_correct': self.is_correct,
            'option_order': self.option_order
        }

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    time_limit = db.Column(db.Integer)  # 제한 시간 (분)
    max_attempts = db.Column(db.Integer, default=1)
    available_from = db.Column(db.DateTime)
    available_until = db.Column(db.DateTime)
    is_published = db.Column(db.Boolean, default=False)
    shuffle_questions = db.Column(db.Boolean, default=False)
    show_correct_answers = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course')
    creator = db.relationship('User', foreign_keys=[created_by])
    quiz_questions = db.relationship('QuizQuestion', back_populates='quiz', cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', back_populates='quiz', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'time_limit': self.time_limit,
            'max_attempts': self.max_attempts,
            'available_from': self.available_from.isoformat() if self.available_from else None,
            'available_until': self.available_until.isoformat() if self.available_until else None,
            'is_published': self.is_published,
            'shuffle_questions': self.shuffle_questions,
            'show_correct_answers': self.show_correct_answers,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'question_count': len(self.quiz_questions)
        }

class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    question_order = db.Column(db.Integer)
    points = db.Column(db.Numeric(8, 2), default=1.00)
    
    # Relationships
    quiz = db.relationship('Quiz', back_populates='quiz_questions')
    question = db.relationship('Question', back_populates='quiz_questions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question_id': self.question_id,
            'question_order': self.question_order,
            'points': float(self.points) if self.points else 1.0,
            'question': self.question.to_dict() if self.question else None
        }

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attempt_number = db.Column(db.Integer, default=1)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    score = db.Column(db.Numeric(8, 2))
    max_score = db.Column(db.Numeric(8, 2))
    time_taken = db.Column(db.Integer)  # 소요 시간 (초)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, submitted, graded
    
    # Relationships
    quiz = db.relationship('Quiz', back_populates='attempts')
    student = db.relationship('User', foreign_keys=[student_id])
    responses = db.relationship('QuizResponse', back_populates='attempt', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'student_id': self.student_id,
            'student_name': f"{self.student.first_name} {self.student.last_name}" if self.student else None,
            'attempt_number': self.attempt_number,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'score': float(self.score) if self.score else None,
            'max_score': float(self.max_score) if self.max_score else None,
            'time_taken': self.time_taken,
            'status': self.status
        }

class QuizResponse(db.Model):
    __tablename__ = 'quiz_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    response_text = db.Column(db.Text)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('question_options.id'))
    is_correct = db.Column(db.Boolean)
    points_earned = db.Column(db.Numeric(8, 2), default=0.00)
    
    # Relationships
    attempt = db.relationship('QuizAttempt', back_populates='responses')
    question = db.relationship('Question', back_populates='responses')
    selected_option = db.relationship('QuestionOption', back_populates='responses')
    
    def to_dict(self):
        return {
            'id': self.id,
            'attempt_id': self.attempt_id,
            'question_id': self.question_id,
            'response_text': self.response_text,
            'selected_option_id': self.selected_option_id,
            'is_correct': self.is_correct,
            'points_earned': float(self.points_earned) if self.points_earned else 0.0
        }

class Rubric(db.Model):
    __tablename__ = 'rubrics'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    total_points = db.Column(db.Numeric(8, 2), default=100.00)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course')
    creator = db.relationship('User', foreign_keys=[created_by])
    criteria = db.relationship('RubricCriterion', back_populates='rubric', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'total_points': float(self.total_points) if self.total_points else 100.0,
            'created_by': self.created_by,
            'creator_name': f"{self.creator.first_name} {self.creator.last_name}" if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'criteria': [criterion.to_dict() for criterion in self.criteria]
        }

class RubricCriterion(db.Model):
    __tablename__ = 'rubric_criteria'
    
    id = db.Column(db.Integer, primary_key=True)
    rubric_id = db.Column(db.Integer, db.ForeignKey('rubrics.id'), nullable=False)
    criterion_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    max_points = db.Column(db.Numeric(8, 2), nullable=False)
    criterion_order = db.Column(db.Integer)
    
    # Relationships
    rubric = db.relationship('Rubric', back_populates='criteria')
    levels = db.relationship('RubricLevel', back_populates='criterion', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'rubric_id': self.rubric_id,
            'criterion_name': self.criterion_name,
            'description': self.description,
            'max_points': float(self.max_points) if self.max_points else 0.0,
            'criterion_order': self.criterion_order,
            'levels': [level.to_dict() for level in self.levels]
        }

class RubricLevel(db.Model):
    __tablename__ = 'rubric_levels'
    
    id = db.Column(db.Integer, primary_key=True)
    criterion_id = db.Column(db.Integer, db.ForeignKey('rubric_criteria.id'), nullable=False)
    level_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    points = db.Column(db.Numeric(8, 2), nullable=False)
    level_order = db.Column(db.Integer)
    
    # Relationships
    criterion = db.relationship('RubricCriterion', back_populates='levels')
    
    def to_dict(self):
        return {
            'id': self.id,
            'criterion_id': self.criterion_id,
            'level_name': self.level_name,
            'description': self.description,
            'points': float(self.points) if self.points else 0.0,
            'level_order': self.level_order
        }

