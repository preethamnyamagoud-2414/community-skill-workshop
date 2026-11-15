-- ==============================================================================
-- SkillConnect - Cloud database schema (MySQL 8 / TiDB Cloud)
-- Used in production (Vercel). Local development keeps using database/schema.sql (SQLite).
-- Run via: python scripts/init_cloud_db.py
-- ==============================================================================

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(512) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'learner',
    phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_users_role CHECK (role IN ('learner', 'admin'))
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workshops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    trainer_name VARCHAR(255) NOT NULL,
    workshop_date VARCHAR(10) NOT NULL,
    workshop_time VARCHAR(50) NOT NULL,
    venue VARCHAR(255) NOT NULL,
    total_seats INT NOT NULL,
    available_seats INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'upcoming',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_ws_total CHECK (total_seats > 0),
    CONSTRAINT chk_ws_available CHECK (available_seats >= 0),
    CONSTRAINT chk_ws_status CHECK (status IN ('upcoming', 'completed', 'cancelled'))
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS enrollments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    workshop_id INT NOT NULL,
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    UNIQUE KEY uq_enroll (user_id, workshop_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (workshop_id) REFERENCES workshops(id) ON DELETE CASCADE,
    CONSTRAINT chk_enroll_status CHECK (status IN ('confirmed', 'cancelled', 'attended', 'Present', 'Absent'))
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    workshop_id INT NOT NULL,
    rating INT NOT NULL,
    comments TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_feedback (user_id, workshop_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (workshop_id) REFERENCES workshops(id) ON DELETE CASCADE,
    CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    enrollment_id INT NOT NULL,
    user_id INT NOT NULL,
    workshop_id INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_attendance (user_id, workshop_id),
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (workshop_id) REFERENCES workshops(id) ON DELETE CASCADE,
    CONSTRAINT chk_att_status CHECK (status IN ('Present', 'Absent'))
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS login_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    ip_address VARCHAR(64),
    attempted_at VARCHAR(19) NOT NULL,
    KEY idx_login_attempts_email (email, attempted_at)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample workshops (public content only; no demo user accounts in production)
INSERT IGNORE INTO workshops (id, title, description, category, trainer_name, workshop_date, workshop_time, venue, total_seats, available_seats, status) VALUES
(1, 'Web Development Foundations', 'Learn semantic HTML5, modern responsive CSS3, and beginner JavaScript to build your first live portfolio website.', 'Technology', 'Sarah Connor', '2026-12-05', '10:00 AM - 01:00 PM', 'Computer Lab 2 / Community Hub', 25, 25, 'upcoming'),
(2, 'Urban Gardening & Composting', 'Practical hands-on workshop covering container gardening, soil enrichment, seasonal planting, and kitchen waste composting.', 'Environment', 'Marcus Green', '2026-12-12', '09:00 AM - 12:00 PM', 'Community Botanical Center', 20, 20, 'upcoming'),
(3, 'Basic Woodworking & Tool Safety', 'Master hand saws, chisels, sanders, and joinery techniques. Build your own sturdy wooden bookstand to take home.', 'Crafts & Trades', 'David Miller', '2026-12-19', '02:00 PM - 05:30 PM', 'Maker Workshop Bay 4', 15, 15, 'upcoming'),
(4, 'Personal Financial Literacy & Budgeting', 'Essential guidance on personal savings, smart budgeting, debt management, and understanding modern retirement accounts.', 'Finance', 'Elena Rodriguez', '2026-11-01', '06:00 PM - 08:00 PM', 'Online via Community Zoom', 50, 50, 'completed');
