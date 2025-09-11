/* ============================================================================
   LMS DB 초기화 (정돈 버전)
   - 포함: Users, UserSettings, Courses, Enrollments, Assignments, Submissions,
           Materials(course_materials/materials/material_events/material_blobs),
           Notices/notice_attachments, Discussions(threads/comments/likes),
           Mentoring(teams/members/reports), Projects/Tasks/TaskFiles,
           Competitions/Entries, Boards/Posts/Attachments, Messages
   - 제외: calendar_events
   - 제출 규칙: 파일 업로드가 있어야 제출 처리, 제출 후에만 점수 저장 (트리거)
============================================================================ */

-- 0) 데이터베이스 및 세션 설정
CREATE DATABASE IF NOT EXISTS lms_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;
USE lms_db;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

/* ============================================================================
-- 1) 드롭(자식 → 부모 순서)
============================================================================ */
DROP TABLE IF EXISTS
  project_task_files,
  project_tasks,
  projects,
  mentoring_reports,
  mentoring_team_members,
  mentoring_teams,
  discussion_comment_likes,
  discussion_comments,
  discussion_threads,
  notice_attachments,
  notices,
  material_events,
  material_blobs,
  materials,
  course_materials,
  competition_entries,
  competitions,
  submissions,
  assignments,
  enrollments,
  posts,
  attachments,
  boards,
  messages,
  user_settings,
  courses,
  users;

SET FOREIGN_KEY_CHECKS = 1;

/* ============================================================================
-- 2) 스키마 생성
============================================================================ */

/* 2-1. Users */
CREATE TABLE users (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name           VARCHAR(100) NOT NULL,
  email          VARCHAR(190) NOT NULL,
  role           VARCHAR(20)  NOT NULL DEFAULT 'student', -- student|instructor|admin|guest
  username       VARCHAR(50)  NULL,
  phone          VARCHAR(30)  NULL,
  student_no     VARCHAR(50)  NULL,                        -- 학번
  school         VARCHAR(120) NULL,                        -- 학교
  github_url     VARCHAR(255) NULL DEFAULT 'https://github.com/kim-smile',
  profile_image  VARCHAR(255) NULL,
  resume_file    VARCHAR(255) NULL,
  is_active      TINYINT(1)   NOT NULL DEFAULT 1,
  department	  VARCHAR(120) NULL,
  password_hash  VARCHAR(255) NULL,
  password       VARCHAR(128) NULL,
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email),
  KEY ix_users_role      (role),
  KEY ix_users_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-2. Courses */
CREATE TABLE courses (
  id                 INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title              VARCHAR(200) NOT NULL,
  description        TEXT NULL,
  start_date         DATE NULL,
  end_date           DATE NULL,
  schedule_text      TEXT NULL,
  credit             TINYINT UNSIGNED NULL DEFAULT 0,
  instructor_user_id INT UNSIGNED NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_courses_start_date (start_date),
  KEY ix_courses_end_date   (end_date),
  KEY ix_courses_instructor_user_id (instructor_user_id),
  CONSTRAINT fk_courses_instructor FOREIGN KEY (instructor_user_id)
    REFERENCES users(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-3. Enrollments */
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-4. Assignments */
CREATE TABLE assignments (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  course_id   INT UNSIGNED NOT NULL,
  title       VARCHAR(200) NOT NULL,
  due_at      DATETIME NULL,
  total_score INT UNSIGNED NOT NULL DEFAULT 100,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_assignments_course (course_id),
  KEY idx_assignments_due    (due_at),
  CONSTRAINT fk_assignments_course
    FOREIGN KEY (course_id) REFERENCES courses(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-5. Submissions (트리거로 제출 규칙 강제) */
CREATE TABLE submissions (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  assignment_id INT UNSIGNED NOT NULL,
  user_id       INT UNSIGNED NOT NULL,
  score         INT NULL,
  submitted_at  DATETIME NULL,
  file_url      VARCHAR(255) NULL,
  comment       TEXT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NULL,
  graded_at     DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_sub_user_assignment (user_id, assignment_id),
  KEY idx_sub_assign      (assignment_id),
  KEY idx_sub_user        (user_id),
  KEY ix_submissions_submitted_at (submitted_at),
  CONSTRAINT fk_sub_assign
    FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
  CONSTRAINT fk_sub_user
    FOREIGN KEY (user_id)       REFERENCES users(id)       ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-6. course_materials (레거시 코스별 자료) */
CREATE TABLE course_materials (
  id                INT UNSIGNED NOT NULL AUTO_INCREMENT,
  course_id         INT UNSIGNED NOT NULL,
  week              INT UNSIGNED NULL,
  title             VARCHAR(200) NOT NULL,
  kind              ENUM('video','file','link') NOT NULL DEFAULT 'video',
  storage_url       VARCHAR(500) NULL,
  file_path         VARCHAR(500) NULL,
  mime              VARCHAR(100) NULL,
  size_bytes        BIGINT UNSIGNED NULL,
  duration_seconds  INT UNSIGNED NULL,
  is_published      TINYINT(1) NOT NULL DEFAULT 1,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_cm_course (course_id),
  KEY idx_cm_week   (week),
  CONSTRAINT fk_cm_course
    FOREIGN KEY (course_id) REFERENCES courses(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-7. materials (앱 자료) */
CREATE TABLE materials (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  course_id        INT UNSIGNED NOT NULL,
  owner_user_id    INT UNSIGNED NULL,
  title            VARCHAR(200) NOT NULL,
  week             INT UNSIGNED NULL,
  kind             ENUM('video','audio','file','link') NOT NULL DEFAULT 'video',
  storage_url      VARCHAR(500) NULL,
  file_path        VARCHAR(500) NULL,
  mime             VARCHAR(100) NULL,
  size_bytes       BIGINT UNSIGNED NULL,
  duration_seconds INT UNSIGNED NULL,
  is_downloadable  TINYINT(1) NOT NULL DEFAULT 0,
  is_published     TINYINT(1) NOT NULL DEFAULT 1,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_materials_course (course_id),
  KEY idx_materials_week   (week),
  KEY idx_materials_kind   (kind),
  CONSTRAINT fk_materials_course
    FOREIGN KEY (course_id) REFERENCES courses(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_materials_owner
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-8. material_events (재생/완료/다운로드 로그) */
CREATE TABLE material_events (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id         INT UNSIGNED NOT NULL,
  material_id     INT UNSIGNED NOT NULL,
  action          ENUM('play','complete','download') NOT NULL,
  seconds_watched INT UNSIGNED NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_me_user (user_id),
  KEY idx_me_material (material_id),
  KEY idx_me_user_material_action (user_id, material_id, action),
  CONSTRAINT fk_me_user
    FOREIGN KEY (user_id)     REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_me_material
    FOREIGN KEY (material_id) REFERENCES materials(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-9. material_blobs */
CREATE TABLE material_blobs (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  material_id  INT UNSIGNED NOT NULL UNIQUE,
  data         LONGBLOB NOT NULL,
  size_bytes   BIGINT NULL,
  mime_type    VARCHAR(100) DEFAULT 'video/mp4',
  checksum_md5 CHAR(32),
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_material_blobs_material
    FOREIGN KEY (material_id) REFERENCES materials(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-10. notices / notice_attachments */
CREATE TABLE notices (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  course_id      INT UNSIGNED NOT NULL,
  author_user_id INT UNSIGNED NULL,
  title          VARCHAR(200) NOT NULL,
  body           LONGTEXT NOT NULL,
  is_pinned      TINYINT(1) NOT NULL DEFAULT 0,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_notices_course (course_id),
  CONSTRAINT fk_notices_course
    FOREIGN KEY (course_id) REFERENCES courses(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_notices_author
    FOREIGN KEY (author_user_id) REFERENCES users(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notice_attachments (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  notice_id   INT UNSIGNED NOT NULL,
  file_path   VARCHAR(255)  NULL,
  storage_url VARCHAR(2048) NULL,
  filename    VARCHAR(255)  NOT NULL,
  size_bytes  BIGINT NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_notice_id (notice_id),
  CONSTRAINT fk_notice_attachments_notice
    FOREIGN KEY (notice_id) REFERENCES notices(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-11. Discussions (threads/comments/likes) */
CREATE TABLE discussion_threads (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  course_id      INT UNSIGNED NOT NULL,
  author_user_id INT UNSIGNED NOT NULL,
  title          VARCHAR(200) NOT NULL,
  body           LONGTEXT NOT NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_threads_course (course_id),
  CONSTRAINT fk_threads_course
    FOREIGN KEY (course_id) REFERENCES courses(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_threads_author
    FOREIGN KEY (author_user_id) REFERENCES users(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE discussion_comments (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  thread_id  INT UNSIGNED NOT NULL,
  user_id    INT UNSIGNED NOT NULL,
  parent_id  INT UNSIGNED NULL,
  body       LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_comments_thread (thread_id),
  KEY idx_comments_parent (parent_id),
  CONSTRAINT fk_comments_thread
    FOREIGN KEY (thread_id) REFERENCES discussion_threads(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_comments_parent
    FOREIGN KEY (parent_id) REFERENCES discussion_comments(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_comments_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE discussion_comment_likes (
  comment_id INT UNSIGNED NOT NULL,
  user_id    INT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (comment_id, user_id),
  KEY ix_dcl_user (user_id),
  CONSTRAINT fk_dcl_comment
    FOREIGN KEY (comment_id) REFERENCES discussion_comments(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_dcl_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-12. Mentoring (teams/members/reports) */
CREATE TABLE mentoring_teams (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name          VARCHAR(120) NOT NULL,
  owner_user_id INT UNSIGNED NOT NULL,
  is_solo       TINYINT(1)   NOT NULL DEFAULT 0,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_mteam_owner (owner_user_id),
  CONSTRAINT fk_mteam_owner
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE mentoring_team_members (
  id        INT UNSIGNED NOT NULL AUTO_INCREMENT,
  team_id   INT UNSIGNED NOT NULL,
  user_id   INT UNSIGNED NOT NULL,
  role      VARCHAR(40) DEFAULT 'member',
  joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_team_user (team_id, user_id), -- 중복 방지(ALTER 제거, CREATE에 통합)
  KEY idx_tmem_team (team_id),
  KEY idx_tmem_user (user_id),
  CONSTRAINT fk_tmem_team FOREIGN KEY (team_id) REFERENCES mentoring_teams(id) ON DELETE CASCADE,
  CONSTRAINT fk_tmem_user FOREIGN KEY (user_id) REFERENCES users(id)        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE mentoring_reports (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  author_user_id INT UNSIGNED NOT NULL,
  team_id        INT UNSIGNED NULL,
  title          VARCHAR(200) NOT NULL,
  content        TEXT NULL,
  file_url       VARCHAR(255) NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_mrep_author (author_user_id),
  KEY idx_mrep_team   (team_id),
  CONSTRAINT fk_mrep_author FOREIGN KEY (author_user_id) REFERENCES users(id)           ON DELETE CASCADE,
  CONSTRAINT fk_mrep_team   FOREIGN KEY (team_id)        REFERENCES mentoring_teams(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-13. Projects/Tasks/TaskFiles */
CREATE TABLE projects (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title           VARCHAR(200) NOT NULL,
  description     TEXT NULL,
  team_id         INT UNSIGNED NULL,
  owner_user_id   INT UNSIGNED NULL,
  mentor_user_id  INT UNSIGNED NULL,
  status          VARCHAR(30) DEFAULT 'ongoing',
  github_repo_url VARCHAR(255) NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_proj_team   (team_id),
  KEY idx_proj_owner  (owner_user_id),
  KEY idx_proj_mentor (mentor_user_id),
  KEY ix_projects_status (status),
  CONSTRAINT fk_proj_team   FOREIGN KEY (team_id)        REFERENCES mentoring_teams(id) ON DELETE SET NULL,
  CONSTRAINT fk_proj_owner  FOREIGN KEY (owner_user_id)  REFERENCES users(id)           ON DELETE SET NULL,
  CONSTRAINT fk_proj_mentor FOREIGN KEY (mentor_user_id) REFERENCES users(id)           ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_tasks (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  project_id       INT UNSIGNED NOT NULL,
  title            VARCHAR(200) NOT NULL,
  due_at           DATETIME NULL,
  assignee_user_id INT UNSIGNED NULL,
  status           VARCHAR(20) DEFAULT 'todo',
  description      MEDIUMTEXT NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_pt_project   (project_id),
  KEY idx_pt_assignee  (assignee_user_id),
  KEY ix_ptasks_due    (due_at),
  KEY ix_ptasks_status (status),
  CONSTRAINT fk_pt_project  FOREIGN KEY (project_id)       REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_pt_assignee FOREIGN KEY (assignee_user_id) REFERENCES users(id)    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project_task_files (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  task_id          INT UNSIGNED NOT NULL,
  file_url         VARCHAR(255) NOT NULL,
  filename         VARCHAR(255) NULL,
  size_bytes       BIGINT NULL,
  uploader_user_id INT UNSIGNED NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_ptf_task     (task_id),
  KEY idx_ptf_uploader (uploader_user_id),
  CONSTRAINT fk_ptf_task     FOREIGN KEY (task_id)          REFERENCES project_tasks(id) ON DELETE CASCADE,
  CONSTRAINT fk_ptf_uploader FOREIGN KEY (uploader_user_id) REFERENCES users(id)         ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-14. Competitions/Entries */
CREATE TABLE competitions (
  id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title          VARCHAR(200) NOT NULL,
  host           VARCHAR(120) NULL,
  url            VARCHAR(255) NULL,
  apply_deadline DATETIME NULL,
  start_at       DATETIME NULL,
  end_at         DATETIME NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_competitions_deadline (apply_deadline),
  KEY ix_competitions_start    (start_at),
  KEY ix_competitions_end      (end_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE competition_entries (
  id                 INT UNSIGNED NOT NULL AUTO_INCREMENT,
  competition_id     INT UNSIGNED NOT NULL,
  team_id            INT UNSIGNED NULL,
  applicant_user_id  INT UNSIGNED NULL,
  project_id         INT UNSIGNED NULL,
  status             VARCHAR(20) DEFAULT 'draft',
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_centry_comp    (competition_id),
  KEY idx_centry_team    (team_id),
  KEY idx_centry_user    (applicant_user_id),
  KEY idx_centry_project (project_id),
  KEY ix_centries_status (status),
  CONSTRAINT fk_centry_comp    FOREIGN KEY (competition_id)    REFERENCES competitions(id)   ON DELETE CASCADE,
  CONSTRAINT fk_centry_team    FOREIGN KEY (team_id)           REFERENCES mentoring_teams(id) ON DELETE SET NULL,
  CONSTRAINT fk_centry_user    FOREIGN KEY (applicant_user_id) REFERENCES users(id)          ON DELETE SET NULL,
  CONSTRAINT fk_centry_project FOREIGN KEY (project_id)        REFERENCES projects(id)       ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-15. Messages / UserSettings */
CREATE TABLE messages (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  sender_id        INT UNSIGNED NOT NULL,
  receiver_id      INT UNSIGNED NOT NULL,
  title            VARCHAR(200) NOT NULL,
  body             TEXT NULL,
  read_at          DATETIME NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sender_deleted   TINYINT(1) NOT NULL DEFAULT 0,
  receiver_deleted TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY ix_messages_sender (sender_id),
  KEY ix_messages_receiver (receiver_id),
  KEY ix_messages_created_at (created_at),
  KEY ix_messages_read_at (read_at),
  KEY ix_messages_sender_deleted (sender_id, sender_deleted),
  KEY ix_messages_receiver_deleted (receiver_id, receiver_deleted),
  CONSTRAINT fk_msg_sender   FOREIGN KEY (sender_id)   REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_msg_receiver FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_settings (
  id                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id             INT UNSIGNED NOT NULL UNIQUE,
  language            VARCHAR(10)  NOT NULL DEFAULT 'ko',
  theme               VARCHAR(10)  NOT NULL DEFAULT 'light',
  timezone            VARCHAR(50)  NOT NULL DEFAULT 'Asia/Seoul',
  email_notifications TINYINT(1)   NOT NULL DEFAULT 1,
  push_notifications  TINYINT(1)   NOT NULL DEFAULT 0,
  created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_usersettings_user (user_id),
  CONSTRAINT fk_user_settings_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* 2-16. Boards/Posts/Attachments */
CREATE TABLE boards (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key` VARCHAR(32) NOT NULL UNIQUE,
  title VARCHAR(100) NOT NULL,
  description VARCHAR(255) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE posts (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  board_id INT UNSIGNED NOT NULL,
  user_id  INT UNSIGNED NOT NULL,
  title VARCHAR(200) NOT NULL,
  body  MEDIUMTEXT NULL,
  is_pinned TINYINT(1) NOT NULL DEFAULT 0,
  is_locked TINYINT(1) NOT NULL DEFAULT 0,
  views INT UNSIGNED NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_posts_board FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
  CONSTRAINT fk_posts_user  FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
  INDEX idx_posts_board_created (board_id, created_at),
  INDEX idx_posts_board_pinned  (board_id, is_pinned, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE attachments (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  post_id INT UNSIGNED NOT NULL,
  kind ENUM('file','url') NOT NULL,
  storage_path  VARCHAR(255) NULL,
  original_name VARCHAR(255) NULL,
  content_type  VARCHAR(100) NULL,
  file_size     BIGINT NULL,
  url TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_attach_post FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
  INDEX idx_attach_post (post_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* ============================================================================
-- 3) 시드 데이터
============================================================================ */

/* 3-1. 사용자 */

ALTER TABLE users MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;

START TRANSACTION;

/* 학생 16명 + 테스트 학생 2명 + 홍학생 + 교수 + 관리자 */
INSERT INTO users
(name, email, role, username, phone, password, github_url, school, department)
VALUES
('백민하', 'odoru400@naver.com', 'student', 'baekminha',   '010-4202-9630', 'stud4821!', 'https://github.com/kim-smile', '한서대학교/5학년(졸업예정)/항공전자공학과', '로봇, AI'),
('김태민', 'kimtaemin0203@gmail.com', 'student', 'kimtaemin','010-3902-9387', 'stud9310!', 'https://github.com/kim-smile', '나사렛대학교/4/IT융합학부', '로봇, AI'),
('김상혁', 'xcv1107@naver.com', 'student', 'kimsanghyuk',  '010-3060-5627', 'stud1742!', 'https://github.com/kim-smile', '우송대학교/3학년/AI빅데이터학과', '로봇, AI'),
('강지훈', 'jih00n22@naver.com', 'student', 'kangjihun',   '010-4344-2968', 'stud5296!', 'https://github.com/kim-smile', '우송대학교/3/컴퓨터정보보안전공', 'AI, 빅데이터'),
('허근',   'kneuny@naver.com', 'student', 'heogeun',       '010-2511-9591', 'stud6403!', 'https://github.com/kim-smile', '충남대학교/4/응용생물학과', '빅데이터, 웹서비스'),
('김기성', 'rlarltjd721@naver.com', 'student', 'kimgiseong','010-2331-4724', 'stud3078!', 'https://github.com/kim-smile', '우송대학교/4/스마트IT 보안전공', '로봇, AI'),
('김선준', 'sunjoon100@naver.com', 'student', 'kimsunjoon', '010-7723-9254', 'stud8921!', 'https://github.com/kim-smile', '나사렛대학교/4/IT융합학부', '로봇, AI'),
('이진수', 'jjkkhh456@naver.com', 'student', 'leejinsu',   '010-8005-5726', 'stud2187!', 'https://github.com/kim-smile', '나사렛대학교/4/IT융합학부', '로봇, AI'),
('김하은', 'ha2un0908@naver.com', 'student', 'kimhaeun',   '010-3829-6194', 'stud4372!', 'https://github.com/kim-smile', '나사렛대학교/4/IT인공지능학부', '로봇, AI'),
('이민용', 'kv0435029@naver.com', 'student', 'leeminyong', '010-2782-5603', 'stud7610!', 'https://github.com/kim-smile', '나사렛대학교/4/IT융합', '로봇, AI'),
('김미소', 'misosmile0306@naver.com', 'student', 'kimmi_so','010-2355-5103', 'stud1543!', 'https://github.com/kim-smile', '나사렛대학교/4/IT인공지능학부', 'AI, 웹서비스'),
('오민수', 'alsehd50@naver.com', 'student', 'ohminsu',     '010-8231-4070', 'stud9450!', 'https://github.com/kim-smile', '우송대학교/4/컴퓨터정보보안전공', 'AI'),
('최승균', 'xormr4596@gmail.com', 'student', 'choiseunggyun','010-4037-8317','stud2209!','https://github.com/kim-smile','우송대학교/3/AI빅데이터학과','AI, 웨어러블기기'),
('이용전', 'wads1234k@naver.com', 'student', 'leeyongjeon','010-3271-7658', 'stud3827!', 'https://github.com/kim-smile', '나사렛대학교/졸업/컴퓨터소프트웨어학과', '로봇, 웨어러블기기'),
('김지훈', 'KJHrlawlgns02@gmail.com', 'student', 'kimjihun','010-9487-2801', 'stud6984!', 'https://github.com/kim-smile', '나사렛대학교/4/IT인공지능학부', 'AI, 빅데이터'),
('강유성', 'dbtjddl0123@naver.com', 'student', 'kangyuseong','010-5036-9500','stud5702!','https://github.com/kim-smile','우송대학교/25년 2월 졸업/언어치료청각재활학과','AI, 웨어러블기기'),
-- 테스트 학생 2명
('박학생', 'student2@example.com', 'student', 'student2',  '010-0000-1002', 'student123', 'https://github.com/student2', '우송대학교', 'IT인공지능학부'),
('이학생', 'student3@example.com', 'student', 'student3',  '010-0000-1003', 'student123', 'https://github.com/student3', '우송대학교', 'IT인공지능학부'),
-- 데모 기본 학생(홍학생) — 이후 스크립트가 @STU1 로 참조
('홍학생', 'student@example.com', 'student', 'student',    '010-0000-0001', 'student123', 'https://github.com/kim-smile', '우송대학교', '컴퓨터공학과'),
-- 교수/관리자
('김교수', 'prof@example.com',  'instructor', 'prof',  '010-0000-0002', 'prof123',  NULL, '우송대학교', '소프트웨어융합학부'),
('관리자', 'admin@example.com', 'admin',      'admin', '010-0000-0003', 'admin123', NULL, '우송대학교', NULL);

/* 부서(department) 보정 — 이미 값이 있어도 안전 */
UPDATE users SET department = '소프트웨어융합학부' WHERE email = 'prof@example.com';
UPDATE users SET department = '컴퓨터공학과'     WHERE email IN ('student@example.com');
UPDATE users SET department = 'IT인공지능학부'   WHERE email IN ('student2@example.com','student3@example.com');

/* 편의 변수 (지금 시점엔 모두 존재하므로 NULL 아님) */
SET @STU1 := (SELECT id FROM users WHERE username='student'  LIMIT 1);
SET @PROF := (SELECT id FROM users WHERE username='prof'     LIMIT 1);
SET @STU2 := (SELECT id FROM users WHERE username='student2' LIMIT 1);
SET @STU3 := (SELECT id FROM users WHERE username='student3' LIMIT 1);

COMMIT;

/* 3-2. 강좌 */
INSERT INTO courses (title, start_date, end_date) VALUES
  ('웹 프로그래밍',       '2024-12-15', '2025-02-20'),
  ('데이터베이스 시스템',  '2025-01-10', '2025-03-20'),
  ('알고리즘',            '2025-01-12', '2025-03-15');

-- 편의 변수
SET @COURSE_WEB := (SELECT id FROM courses WHERE title='웹 프로그래밍' LIMIT 1);
SET @COURSE_DB  := (SELECT id FROM courses WHERE title='데이터베이스 시스템' LIMIT 1);
SET @COURSE_ALG := (SELECT id FROM courses WHERE title='알고리즘' LIMIT 1);

/* 강좌 상세/담당교수/학점/시간표 세팅 */
UPDATE courses
SET description = 'HTML, CSS, JavaScript 기초부터 실습 중심으로 동적 웹 페이지 제작을 학습합니다. 최신 웹 트렌드와 프로젝트 기반 실습을 포함합니다.',
    schedule_text = '월, 수 14:00-15:30',
    credit = 3,
    instructor_user_id = @PROF
WHERE id = @COURSE_WEB;

UPDATE courses
SET description = '관계형 데이터베이스 설계/정규화, SQL, 트랜잭션과 인덱싱, 성능 최적화까지 실습과 함께 학습합니다.',
    schedule_text = '화, 목 10:30-12:00',
    credit = 3,
    instructor_user_id = @PROF
WHERE id = @COURSE_DB;

UPDATE courses
SET description = '정렬, 탐색, 그래프, 동적 계획법 등 핵심 알고리즘을 이론과 코딩 실습으로 다룹니다.',
    schedule_text = '화 15:00-16:30, 금 15:00-16:30',
    credit = 3,
    instructor_user_id = @PROF
WHERE id = @COURSE_ALG;

/* 3-3. 수강신청 */
INSERT INTO enrollments (user_id, course_id) VALUES
  (@STU1, @COURSE_WEB),
  (@STU1, @COURSE_DB),
  (@STU1, @COURSE_ALG);

/* 3-4. 과제 */
INSERT INTO assignments (id, course_id, title, due_at, total_score, created_at, updated_at) VALUES
  (1, @COURSE_WEB, '웹프로그래밍 프로젝트',     '2025-09-07 23:00:43', 100, NOW(), NOW()),
  (2, @COURSE_DB,  '데이터베이스 중간고사',      '2025-09-10 23:00:43', 100, NOW(), NOW()),
  (3, @COURSE_ALG, '알고리즘 과제 #3',          '2025-09-12 23:00:43', 100, NOW(), NOW()),
  (4, @COURSE_WEB, 'HTML/CSS 퀴즈',             '2025-09-04 23:00:43',  50, NOW(), NOW()),
  (5, @COURSE_DB,  'ERD 과제',                  '2025-09-03 23:00:43',  50, NOW(), NOW()),
  (6, @COURSE_WEB, '과제개발계획서 제출',       '2025-09-11 00:00:00', 100, NOW(), NOW()),
  (7, @COURSE_WEB, 'HTML/CSS 미니 프로젝트',    '2025-09-25 23:59:00', 100, NOW(), NOW());

/* 3-5. 자료 */
INSERT INTO course_materials
  (id, course_id, week, title, kind, storage_url, file_path, mime, size_bytes, duration_seconds, is_published, created_at, updated_at)
VALUES
  (1, @COURSE_WEB, 1, '1주차: HTML 기초',        'video', NULL, 'materials/1/1-html.mp4',  'video/mp4',      123456789, 2700, 1, NOW(), NOW()),
  (2, @COURSE_DB,  2, '2주차: CSS 스타일링',     'video', NULL, 'materials/1/2-css.mp4',   'video/mp4',      234567890, 3000, 1, NOW(), NOW()),
  (3, @COURSE_ALG, 0, '실습 자료 - HTML 템플릿', 'file',  NULL, 'materials/1/html-template.zip', 'application/zip', 2500000, NULL, 1, NOW(), NOW());

INSERT INTO materials
  (id, course_id, owner_user_id, title, week, kind, storage_url, file_path, mime, size_bytes, duration_seconds, is_downloadable, is_published, created_at, updated_at)
VALUES
  (4, @COURSE_WEB, @PROF, '바이오헬스 OT.mp4', 1, 'video', NULL, 'materials/1/바T.mp4', 'video/mp4', NULL, NULL, 0, 1, NOW(), NOW());

UPDATE materials
SET file_path='바다.mp4', mime='video/mp4'
WHERE id=4;

/* 3-6. 자료 이벤트 */
INSERT INTO material_events (user_id, material_id, action, seconds_watched, created_at) VALUES
  (@STU1, 4, 'play',     NULL, '2025-09-06 04:20:00'),
  (@STU2, 4, 'play',     NULL, '2025-09-06 04:27:00'),
  (@STU1, 4, 'complete', 2600, '2025-09-06 04:35:00');

/* 3-7. 공지/첨부 */
INSERT INTO notices (course_id, author_user_id, title, body, is_pinned, created_at, updated_at) VALUES
  (@COURSE_WEB, @PROF, '중간고사 안내',      '중간고사 범위 및 일정 안내입니다.', 1, '2025-03-05 09:00:00', '2025-03-05 09:00:00'),
  (@COURSE_WEB, @PROF, '실습 자료 업데이트', '실습 자료가 업데이트되었습니다.', 0, '2025-02-28 12:00:00', '2025-02-28 12:00:00');

-- 위 공지 중 '중간고사 안내' id 확보 후 첨부 1건
SET @nid := (SELECT id FROM notices WHERE course_id=@COURSE_WEB AND title='중간고사 안내' LIMIT 1);
INSERT INTO notice_attachments (notice_id, file_path, filename, size_bytes, created_at)
VALUES (@nid, '간편 장부 프로그램_01.pdf', '간편 장부 프로그램_01.pdf', 0, NOW());

/* 3-8. 토론 스레드/댓글 */
INSERT INTO discussion_threads (id, course_id, author_user_id, title, body, created_at, updated_at) VALUES
  (1, @COURSE_WEB, @PROF, '1주차 과제 질문 스레드', '여기에 자유롭게 질문을 남겨주세요.', '2025-09-06 18:53:00', '2025-09-06 18:53:00'),
  (2, @COURSE_WEB, @PROF, '프로젝트 팀 편성',       '팀 편성 관련 안내와 희망 팀원 매칭용 스레드입니다.', '2025-09-05 10:00:00', '2025-09-05 10:00:00');

INSERT INTO discussion_comments (id, thread_id, user_id, parent_id, body, created_at, updated_at) VALUES
  (1, 1, @STU1, NULL, '너무 어려워요', '2025-09-06 10:01:00', '2025-09-06 10:01:00'),
  (2, 1, @STU2, 1,    '이 부분은 이렇게 생각해보면 쉬워요!', '2025-09-06 10:05:00', '2025-09-06 10:05:00');

/* 3-10. 멘토링 팀/멤버/보고서 */
INSERT INTO mentoring_teams (name, owner_user_id, is_solo) VALUES
  ('웹프 A팀',   @STU1, 0),
  ('홍학생(개인)', @STU1, 1);

-- 팀/멤버 변수
SET @TEAM_A := (SELECT id FROM mentoring_teams WHERE name='웹프 A팀' LIMIT 1);
SET @TEAM_S := (SELECT id FROM mentoring_teams WHERE name='홍학생(개인)' LIMIT 1);

INSERT INTO mentoring_team_members (team_id, user_id, role) VALUES
  (@TEAM_A, @STU1, 'leader'),
  (@TEAM_A, @STU2, 'member'),
  (@TEAM_A, @STU3, 'member'),
  (@TEAM_S, @STU1, 'leader');

INSERT INTO mentoring_reports (author_user_id, team_id, title, content) VALUES
  (@STU1, @TEAM_A, '주간 보고서 #1', '금주 목표: 프로젝트 기본 구조 잡기');

/* 3-11. 프로젝트/작업 */
INSERT INTO projects (title, description, team_id, owner_user_id, github_repo_url, status) VALUES
  ('웹프 팀 프로젝트', '프런트/백엔드 기초', @TEAM_A, NULL, 'https://github.com/example/webproj', 'ongoing'),
  ('개인 미니 앱',     'Flask로 간단한 앱',   NULL,   @STU1, NULL,                                  'ongoing');

-- 협업 테스트 프로젝트 없으면 생성해도 되지만, 여기서는 바로 생성
INSERT INTO projects (title, description, team_id, status)
VALUES ('테스트 협업 프로젝트', '탈퇴/프로필/작업 뒤로가기 점검용', @TEAM_A, 'ongoing');

SET @PROJ_TEST := (SELECT id FROM projects WHERE title='테스트 협업 프로젝트' AND team_id=@TEAM_A LIMIT 1);

INSERT INTO project_tasks (project_id, title, description, due_at, assignee_user_id, status) VALUES
  ((SELECT id FROM projects WHERE title='웹프 팀 프로젝트' LIMIT 1), 'UI 목업 만들기', NULL, DATE_ADD(NOW(), INTERVAL 3 DAY), @STU1, 'doing'),
  ((SELECT id FROM projects WHERE title='개인 미니 앱'     LIMIT 1), '라우팅 구현',    NULL, DATE_ADD(NOW(), INTERVAL 2 DAY), @STU1, 'todo'),
  (@PROJ_TEST, '회의 준비',        '자료 취합 및 안건 정리', DATE_ADD(NOW(), INTERVAL 2 DAY), @STU2, 'doing'),
  (@PROJ_TEST, '프로토타입 작성',  'UI 초안 및 흐름도',     DATE_ADD(NOW(), INTERVAL 4 DAY), @STU3, 'todo');

/* 3-12. 공모전/신청 */
INSERT INTO competitions (title, host, url, apply_deadline) VALUES
  ('캡스톤 경진대회', '공과대학', 'https://contest.example.com', DATE_ADD(NOW(), INTERVAL 30 DAY));

INSERT INTO competition_entries (competition_id, team_id, applicant_user_id, project_id, status) VALUES
  ((SELECT id FROM competitions WHERE title='캡스톤 경진대회' LIMIT 1),
   @TEAM_A,
   @STU1,
   (SELECT id FROM projects WHERE title='웹프 팀 프로젝트' LIMIT 1),
   'submitted');

/* 3-13. 메시지 */
INSERT INTO messages (sender_id, receiver_id, title, body, read_at, created_at) VALUES
  ((SELECT id FROM users WHERE email='admin@example.com'),   (SELECT id FROM users WHERE email='student@example.com'),  '환영합니다',             '플랫폼에 오신 것을 환영합니다!', NULL, NOW()),
  ((SELECT id FROM users WHERE email='prof@example.com'),    (SELECT id FROM users WHERE email='student@example.com'),  '멘토링 안내',           '이번 주 멘토링은 금요일 3시입니다.', NULL, NOW()),
  ((SELECT id FROM users WHERE email='student@example.com'), (SELECT id FROM users WHERE email='prof@example.com'),     '과제 관련 질문 드립니다','교수님, HTML/CSS 과제 제출 형식 문의드립니다.', NULL, DATE_ADD(NOW(), INTERVAL -2 DAY)),
  ((SELECT id FROM users WHERE email='student2@example.com'),(SELECT id FROM users WHERE email='prof@example.com'),     '팀 프로젝트 주제 제안', '바이오헬스 데이터 시각화 주제 어떤가요?', NOW(), DATE_ADD(NOW(), INTERVAL -1 DAY)),
  ((SELECT id FROM users WHERE email='prof@example.com'),    (SELECT id FROM users WHERE email='student@example.com'),  '과제 관련 질문 드립니다','제출 형식은 PDF + 소스코드 ZIP입니다.', NOW(), DATE_ADD(NOW(), INTERVAL -1 DAY)),
  ((SELECT id FROM users WHERE email='student@example.com'), (SELECT id FROM users WHERE email='prof@example.com'),     '출결 문의',             '지난주 결석 사유서 제출 방법 문의드립니다.', NULL, DATE_ADD(NOW(), INTERVAL -12 HOUR)),
  ((SELECT id FROM users WHERE email='prof@example.com'),    (SELECT id FROM users WHERE email='student2@example.com'), '프로젝트 저장소 생성',   'GitHub 리포지토리 생성 및 초대 확인하세요.', NULL, DATE_ADD(NOW(), INTERVAL -20 HOUR)),
  ((SELECT id FROM users WHERE email='admin@example.com'),   (SELECT id FROM users WHERE email='prof@example.com'),     '[공지] 시스템 점검 안내','금요일 00:00~02:00 점검 예정입니다.', NULL, DATE_ADD(NOW(), INTERVAL -6 HOUR));

/* 3-14. 보드/게시글/첨부 */
INSERT INTO boards(`key`, title, description) VALUES
  ('notice', '공지사항',   '중요 공지 및 안내'),
  ('free',   '자유게시판', '자유롭게 의견을 나누는 공간');

INSERT INTO posts(board_id, user_id, title, body, is_pinned)
VALUES (
  (SELECT id FROM boards WHERE `key`='notice'),
  (SELECT id FROM users  WHERE email='prof@example.com'),
  'LMS 오픈 안내',
  '플랫폼이 오픈되었습니다. 공지 확인 부탁드립니다.',
  1
);

INSERT INTO posts(board_id, user_id, title, body, is_pinned)
VALUES (
  (SELECT id FROM boards WHERE `key`='free'),
  (SELECT id FROM users  WHERE email='admin@example.com'),
  '첫 글 테스트',
  '자유게시판 테스트 글입니다 😀',
  0
);