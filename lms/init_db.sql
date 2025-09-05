/* ============================================================================
   LMS DB 초기화 스크립트 (MySQL / MariaDB)
   - InnoDB + utf8mb4_general_ci
   - 드랍 → 재생성 → 샘플 데이터 삽입
   - 모든 PK/FK: INT UNSIGNED
   - 로그인 로직 반영: users.password_hash(신규), users.password(레거시)
   ============================================================================ */

-- ----------------------------------------------------------------------------
-- 0) 데이터베이스 / 세션 설정
-- ----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS lms_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;
USE lms_db;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------------------------------------
-- 1) 기존 테이블 정리 (FK 의존 역순 드랍)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS
  calendar_events,
  messages,
  competition_entries,
  competitions,
  project_tasks,
  projects,
  mentoring_reports,
  mentoring_team_members,
  mentoring_teams,
  submissions,
  assignments,
  enrollments,
  courses,
  user_settings,
  users;

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------------------------
-- 2) 핵심 테이블
-- ----------------------------------------------------------------------------
CREATE TABLE users (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name           VARCHAR(100) NOT NULL,
  email          VARCHAR(190) NOT NULL,
  role           VARCHAR(20)  NOT NULL DEFAULT 'student',         -- student|instructor|admin
  username       VARCHAR(50)  NULL,
  phone          VARCHAR(30)  NULL,
  is_active      TINYINT(1)   NOT NULL DEFAULT 1,
  -- 로그인용 컬럼
  password_hash  VARCHAR(255) NULL,                                -- 권장: 해시 저장(Flask에서 생성)
  password       VARCHAR(128) NULL,                                -- 레거시/데모용: 평문 저장(운영 비권장)
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email),
  UNIQUE KEY uq_users_username (username),
  KEY ix_users_role      (role),
  KEY ix_users_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE courses (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title      VARCHAR(200) NOT NULL,
  start_date DATE NULL,
  end_date   DATE NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_courses_start_date (start_date),
  KEY ix_courses_end_date   (end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE enrollments (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    INT UNSIGNED NOT NULL,
  course_id  INT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_enroll_user   (user_id),
  KEY idx_enroll_course (course_id),
  CONSTRAINT fk_enroll_user
    FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE CASCADE,
  CONSTRAINT fk_enroll_course
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE assignments (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  course_id   INT UNSIGNED NOT NULL,
  title       VARCHAR(200) NOT NULL,
  due_at      DATETIME NULL,
  total_score INT NOT NULL DEFAULT 100,
  PRIMARY KEY (id),
  KEY idx_assign_course (course_id),
  KEY ix_assignments_due (due_at),
  CONSTRAINT fk_assign_course
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE submissions (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  assignment_id INT UNSIGNED NOT NULL,
  user_id       INT UNSIGNED NOT NULL,
  score         INT NULL,
  submitted_at  DATETIME NULL,
  -- 첨부/메타
  file_url      VARCHAR(255) NULL,
  comment       TEXT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NULL,
  graded_at     DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_sub_user_assignment (user_id, assignment_id),   -- 한 과제당 사용자 1개 제출
  KEY idx_sub_assign      (assignment_id),
  KEY idx_sub_user        (user_id),
  KEY ix_submissions_submitted_at (submitted_at),
  CONSTRAINT fk_sub_assign
    FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
  CONSTRAINT fk_sub_user
    FOREIGN KEY (user_id)       REFERENCES users(id)       ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------------------------------------------------------
-- 3) 멘토링 / 프로젝트 / 공모전
-- ----------------------------------------------------------------------------
CREATE TABLE mentoring_teams (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name          VARCHAR(120) NOT NULL,
  owner_user_id INT UNSIGNED NOT NULL,               -- 팀장
  is_solo       TINYINT(1)   NOT NULL DEFAULT 0,     -- 개인 단독 팀 여부
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_mteam_owner (owner_user_id),
  CONSTRAINT fk_mteam_owner
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE mentoring_team_members (
  id        INT UNSIGNED NOT NULL AUTO_INCREMENT,
  team_id   INT UNSIGNED NOT NULL,
  user_id   INT UNSIGNED NOT NULL,
  role      VARCHAR(40) DEFAULT 'member',            -- member|leader|mentor
  joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_tmem_team (team_id),
  KEY idx_tmem_user (user_id),
  CONSTRAINT fk_tmem_team
    FOREIGN KEY (team_id) REFERENCES mentoring_teams(id) ON DELETE CASCADE,
  CONSTRAINT fk_tmem_user
    FOREIGN KEY (user_id) REFERENCES users(id)        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE mentoring_reports (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  author_user_id INT UNSIGNED NOT NULL,
  team_id        INT UNSIGNED NULL,                  -- 개인 보고서 가능
  title          VARCHAR(200) NOT NULL,
  content        TEXT NULL,
  file_url       VARCHAR(255) NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_mrep_author (author_user_id),
  KEY idx_mrep_team   (team_id),
  CONSTRAINT fk_mrep_author
    FOREIGN KEY (author_user_id) REFERENCES users(id)           ON DELETE CASCADE,
  CONSTRAINT fk_mrep_team
    FOREIGN KEY (team_id)        REFERENCES mentoring_teams(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE projects (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title           VARCHAR(200) NOT NULL,
  description     TEXT NULL,
  team_id         INT UNSIGNED NULL,                 -- 팀 프로젝트(선택)
  owner_user_id   INT UNSIGNED NULL,                 -- 개인 프로젝트(선택)
  mentor_user_id  INT UNSIGNED NULL,
  status          VARCHAR(30) DEFAULT 'ongoing',     -- ongoing|done|paused
  github_repo_url VARCHAR(255) NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_proj_team   (team_id),
  KEY idx_proj_owner  (owner_user_id),
  KEY idx_proj_mentor (mentor_user_id),
  KEY ix_projects_status (status),
  CONSTRAINT fk_proj_team
    FOREIGN KEY (team_id)        REFERENCES mentoring_teams(id) ON DELETE SET NULL,
  CONSTRAINT fk_proj_owner
    FOREIGN KEY (owner_user_id)  REFERENCES users(id)           ON DELETE SET NULL,
  CONSTRAINT fk_proj_mentor
    FOREIGN KEY (mentor_user_id) REFERENCES users(id)           ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE project_tasks (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  project_id       INT UNSIGNED NOT NULL,
  title            VARCHAR(200) NOT NULL,
  due_at           DATETIME NULL,
  assignee_user_id INT UNSIGNED NULL,
  status           VARCHAR(20) DEFAULT 'todo',       -- todo|doing|done
  PRIMARY KEY (id),
  KEY idx_pt_project    (project_id),
  KEY idx_pt_assignee   (assignee_user_id),
  KEY ix_ptasks_due     (due_at),
  KEY ix_ptasks_status  (status),
  CONSTRAINT fk_pt_project
    FOREIGN KEY (project_id)       REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_pt_assignee
    FOREIGN KEY (assignee_user_id) REFERENCES users(id)    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE competitions (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title          VARCHAR(200) NOT NULL,
  host           VARCHAR(120) NULL,
  url            VARCHAR(255) NULL,
  apply_deadline DATETIME NULL,
  start_at       DATETIME NULL,
  end_at         DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_competitions_deadline (apply_deadline),
  KEY ix_competitions_start    (start_at),
  KEY ix_competitions_end      (end_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE competition_entries (
  id                 INT UNSIGNED NOT NULL AUTO_INCREMENT,
  competition_id     INT UNSIGNED NOT NULL,
  team_id            INT UNSIGNED NULL,
  applicant_user_id  INT UNSIGNED NULL,             -- 개인 신청자
  project_id         INT UNSIGNED NULL,
  status             VARCHAR(20) DEFAULT 'draft',   -- draft|submitted|accepted|rejected
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_centry_comp    (competition_id),
  KEY idx_centry_team    (team_id),
  KEY idx_centry_user    (applicant_user_id),
  KEY idx_centry_project (project_id),
  KEY ix_centries_status (status),
  CONSTRAINT fk_centry_comp
    FOREIGN KEY (competition_id)    REFERENCES competitions(id)    ON DELETE CASCADE,
  CONSTRAINT fk_centry_team
    FOREIGN KEY (team_id)           REFERENCES mentoring_teams(id) ON DELETE SET NULL,
  CONSTRAINT fk_centry_user
    FOREIGN KEY (applicant_user_id) REFERENCES users(id)           ON DELETE SET NULL,
  CONSTRAINT fk_centry_project
    FOREIGN KEY (project_id)        REFERENCES projects(id)        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------------------------------------------------------
-- 4) 메시지 / 캘린더 / 사용자 설정
-- ----------------------------------------------------------------------------
CREATE TABLE messages (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  sender_id   INT UNSIGNED NOT NULL,
  receiver_id INT UNSIGNED NOT NULL,
  title       VARCHAR(200) NOT NULL,
  body        TEXT NULL,
  read_at     DATETIME NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_msg_sender   (sender_id),
  KEY idx_msg_receiver (receiver_id),
  KEY idx_msg_created  (created_at),
  KEY ix_messages_read_at (read_at),
  CONSTRAINT fk_msg_sender
    FOREIGN KEY (sender_id)   REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_msg_receiver
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE calendar_events (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    INT UNSIGNED NULL,                     -- NULL=공용, 값=개인
  course_id  INT UNSIGNED NULL,
  title      VARCHAR(200) NOT NULL,
  start_at   DATETIME NOT NULL,
  end_at     DATETIME NULL,
  location   VARCHAR(200) NULL,
  kind       VARCHAR(20)  NOT NULL DEFAULT 'event', -- event|mentoring|exam|meeting...
  description TEXT NULL,
  source     VARCHAR(20)  NOT NULL DEFAULT 'manual',-- manual|system
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_cal_user   (user_id),
  KEY idx_cal_course (course_id),
  KEY idx_cal_start  (start_at),
  KEY ix_cevents_kind (kind),
  CONSTRAINT fk_cal_user
    FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE SET NULL,
  CONSTRAINT fk_cal_course
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE user_settings (
  id                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id             INT UNSIGNED NOT NULL UNIQUE,
  language            VARCHAR(10)  NOT NULL DEFAULT 'ko',      -- 'ko' | 'en' ...
  theme               VARCHAR(10)  NOT NULL DEFAULT 'light',   -- 'light' | 'dark'
  timezone            VARCHAR(50)  NOT NULL DEFAULT 'Asia/Seoul',
  email_notifications TINYINT(1)   NOT NULL DEFAULT 1,
  push_notifications  TINYINT(1)   NOT NULL DEFAULT 0,
  created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_usersettings_user (user_id),
  CONSTRAINT fk_user_settings_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------------------------------------------------------
-- 5) 샘플 데이터 (로그인 데모 계정 3개 + 강좌/과제 등)
-- ----------------------------------------------------------------------------
-- 데모 사용자(순서 중요: id=1이 학생)
INSERT INTO users (name, email, role, username, phone, password) VALUES
  ('홍학생', 'student@example.com',   'student',    'student',  '010-0000-0001', 'student123'),
  ('김교수', 'prof@example.com',      'instructor', 'prof',     '010-0000-0002', 'prof123'),
  ('관리자', 'admin@example.com',     'admin',      'admin',    '010-0000-0003', 'admin123');

-- 강좌
INSERT INTO courses (title, start_date, end_date) VALUES
  ('웹 프로그래밍',        '2024-12-15', '2025-02-20'),
  ('데이터베이스 시스템',   '2025-01-10', '2025-03-20'),
  ('알고리즘',             '2025-01-12', '2025-03-15');

-- 수강(학생 id=1 등록)
INSERT INTO enrollments (user_id, course_id) VALUES
  (1,1),(1,2),(1,3);

-- 과제
INSERT INTO assignments (course_id, title, due_at, total_score) VALUES
  (1, '웹 프로그래밍 프로젝트', DATE_ADD(NOW(), INTERVAL  2 DAY), 100),
  (2, '데이터베이스 중간고사', DATE_ADD(NOW(), INTERVAL  5 DAY), 100),
  (3, '알고리즘 과제 #3',     DATE_ADD(NOW(), INTERVAL  7 DAY), 100),
  (1, 'HTML/CSS 퀴즈',        DATE_ADD(NOW(), INTERVAL -1 DAY),  50),
  (2, 'ERD 과제',             DATE_ADD(NOW(), INTERVAL -2 DAY),  50);

-- 제출(예시)
INSERT INTO submissions (assignment_id, user_id, score, submitted_at)
VALUES
  (1, 1, 95, NOW()),
  (4, 1, 40, DATE_ADD(NOW(), INTERVAL -2 DAY));

-- 멘토링: 팀/멤버
INSERT INTO mentoring_teams (name, owner_user_id, is_solo) VALUES
  ('웹프 A팀',   1, 0),
  ('홍학생(개인)', 1, 1);

INSERT INTO mentoring_team_members (team_id, user_id, role) VALUES
  (1, 1, 'leader'),
  (2, 1, 'leader');

-- 보고서
INSERT INTO mentoring_reports (author_user_id, team_id, title, content) VALUES
  (1, 1, '주간 보고서 #1', '금주 목표: 프로젝트 기본 구조 잡기');

-- 프로젝트 + 작업
INSERT INTO projects (title, description, team_id, owner_user_id, github_repo_url) VALUES
  ('웹프 팀 프로젝트', '프런트/백엔드 기초', 1, NULL, 'https://github.com/example/webproj'),
  ('개인 미니 앱',     'Flask로 간단한 앱',  NULL, 1,   NULL);

INSERT INTO project_tasks (project_id, title, due_at, assignee_user_id, status) VALUES
  (1, 'UI 목업 만들기', DATE_ADD(NOW(), INTERVAL 3 DAY), 1, 'doing'),
  (2, '라우팅 구현',    DATE_ADD(NOW(), INTERVAL 2 DAY), 1, 'todo');

-- 공모전 + 신청
INSERT INTO competitions (title, host, url, apply_deadline) VALUES
  ('캡스톤 경진대회', '공과대학', 'https://contest.example.com', DATE_ADD(NOW(), INTERVAL 30 DAY));

INSERT INTO competition_entries (competition_id, team_id, applicant_user_id, project_id, status) VALUES
  (1, 1, 1, 1, 'submitted');

-- 메시지(관리자/교수 → 학생)
INSERT INTO messages (sender_id, receiver_id, title, body) VALUES
  (3, 1, '환영합니다', '플랫폼에 오신 것을 환영합니다!'),
  (2, 1, '멘토링 안내', '이번 주 멘토링은 금요일 3시입니다.');

-- 캘린더
INSERT INTO calendar_events (user_id, title, start_at, end_at, location, kind) VALUES
  (1, '멘토링 미팅',
      DATE_ADD(NOW(), INTERVAL 2 DAY),
      DATE_ADD(DATE_ADD(NOW(), INTERVAL 2 DAY), INTERVAL 1 HOUR),
      'H-301', 'mentoring');

-- 사용자 설정(옵션)
INSERT INTO user_settings (user_id, language, theme, timezone)
VALUES (1, 'ko', 'light', 'Asia/Seoul')
ON DUPLICATE KEY UPDATE user_id = user_id;

-- ----------------------------------------------------------------------------
-- 끝
-- ----------------------------------------------------------------------------