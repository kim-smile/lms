# LMS 데이터베이스 스키마 설계

## 1. 개요

본 문서는 LMS(Learning Management System)의 데이터베이스 스키마를 설계하고 정의한다. PostgreSQL을 기반으로 하며, 사용자 관리, 강좌 관리, 학습 콘텐츠 관리, 평가 시스템, 소통 기능, 리포팅 등의 기능을 지원하는 데이터 구조를 제공한다.

## 2. 데이터베이스 설계 원칙

- **정규화**: 데이터 중복을 최소화하고 무결성을 보장하기 위해 3NF(Third Normal Form)까지 정규화를 적용한다.
- **확장성**: 향후 기능 확장을 고려하여 유연한 구조로 설계한다.
- **성능**: 자주 사용되는 쿼리를 고려하여 적절한 인덱스를 설계한다.
- **보안**: 민감한 정보는 암호화하여 저장하고, 접근 권한을 제어한다.

## 3. 주요 엔티티 및 관계

### 3.1. 사용자 관리 (User Management)

#### Users 테이블
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    profile_image_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(32)
);
```

#### Roles 테이블
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기본 역할 데이터
INSERT INTO roles (name, description) VALUES 
('student', '학생'),
('instructor', '교수'),
('teaching_assistant', '조교'),
('admin', '관리자');
```

#### User_Roles 테이블 (다대다 관계)
```sql
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER REFERENCES users(id),
    UNIQUE(user_id, role_id)
);
```

#### Permissions 테이블
```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL
);
```

#### Role_Permissions 테이블
```sql
CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);
```

### 3.2. 강좌 관리 (Course Management)

#### Courses 테이블
```sql
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    course_code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    credits INTEGER DEFAULT 3,
    max_students INTEGER,
    instructor_id INTEGER REFERENCES users(id),
    semester VARCHAR(20) NOT NULL,
    year INTEGER NOT NULL,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Course_Sections 테이블 (분반 관리)
```sql
CREATE TABLE course_sections (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    section_number VARCHAR(10) NOT NULL,
    instructor_id INTEGER REFERENCES users(id),
    max_students INTEGER,
    schedule_days VARCHAR(20), -- 'MON,WED,FRI'
    schedule_time_start TIME,
    schedule_time_end TIME,
    classroom VARCHAR(50),
    UNIQUE(course_id, section_number)
);
```

#### Course_Enrollments 테이블
```sql
CREATE TABLE course_enrollments (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES course_sections(id),
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'enrolled', -- enrolled, dropped, completed
    final_grade VARCHAR(5),
    UNIQUE(course_id, student_id)
);
```

#### Course_Materials 테이블 (교재 정보)
```sql
CREATE TABLE course_materials (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(100),
    publisher VARCHAR(100),
    isbn VARCHAR(20),
    material_type VARCHAR(20) DEFAULT 'textbook', -- textbook, reference, online
    is_required BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Course_Syllabus 테이블 (강의계획서)
```sql
CREATE TABLE course_syllabus (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);
```

### 3.3. 학습 콘텐츠 관리 (Content Management)

#### Content_Categories 테이블
```sql
CREATE TABLE content_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES content_categories(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Course_Contents 테이블
```sql
CREATE TABLE course_contents (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    content_type VARCHAR(50) NOT NULL, -- video, pdf, ppt, scorm, xapi, link
    file_path VARCHAR(500),
    file_size INTEGER,
    duration INTEGER, -- 동영상 길이 (초)
    category_id INTEGER REFERENCES content_categories(id),
    week_number INTEGER,
    lesson_order INTEGER,
    is_published BOOLEAN DEFAULT FALSE,
    access_start_date TIMESTAMP,
    access_end_date TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);
```

#### Content_Versions 테이블 (버전 관리)
```sql
CREATE TABLE content_versions (
    id SERIAL PRIMARY KEY,
    content_id INTEGER REFERENCES course_contents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    file_path VARCHAR(500),
    file_size INTEGER,
    change_description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(content_id, version_number)
);
```

#### Content_Access_Logs 테이블 (접근 로그)
```sql
CREATE TABLE content_access_logs (
    id SERIAL PRIMARY KEY,
    content_id INTEGER REFERENCES course_contents(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER,
    completion_percentage DECIMAL(5,2) DEFAULT 0.00,
    device_type VARCHAR(20), -- desktop, mobile, tablet
    ip_address INET
);
```

### 3.4. 학습 진도 및 활동 관리 (Progress & Activity Management)

#### User_Progress 테이블
```sql
CREATE TABLE user_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    content_id INTEGER REFERENCES course_contents(id) ON DELETE CASCADE,
    progress_percentage DECIMAL(5,2) DEFAULT 0.00,
    completion_status VARCHAR(20) DEFAULT 'not_started', -- not_started, in_progress, completed
    first_accessed_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    total_time_spent INTEGER DEFAULT 0, -- 총 학습 시간 (초)
    UNIQUE(user_id, content_id)
);
```

#### Attendance 테이블
```sql
CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES course_sections(id),
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    attendance_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'present', -- present, absent, late, excused
    attendance_type VARCHAR(20) DEFAULT 'manual', -- manual, code, time_based, activity_based
    attendance_code VARCHAR(10),
    recorded_by INTEGER REFERENCES users(id),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(course_id, student_id, attendance_date)
);
```

#### Learning_Activities 테이블
```sql
CREATE TABLE learning_activities (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    activity_type VARCHAR(50) NOT NULL, -- assignment, quiz, discussion, project
    due_date TIMESTAMP,
    max_points DECIMAL(8,2) DEFAULT 0.00,
    is_published BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Activity_Submissions 테이블
```sql
CREATE TABLE activity_submissions (
    id SERIAL PRIMARY KEY,
    activity_id INTEGER REFERENCES learning_activities(id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    submission_text TEXT,
    file_path VARCHAR(500),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'submitted', -- submitted, graded, returned
    score DECIMAL(8,2),
    feedback TEXT,
    graded_by INTEGER REFERENCES users(id),
    graded_at TIMESTAMP,
    UNIQUE(activity_id, student_id)
);
```

### 3.5. 평가 및 성적 관리 (Assessment & Grading)

#### Question_Banks 테이블
```sql
CREATE TABLE question_banks (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Questions 테이블
```sql
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    bank_id INTEGER REFERENCES question_banks(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) NOT NULL, -- multiple_choice, true_false, short_answer, essay
    points DECIMAL(8,2) DEFAULT 1.00,
    difficulty_level VARCHAR(20) DEFAULT 'medium', -- easy, medium, hard
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Question_Options 테이블 (객관식 선택지)
```sql
CREATE TABLE question_options (
    id SERIAL PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    option_order INTEGER
);
```

#### Quizzes 테이블
```sql
CREATE TABLE quizzes (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    time_limit INTEGER, -- 제한 시간 (분)
    max_attempts INTEGER DEFAULT 1,
    available_from TIMESTAMP,
    available_until TIMESTAMP,
    is_published BOOLEAN DEFAULT FALSE,
    shuffle_questions BOOLEAN DEFAULT FALSE,
    show_correct_answers BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Quiz_Questions 테이블
```sql
CREATE TABLE quiz_questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    question_order INTEGER,
    points DECIMAL(8,2) DEFAULT 1.00
);
```

#### Quiz_Attempts 테이블
```sql
CREATE TABLE quiz_attempts (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    attempt_number INTEGER DEFAULT 1,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    score DECIMAL(8,2),
    max_score DECIMAL(8,2),
    time_taken INTEGER, -- 소요 시간 (초)
    status VARCHAR(20) DEFAULT 'in_progress' -- in_progress, submitted, graded
);
```

#### Quiz_Responses 테이블
```sql
CREATE TABLE quiz_responses (
    id SERIAL PRIMARY KEY,
    attempt_id INTEGER REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    response_text TEXT,
    selected_option_id INTEGER REFERENCES question_options(id),
    is_correct BOOLEAN,
    points_earned DECIMAL(8,2) DEFAULT 0.00
);
```

#### Rubrics 테이블
```sql
CREATE TABLE rubrics (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    total_points DECIMAL(8,2) DEFAULT 100.00,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Rubric_Criteria 테이블
```sql
CREATE TABLE rubric_criteria (
    id SERIAL PRIMARY KEY,
    rubric_id INTEGER REFERENCES rubrics(id) ON DELETE CASCADE,
    criterion_name VARCHAR(100) NOT NULL,
    description TEXT,
    max_points DECIMAL(8,2) NOT NULL,
    criterion_order INTEGER
);
```

#### Rubric_Levels 테이블
```sql
CREATE TABLE rubric_levels (
    id SERIAL PRIMARY KEY,
    criterion_id INTEGER REFERENCES rubric_criteria(id) ON DELETE CASCADE,
    level_name VARCHAR(50) NOT NULL,
    description TEXT,
    points DECIMAL(8,2) NOT NULL,
    level_order INTEGER
);
```

### 3.6. 소통 및 협업 (Communication & Collaboration)

#### Announcements 테이블
```sql
CREATE TABLE announcements (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    is_published BOOLEAN DEFAULT FALSE,
    publish_date TIMESTAMP,
    expire_date TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Messages 테이블
```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    subject VARCHAR(200),
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'private', -- private, group
    parent_message_id INTEGER REFERENCES messages(id),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE
);
```

#### Message_Recipients 테이블
```sql
CREATE TABLE message_recipients (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    recipient_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);
```

#### Discussion_Forums 테이블
```sql
CREATE TABLE discussion_forums (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    forum_type VARCHAR(20) DEFAULT 'general', -- general, qa, assignment
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Discussion_Topics 테이블
```sql
CREATE TABLE discussion_topics (
    id SERIAL PRIMARY KEY,
    forum_id INTEGER REFERENCES discussion_forums(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    is_pinned BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Discussion_Posts 테이블
```sql
CREATE TABLE discussion_posts (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER REFERENCES discussion_topics(id) ON DELETE CASCADE,
    parent_post_id INTEGER REFERENCES discussion_posts(id),
    content TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Project_Groups 테이블
```sql
CREATE TABLE project_groups (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    group_name VARCHAR(100) NOT NULL,
    description TEXT,
    max_members INTEGER DEFAULT 5,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Group_Members 테이블
```sql
CREATE TABLE group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES project_groups(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member', -- leader, member
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, user_id)
);
```

### 3.7. 리포팅 및 분석 (Reporting & Analytics)

#### Learning_Analytics 테이블
```sql
CREATE TABLE learning_analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,2),
    metric_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### System_Logs 테이블
```sql
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);
```

#### Risk_Alerts 테이블 (위험군 경고)
```sql
CREATE TABLE risk_alerts (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL, -- low_progress, low_attendance, low_grades
    severity VARCHAR(20) DEFAULT 'medium', -- low, medium, high
    description TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by INTEGER REFERENCES users(id)
);
```

## 4. 인덱스 설계

성능 최적화를 위한 주요 인덱스:

```sql
-- 사용자 관련 인덱스
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);

-- 강좌 관련 인덱스
CREATE INDEX idx_courses_instructor_id ON courses(instructor_id);
CREATE INDEX idx_course_enrollments_student_id ON course_enrollments(student_id);
CREATE INDEX idx_course_enrollments_course_id ON course_enrollments(course_id);

-- 콘텐츠 관련 인덱스
CREATE INDEX idx_course_contents_course_id ON course_contents(course_id);
CREATE INDEX idx_content_access_logs_user_id ON content_access_logs(user_id);
CREATE INDEX idx_content_access_logs_content_id ON content_access_logs(content_id);

-- 진도 관련 인덱스
CREATE INDEX idx_user_progress_user_id ON user_progress(user_id);
CREATE INDEX idx_user_progress_course_id ON user_progress(course_id);
CREATE INDEX idx_attendance_student_id ON attendance(student_id);
CREATE INDEX idx_attendance_course_id ON attendance(course_id);

-- 평가 관련 인덱스
CREATE INDEX idx_quiz_attempts_student_id ON quiz_attempts(student_id);
CREATE INDEX idx_quiz_attempts_quiz_id ON quiz_attempts(quiz_id);

-- 소통 관련 인덱스
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_message_recipients_recipient_id ON message_recipients(recipient_id);
CREATE INDEX idx_discussion_posts_topic_id ON discussion_posts(topic_id);

-- 로그 관련 인덱스
CREATE INDEX idx_system_logs_user_id ON system_logs(user_id);
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
```

## 5. 데이터 무결성 제약조건

```sql
-- 사용자 이메일 형식 검증
ALTER TABLE users ADD CONSTRAINT check_email_format 
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- 강좌 날짜 검증
ALTER TABLE courses ADD CONSTRAINT check_course_dates 
CHECK (start_date <= end_date);

-- 퀴즈 점수 범위 검증
ALTER TABLE quiz_attempts ADD CONSTRAINT check_score_range 
CHECK (score >= 0 AND score <= max_score);

-- 진도율 범위 검증
ALTER TABLE user_progress ADD CONSTRAINT check_progress_range 
CHECK (progress_percentage >= 0 AND progress_percentage <= 100);
```

## 6. 보안 고려사항

- **비밀번호 해싱**: bcrypt 또는 Argon2를 사용하여 비밀번호를 해싱하여 저장
- **개인정보 암호화**: 민감한 개인정보는 AES-256 암호화 적용
- **접근 로그**: 모든 데이터 접근 및 수정 작업에 대한 로그 기록
- **데이터 백업**: 정기적인 데이터 백업 및 복구 전략 수립
- **SQL 인젝션 방지**: 매개변수화된 쿼리 사용

## 7. 확장성 고려사항

- **파티셔닝**: 대용량 테이블(로그, 분석 데이터)에 대한 파티셔닝 전략
- **읽기 전용 복제본**: 리포팅 및 분석 쿼리를 위한 읽기 전용 데이터베이스 복제본
- **캐싱**: Redis를 활용한 자주 조회되는 데이터 캐싱
- **아카이빙**: 오래된 데이터의 아카이빙 정책 수립

이 데이터베이스 스키마는 LMS의 모든 핵심 기능을 지원하며, 확장성과 성능을 고려하여 설계되었다. 실제 구현 시에는 비즈니스 요구사항에 따라 세부 조정이 필요할 수 있다.

