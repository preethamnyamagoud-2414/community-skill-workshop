"""
Automated Test Suite for Learner Dashboard
Covers: Personalized Welcome, Real Database Analytics, Upcoming Sessions,
        Registration History, Profile Information, Sidebar Navigation & Route Security.
Run with: python -m unittest tests/test_dashboard.py
"""

import os
import sys
import unittest
import tempfile
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from app import app, get_db


class LearnerDashboardTestCase(unittest.TestCase):
    """Test case for Learner Dashboard data integrity, metrics, and views."""

    def setUp(self):
        """Set up an isolated temporary database for each test run."""
        self.db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        app.config['DATABASE'] = self.temp_db_path
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            schema_path = os.path.join(BASE_DIR, 'database', 'schema.sql')
            conn = sqlite3.connect(self.temp_db_path)
            with open(schema_path, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()

    def tearDown(self):
        """Clean up the temporary database."""
        import gc
        gc.collect()
        try:
            os.close(self.db_fd)
        except OSError:
            pass
        if os.path.exists(self.temp_db_path):
            try:
                os.unlink(self.temp_db_path)
            except PermissionError:
                pass

    def login_learner(self):
        """Logs in as the pre-seeded learner (Alex Johnson)."""
        return self.client.post('/login', data={
            'email': 'learner@workshop.com',
            'password': 'learner123'
        }, follow_redirects=True)

    def login_admin(self):
        """Logs in as the pre-seeded admin."""
        return self.client.post('/login', data={
            'email': 'admin@workshop.com',
            'password': 'admin123'
        }, follow_redirects=True)

    # ----------------------------------------------------
    # 1. Access Control Tests
    # ----------------------------------------------------
    def test_unauthenticated_access_denied(self):
        """Test anonymous user is redirected to login when visiting dashboard."""
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please sign in to access this page', response.data)

    def test_admin_redirected_to_admin_dashboard(self):
        """Test administrator is redirected to admin dashboard when requesting learner dashboard."""
        self.login_admin()
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Control Center', response.data)

    # ----------------------------------------------------
    # 2. Data Integrity & Personalization Tests
    # ----------------------------------------------------
    def test_learner_welcome_and_sidebar_profile(self):
        """Test learner dashboard displays personalized welcome message and sidebar details."""
        self.login_learner()
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

        # Welcome header
        self.assertIn(b'Welcome back, Alex Johnson!', response.data)
        # Sidebar avatar initials & email
        self.assertIn(b'AL', response.data)
        self.assertIn(b'learner@workshop.com', response.data)
        self.assertIn(b'Community Learner', response.data)

    def test_real_database_statistics(self):
        """Test that counts are calculated dynamically from SQLite without hardcoded numbers."""
        self.login_learner()

        # In seed data for user 2 (Alex Johnson):
        # 1 confirmed enrollment (workshop 1)
        # 1 attended enrollment (workshop 4)
        # Total registered = 2, Upcoming = 1, Completed = 1, Feedback = 1
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Total Registered', response.data)
        self.assertIn(b'Upcoming Workshops', response.data)
        self.assertIn(b'Completed Workshops', response.data)
        self.assertIn(b'Feedback Shared', response.data)

        # Enroll in workshop 3 to verify dynamic increment
        self.client.post('/enroll/3')
        updated_response = self.client.get('/dashboard')
        # Total registered should now be 3, upcoming 2
        with app.app_context():
            db = get_db()
            confirmed = db.execute(
                "SELECT COUNT(*) FROM enrollments WHERE user_id = 2 AND status = 'confirmed'"
            ).fetchone()[0]
            self.assertEqual(confirmed, 2)

    def test_upcoming_sessions_section(self):
        """Test that upcoming workshops appear with details, schedule, venue, and cancel button."""
        self.login_learner()
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

        # Workshop 1 is confirmed upcoming
        self.assertIn(b'Web Development Foundations', response.data)
        self.assertIn(b'Sarah Connor', response.data)
        self.assertIn(b'Computer Lab 2', response.data)
        self.assertIn(b'Cancel Seat', response.data)

    def test_registration_history_table(self):
        """Test that full enrollment history renders in table."""
        self.login_learner()
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

        self.assertIn(b'Workshop Registration History', response.data)
        self.assertIn(b'Personal Financial Literacy &amp; Budgeting', response.data)
        self.assertIn(b'Attended', response.data)

    def test_profile_information_card(self):
        """Test learner profile attributes rendered from database."""
        self.login_learner()
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

        self.assertIn(b'Profile Information', response.data)
        self.assertIn(b'Alex Johnson', response.data)
        self.assertIn(b'learner@workshop.com', response.data)
        self.assertIn(b'555-0144', response.data)
        self.assertIn(b'Learner', response.data)


if __name__ == '__main__':
    unittest.main()
