CREATE DATABASE IF NOT EXISTS lms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE lms_db;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `submissions`;
DROP TABLE IF EXISTS `assignments`;
DROP TABLE IF EXISTS `enrollments`;
DROP TABLE IF EXISTS `courses`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE `users` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(190) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `courses` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(200) NOT NULL,
  `start_date` DATE NULL,
  `end_date` DATE NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `enrollments` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` INT UNSIGNED NOT NULL,
  `course_id` INT UNSIGNED NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_enroll_user` (`user_id`),
  KEY `idx_enroll_course` (`course_id`),
  CONSTRAINT `fk_enroll_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_enroll_course` FOREIGN KEY (`course_id`) REFERENCES `courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `assignments` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `course_id` INT UNSIGNED NOT NULL,
  `title` VARCHAR(200) NOT NULL,
  `due_at` DATETIME NULL,
  `total_score` INT DEFAULT 100,
  PRIMARY KEY (`id`),
  KEY `idx_assign_course` (`course_id`),
  CONSTRAINT `fk_assign_course` FOREIGN KEY (`course_id`) REFERENCES `courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `submissions` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `assignment_id` INT UNSIGNED NOT NULL,
  `user_id` INT UNSIGNED NOT NULL,
  `score` INT NULL,
  `submitted_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_sub_assign` (`assignment_id`),
  KEY `idx_sub_user` (`user_id`),
  CONSTRAINT `fk_sub_assign` FOREIGN KEY (`assignment_id`) REFERENCES `assignments`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sub_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 샘플데이터
INSERT INTO `users` (`name`, `email`) VALUES ('영이', 'young@example.com');

INSERT INTO `courses` (`title`, `start_date`, `end_date`) VALUES
('웹 프로그래밍', '2024-12-15', '2025-02-20'),
('데이터베이스 시스템', '2025-01-10', '2025-03-20'),
('알고리즘', '2025-01-12', '2025-03-15');

INSERT INTO `enrollments` (`user_id`, `course_id`) VALUES (1,1),(1,2),(1,3);

INSERT INTO `assignments` (`course_id`, `title`, `due_at`, `total_score`) VALUES
(1, '웹 프로그래밍 프로젝트', DATE_ADD(NOW(), INTERVAL 2 DAY), 100),
(2, '데이터베이스 중간고사', DATE_ADD(NOW(), INTERVAL 5 DAY), 100),
(3, '알고리즘 과제 #3', DATE_ADD(NOW(), INTERVAL 7 DAY), 100),
(1, 'HTML/CSS 퀴즈', DATE_ADD(NOW(), INTERVAL -1 DAY), 50),
(2, 'ERD 과제', DATE_ADD(NOW(), INTERVAL -2 DAY), 50);

INSERT INTO `submissions` (`assignment_id`, `user_id`, `score`, `submitted_at`) VALUES
(1, 1, 95, NOW()),
(4, 1, 40, DATE_ADD(NOW(), INTERVAL -2 DAY));