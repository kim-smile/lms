/* ===========================================================================
   LMS DB 초기화 스크립트
   - MySQL/MariaDB + InnoDB + utf8mb4_general_ci
   - 테이블 드랍 → 재생성 → 샘플데이터 삽입
   - 모든 FK 컬럼: INT UNSIGNED  (users.id 등과 일치)
   =========================================================================== */

-- 0) 데이터베이스
CREATE DATABASE IF NOT EXISTS lms_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;
USE lms_db;

-- 1) 기존 테이블 정리
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS
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
  users;
SET FOREIGN_KEY_CHECKS = 1;

-- 2) 핵심 테이블 ------------------------------------------------------------

CREATE TABLE users (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name       VARCHAR(100) NOT NULL,
  email      VARCHAR(190) NOT NULL,
  role       VARCHAR(20)  NOT NULL DEFAULT 'student',   -- student|instructor|admin
  username   VARCHAR(50)  NULL,
  phone      VARCHAR(30)  NULL,
  is_active  TINYINT(1)   NOT NULL DEFAULT 1,
  created_at DATETIME     DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE courses (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title      VARCHAR(200) NOT NULL,
  start_date DATE NULL,
  end_date   DATE NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE enrollments (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    INT UNSIGNED NOT NULL,
  course_id  INT UNSIGNED NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_enroll_user (user_id),
  KEY idx_enroll_course (course_id),
  CONSTRAINT fk_enroll_user   FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE CASCADE,
  CONSTRAINT fk_enroll_course FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE assignments (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  course_id   INT UNSIGNED NOT NULL,
  title       VARCHAR(200) NOT NULL,
  due_at      DATETIME NULL,
  total_score INT DEFAULT 100,
  PRIMARY KEY (id),
  KEY idx_assign_course (course_id),
  CONSTRAINT fk_assign_course FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE submissions (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  assignment_id INT UNSIGNED NOT NULL,
  user_id       INT UNSIGNED NOT NULL,
  score         INT NULL,
  submitted_at  DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_sub_assign (assignment_id),
  KEY idx_sub_user   (user_id),
  CONSTRAINT fk_sub_assign FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
  CONSTRAINT fk_sub_user   FOREIGN KEY (user_id)       REFERENCES users(id)       ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3) 멘토링/프로젝트/공모전 -------------------------------------------------

CREATE TABLE mentoring_teams (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name          VARCHAR(120) NOT NULL,
  owner_user_id INT UNSIGNED NOT NULL,  -- 팀장
  is_solo       TINYINT(1)   NOT NULL DEFAULT 0,  -- 개인 단독 팀 여부
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_mteam_owner (owner_user_id),
  CONSTRAINT fk_mteam_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE mentoring_team_members (
  id        INT UNSIGNED NOT NULL AUTO_INCREMENT,
  team_id   INT UNSIGNED NOT NULL,
  user_id   INT UNSIGNED NOT NULL,
  role      VARCHAR(40) DEFAULT 'member',  -- member|leader|mentor
  joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_tmem_team (team_id),
  KEY idx_tmem_user (user_id),
  CONSTRAINT fk_tmem_team FOREIGN KEY (team_id) REFERENCES mentoring_teams(id) ON DELETE CASCADE,
  CONSTRAINT fk_tmem_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE mentoring_reports (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  author_user_id INT UNSIGNED NOT NULL,
  team_id        INT UNSIGNED NULL,       -- 개인 보고서 가능
  title          VARCHAR(200) NOT NULL,
  content        TEXT NULL,
  file_url       VARCHAR(255) NULL,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_mrep_author (author_user_id),
  KEY idx_mrep_team   (team_id),
  CONSTRAINT fk_mrep_author FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_mrep_team   FOREIGN KEY (team_id)        REFERENCES mentoring_teams(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE projects (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title           VARCHAR(200) NOT NULL,
  description     TEXT NULL,
  team_id         INT UNSIGNED NULL,      -- 팀 프로젝트(선택)
  owner_user_id   INT UNSIGNED NULL,      -- 개인 프로젝트(선택)
  mentor_user_id  INT UNSIGNED NULL,
  status          VARCHAR(30) DEFAULT 'ongoing',  -- ongoing|done|paused
  github_repo_url VARCHAR(255) NULL,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_proj_team   (team_id),
  KEY idx_proj_owner  (owner_user_id),
  KEY idx_proj_mentor (mentor_user_id),
  CONSTRAINT fk_proj_team   FOREIGN KEY (team_id)        REFERENCES mentoring_teams(id) ON DELETE SET NULL,
  CONSTRAINT fk_proj_owner  FOREIGN KEY (owner_user_id)  REFERENCES users(id)          ON DELETE SET NULL,
  CONSTRAINT fk_proj_mentor FOREIGN KEY (mentor_user_id) REFERENCES users(id)          ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_tasks (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  project_id       INT UNSIGNED NOT NULL,
  title            VARCHAR(200) NOT NULL,
  due_at           DATETIME NULL,
  assignee_user_id INT UNSIGNED NULL,
  status           VARCHAR(20) DEFAULT 'todo',   -- todo|doing|done
  PRIMARY KEY (id),
  KEY idx_pt_project  (project_id),
  KEY idx_pt_assignee (assignee_user_id),
  CONSTRAINT fk_pt_project  FOREIGN KEY (project_id)       REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_pt_assignee FOREIGN KEY (assignee_user_id) REFERENCES users(id)    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE competitions (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title          VARCHAR(200) NOT NULL,
  host           VARCHAR(120) NULL,
  url            VARCHAR(255) NULL,
  apply_deadline DATETIME NULL,
  start_at       DATETIME NULL,
  end_at         DATETIME NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE competition_entries (
  id                 INT UNSIGNED NOT NULL AUTO_INCREMENT,
  competition_id     INT UNSIGNED NOT NULL,
  team_id            INT UNSIGNED NULL,
  applicant_user_id  INT UNSIGNED NULL,   -- 개인 신청자
  project_id         INT UNSIGNED NULL,
  status             VARCHAR(20) DEFAULT 'draft', -- draft|submitted|accepted|rejected
  created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_centry_comp    (competition_id),
  KEY idx_centry_team    (team_id),
  KEY idx_centry_user    (applicant_user_id),
  KEY idx_centry_project (project_id),
  CONSTRAINT fk_centry_comp    FOREIGN KEY (competition_id)    REFERENCES competitions(id)   ON DELETE CASCADE,
  CONSTRAINT fk_centry_team    FOREIGN KEY (team_id)           REFERENCES mentoring_teams(id) ON DELETE SET NULL,
  CONSTRAINT fk_centry_user    FOREIGN KEY (applicant_user_id) REFERENCES users(id)           ON DELETE SET NULL,
  CONSTRAINT fk_centry_project FOREIGN KEY (project_id)        REFERENCES projects(id)        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4) 샘플 데이터 -------------------------------------------------------------

-- 사용자 (DEMO: id=1 보장용으로 가장 먼저 삽입)
INSERT INTO users (name, email, role, username, phone)
VALUES
  ('영이',     'young@example.com', 'student', 'young',  '010-0000-0000'),
  ('김멘토',   'mentor@example.com', 'instructor', 'mentor', NULL),
  ('관리자',   'admin@university.edu', 'admin', 'admin', NULL);

-- 강좌/수강/과제
INSERT INTO courses (title, start_date, end_date) VALUES
  ('웹 프로그래밍',        '2024-12-15', '2025-02-20'),
  ('데이터베이스 시스템',   '2025-01-10', '2025-03-20'),
  ('알고리즘',             '2025-01-12', '2025-03-15');

INSERT INTO enrollments (user_id, course_id) VALUES
  (1,1),(1,2),(1,3);

INSERT INTO assignments (course_id, title, due_at, total_score) VALUES
  (1, '웹 프로그래밍 프로젝트', DATE_ADD(NOW(), INTERVAL  2 DAY), 100),
  (2, '데이터베이스 중간고사', DATE_ADD(NOW(), INTERVAL  5 DAY), 100),
  (3, '알고리즘 과제 #3',     DATE_ADD(NOW(), INTERVAL  7 DAY), 100),
  (1, 'HTML/CSS 퀴즈',        DATE_ADD(NOW(), INTERVAL -1 DAY),  50),
  (2, 'ERD 과제',             DATE_ADD(NOW(), INTERVAL -2 DAY),  50);

INSERT INTO submissions (assignment_id, user_id, score, submitted_at) VALUES
  (1, 1, 95, NOW()),
  (4, 1, 40, DATE_ADD(NOW(), INTERVAL -2 DAY));

-- 멘토링: 팀/멤버
INSERT INTO mentoring_teams (name, owner_user_id, is_solo) VALUES
  ('웹프 A팀', 1, 0),
  ('영이(개인)', 1, 1);

-- 리더로 자동 가입 + 개인팀 가입
INSERT INTO mentoring_team_members (team_id, user_id, role) VALUES
  (1, 1, 'leader'),
  (2, 1, 'leader');

-- 보고서
INSERT INTO mentoring_reports (author_user_id, team_id, title, content)
VALUES
  (1, 1, '주간 보고서 #1', '금주 목표: 프로젝트 기본 구조 잡기');

-- 프로젝트 + 작업
INSERT INTO projects (title, description, team_id, owner_user_id, github_repo_url)
VALUES
  ('웹프 팀 프로젝트', '프런트/백엔드 기초', 1, NULL, 'https://github.com/example/webproj'),
  ('개인 미니 앱', 'Flask로 간단한 앱', NULL, 1, NULL);

INSERT INTO project_tasks (project_id, title, due_at, assignee_user_id, status)
VALUES
  (1, 'UI 목업 만들기', DATE_ADD(NOW(), INTERVAL 3 DAY), 1, 'doing'),
  (2, '라우팅 구현',    DATE_ADD(NOW(), INTERVAL 2 DAY), 1, 'todo');

-- 공모전 + 신청
INSERT INTO competitions (title, host, url, apply_deadline)
VALUES
  ('캡스톤 경진대회', '공과대학', 'https://contest.example.com', DATE_ADD(NOW(), INTERVAL 30 DAY));

INSERT INTO competition_entries (competition_id, team_id, applicant_user_id, project_id, status)
VALUES
  (1, 1, 1, 1, 'submitted');

-- =========================
-- 메시지 (드롭 후 재생성)
-- =========================
SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS messages;
SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE messages (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  sender_id   INT UNSIGNED NOT NULL,
  receiver_id INT UNSIGNED NOT NULL,
  title VARCHAR(200) NOT NULL,
  body  TEXT NULL,
  read_at   DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_msg_sender (sender_id),
  KEY idx_msg_receiver (receiver_id),
  KEY idx_msg_created (created_at),
  CONSTRAINT fk_msg_sender   FOREIGN KEY (sender_id)   REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_msg_receiver FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 샘플(사용자 id는 앞서 만든 seed에 맞게 조정하세요)
INSERT INTO messages (sender_id, receiver_id, title, body)
VALUES
  (3, 1, '환영합니다', '플랫폼에 오신 것을 환영합니다!'),
  (2, 1, '멘토링 안내', '이번 주 멘토링은 금요일 3시입니다.');

-- =========================
-- 캘린더 일정 (드롭 후 재생성)
-- =========================
SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS calendar_events;
SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE calendar_events (
  id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id    INT UNSIGNED NULL,           -- NULL이면 공개/공용, 값이 있으면 개인 일정
  course_id  INT UNSIGNED NULL,
  title      VARCHAR(200) NOT NULL,
  start_at   DATETIME NOT NULL,
  end_at     DATETIME NULL,
  location   VARCHAR(200) NULL,
  kind       VARCHAR(20)  DEFAULT 'event',   -- event|mentoring|exam|meeting ...
  description TEXT NULL,
  source     VARCHAR(20)  DEFAULT 'manual',  -- manual|system
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_cal_user   (user_id),
  KEY idx_cal_course (course_id),
  KEY idx_cal_start  (start_at),
  CONSTRAINT fk_cal_user   FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE SET NULL,
  CONSTRAINT fk_cal_course FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 샘플 일정
INSERT INTO calendar_events (user_id, title, start_at, end_at, location, kind)
VALUES
  (1, '멘토링 미팅', DATE_ADD(NOW(), INTERVAL 2 DAY),
       DATE_ADD(DATE_ADD(NOW(), INTERVAL 2 DAY), INTERVAL 1 HOUR), 'H-301', 'mentoring');

USE lms_db;

ALTER TABLE submissions
  ADD COLUMN IF NOT EXISTS file_url   VARCHAR(255) NULL AFTER submitted_at,
  ADD COLUMN IF NOT EXISTS comment    TEXT NULL AFTER file_url,
  ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP AFTER comment,
  ADD COLUMN IF NOT EXISTS updated_at DATETIME NULL AFTER created_at,
  ADD COLUMN IF NOT EXISTS graded_at  DATETIME NULL AFTER updated_at;

-- 한 과제당 사용자 1개 제출만 허용
ALTER TABLE submissions
  ADD CONSTRAINT uq_sub_user_assignment UNIQUE KEY (user_id, assignment_id);

/* =========================
   사용자 환경설정 (Settings)
   ========================= */
SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS user_settings;
SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE user_settings (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL UNIQUE,
  language VARCHAR(10)  DEFAULT 'ko',         -- 'ko' | 'en' ...
  theme    VARCHAR(10)  DEFAULT 'light',      -- 'light' | 'dark'
  timezone VARCHAR(50)  DEFAULT 'Asia/Seoul',
  email_notifications TINYINT(1) NOT NULL DEFAULT 1,
  push_notifications  TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  CONSTRAINT fk_user_settings_user FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 끝