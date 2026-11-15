-- ====================================================
-- Community Skill-Building Workshop Platform Schema
-- Database: SQLite
-- ====================================================

PRAGMA foreign_keys = ON;

-- 1. Users Table (Learners & Administrators)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'learner' CHECK(role IN ('learner', 'admin')),
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Workshops Table
CREATE TABLE IF NOT EXISTS workshops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    trainer_name TEXT NOT NULL,
    workshop_date TEXT NOT NULL,      -- Format: YYYY-MM-DD
    workshop_time TEXT NOT NULL,      -- e.g. 10:00 AM
    venue TEXT NOT NULL,              -- e.g. Community Hall Room A or Online Zoom Link
    total_seats INTEGER NOT NULL CHECK(total_seats > 0),
    available_seats INTEGER NOT NULL CHECK(available_seats >= 0),
    status TEXT NOT NULL DEFAULT 'upcoming' CHECK(status IN ('upcoming', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Enrollments Table
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    workshop_id INTEGER NOT NULL,
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'cancelled', 'attended', 'Present', 'Absent')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (workshop_id) REFERENCES workshops(id) ON DELETE CASCADE,
    UNIQUE(user_id, workshop_id)
);

-- 4. Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    workshop_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comments TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (workshop_id) REFERENCES workshops(id) ON DELETE CASCADE,
    UNIQUE(user_id, workshop_id)
);

-- 5. Attendance Records Table (Strict Prevention of Duplicates)
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    workshop_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (workshop_id) REFERENCES workshops(id) ON DELETE CASCADE,
    UNIQUE(user_id, workshop_id)
);

-- ====================================================
-- Initial Seed Data (Demo Users, Workshops, Feedback)
-- Passwords:
-- admin@workshop.com   -> admin123  (scrypt or pbkdf2)
-- learner@workshop.com -> learner123
-- ====================================================

-- Demo Admin & Learner (pre-hashed with standard Werkzeug PBKDF2-SHA256)
-- admin@workshop.com   -> admin123
-- learner@workshop.com -> learner123
INSERT OR IGNORE INTO users (id, name, email, password_hash, role, phone) VALUES 
(1, 'System Administrator', 'admin@workshop.com', 'pbkdf2:sha256:260000$salt2026$ab6d6e0b214e98b0c37489eb47bed8e1af73a637a40399720ee6ffd733f31c2a', 'admin', '555-0199'),
(2, 'Alex Johnson', 'learner@workshop.com', 'pbkdf2:sha256:260000$salt2026$d3391a078f9f2dd7a77d7dd1f8d30cf0aef4a9a6087054a1e36eb2290602aa35', 'learner', '555-0144');

-- Demo Workshops
INSERT OR IGNORE INTO workshops (id, title, description, category, trainer_name, workshop_date, workshop_time, venue, total_seats, available_seats, status) VALUES 
(1, 'Web Development Foundations', 'Learn semantic HTML5, modern responsive CSS3, and beginner JavaScript to build your first live portfolio website.', 'Technology', 'Sarah Connor', '2026-12-05', '10:00 AM - 01:00 PM', 'Computer Lab 2 / Community Hub', 25, 24, 'upcoming'),
(2, 'Urban Gardening & Composting', 'Practical hands-on workshop covering container gardening, soil enrichment, seasonal planting, and kitchen waste composting.', 'Environment', 'Marcus Green', '2026-12-12', '09:00 AM - 12:00 PM', 'Community Botanical Center', 20, 19, 'upcoming'),
(3, 'Basic Woodworking & Tool Safety', 'Master hand saws, chisels, sanders, and joinery techniques. Build your own sturdy wooden bookstand to take home.', 'Crafts & Trades', 'David Miller', '2026-12-19', '02:00 PM - 05:30 PM', 'Maker Workshop Bay 4', 15, 15, 'upcoming'),
(4, 'Personal Financial Literacy & Budgeting', 'Essential guidance on personal savings, smart budgeting, debt management, and understanding modern retirement accounts.', 'Finance', 'Elena Rodriguez', '2026-11-01', '06:00 PM - 08:00 PM', 'Online via Community Zoom', 50, 48, 'completed');

-- Demo Enrollments
INSERT OR IGNORE INTO enrollments (id, user_id, workshop_id, enrollment_date, status) VALUES
(1, 2, 1, '2026-11-10 14:30:00', 'confirmed'),
(2, 2, 4, '2026-10-25 11:15:00', 'attended');

-- Demo Feedback for Completed Workshop
INSERT OR IGNORE INTO feedback (id, user_id, workshop_id, rating, comments) VALUES
(1, 2, 4, 5, 'Elena explained budgeting in such an approachable way! The practical spreadsheets she shared were immensely helpful.');

-- Demo Attendance Records (Pre-Marked Present)
INSERT OR IGNORE INTO attendance (id, enrollment_id, user_id, workshop_id, status) VALUES
(1, 2, 2, 4, 'Present');
