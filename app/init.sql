CREATE DATABASE IF NOT EXISTS banned_ips_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE banned_ips_db;

CREATE TABLE IF NOT EXISTS banned_ips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45) NOT NULL,
    bantime DATETIME NOT NULL,
    country VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    city VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    isp VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    latitude DECIMAL(10, 8) DEFAULT NULL,
    longitude DECIMAL(11, 8) DEFAULT NULL,
    attempts INT DEFAULT 0,
    jail VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS total_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    num_ips INT,
    num_failed_attempts INT
);

Create TABLE IF NOT EXISTS jails (
    id INT AUTO_INCREMENT PRIMARY KEY,
    jail VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
);