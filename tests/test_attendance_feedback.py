"""
Automated Test Suite for Attendance and Feedback Subsystems
Covers: Attendance Marking (Present / Absent), Duplicate Attendance Prevention,
        Participant-Restricted Feedback, Star Rating Bounds Validation, and Admin Moderation.
Run with: python -m unittest tests/test_attendance_feedback.py
"""

import os
import sys
import unittest
import tempfile
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from app import app, get_db


class AttendanceFeedbackTestCase(unittest.TestCase):
    """Test case for Attendance tracking and Participant-Restricted Feedback."""

    def setUp(self):
        """Set up an isolated temporary SQLite database for each test run."""
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
        """Logs in as the pre-seeded learner (Alex Johnson, id 2)."""
        return self.client.post('/login', data={
            'email': 'learner@workshop.com',
            'password': 'learner123'
        }, follow_redirects=True)

    def login_admin(self):
        """Logs in as the pre-seeded administrator (id 1)."""
        return self.client.post('/login', data={
            'email': 'admin@workshop.com',
            'password': 'admin123'
        }, follow_redirects=True)

    # ----------------------------------------------------
    # 1. Attendance Module Tests
    # ----------------------------------------------------
    def test_admin_view_registered_participants(self):
        """Test administrator can view attendee roster with contact info and workshop details."""
        self.login_admin()
        response = self.client.get('/admin/participants')
        self.assertEqual(response.status_code, 200)

        # In seed data: User 2 is registered for Workshop 1
        self.assertIn(b'Alex Johnson', response.data)
        self.assertIn(b'learner@workshop.com', response.data)
        self.assertIn(b'Web Development Foundations', response.data)

    def test_admin_mark_attendance_present(self):
        """Test administrator marks attendance as Present and updates DB."""
        self.login_admin()

        response = self.client.post('/admin/attendance/mark', data={
            'enrollment_id': '1',
            'status': 'Present'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Attendance for participant marked as Present', response.data)

        with app.app_context():
            db = get_db()
            att = db.execute("SELECT * FROM attendance WHERE enrollment_id = 1").fetchone()
            self.assertIsNotNone(att)
            self.assertEqual(att['status'], 'Present')

            # Verify enrollments table was synced
            enrollment = db.execute("SELECT status FROM enrollments WHERE id = 1").fetchone()
            self.assertEqual(enrollment['status'], 'Present')

    def test_admin_mark_attendance_absent(self):
        """Test administrator marks attendance as Absent and updates DB."""
        self.login_admin()

        response = self.client.post('/admin/attendance/mark', data={
            'enrollment_id': '1',
            'status': 'Absent'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Attendance for participant marked as Absent', response.data)

        with app.app_context():
            db = get_db()
            att = db.execute("SELECT * FROM attendance WHERE enrollment_id = 1").fetchone()
            self.assertIsNotNone(att)
            self.assertEqual(att['status'], 'Absent')

    def test_prevent_duplicate_attendance_records(self):
        """Test that repeated attendance marking updates existing record without duplicate rows."""
        self.login_admin()

        # Mark Present first
        self.client.post('/admin/attendance/mark', data={'enrollment_id': '1', 'status': 'Present'})
        # Mark Absent second
        self.client.post('/admin/attendance/mark', data={'enrollment_id': '1', 'status': 'Absent'})

        with app.app_context():
            db = get_db()
            rows = db.execute(
                "SELECT * FROM attendance WHERE user_id = 2 AND workshop_id = 1"
            ).fetchall()
            # Assert exactly ONE attendance record exists
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['status'], 'Absent')

    # ----------------------------------------------------
    # 2. Feedback Module Tests
    # ----------------------------------------------------
    def test_unregistered_learner_blocked_from_submitting_feedback(self):
        """Test feedback submission is strictly restricted to registered participants."""
        self.login_learner()

        # User 2 is NOT registered for Workshop 3
        response = self.client.get('/feedback/3', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Access denied: You must be a registered participant', response.data)

        # POST attempt should also be blocked
        post_res = self.client.post('/feedback/3', data={
            'rating': '5',
            'comments': 'Great workshop!'
        }, follow_redirects=True)
        self.assertIn(b'Access denied', post_res.data)

        with app.app_context():
            db = get_db()
            fb = db.execute("SELECT * FROM feedback WHERE user_id = 2 AND workshop_id = 3").fetchone()
            self.assertIsNone(fb)

    def test_registered_learner_submits_valid_feedback(self):
        """Test registered participant submits rating (1-5) and written comments successfully."""
        self.login_learner()

        # User 2 is registered for Workshop 1 (Web Dev)
        response = self.client.post('/feedback/1', data={
            'rating': '5',
            'comments': 'Incredible workshop! The CSS flexbox exercises were super practical.'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your feedback has been recorded successfully', response.data)

        with app.app_context():
            db = get_db()
            fb = db.execute("SELECT * FROM feedback WHERE user_id = 2 AND workshop_id = 1").fetchone()
            self.assertIsNotNone(fb)
            self.assertEqual(fb['rating'], 5)
            self.assertEqual(fb['comments'], 'Incredible workshop! The CSS flexbox exercises were super practical.')

    def test_feedback_rating_bounds_validation(self):
        """Test server rejects ratings outside the 1 to 5 range."""
        self.login_learner()

        # Invalid rating 0
        res1 = self.client.post('/feedback/1', data={
            'rating': '0',
            'comments': 'Too low'
        }, follow_redirects=True)
        self.assertIn(b'valid star rating between 1 and 5', res1.data)

        # Invalid rating 6
        res2 = self.client.post('/feedback/1', data={
            'rating': '6',
            'comments': 'Too high'
        }, follow_redirects=True)
        self.assertIn(b'valid star rating between 1 and 5', res2.data)

    def test_feedback_displayed_to_administrators_and_moderation(self):
        """Test feedback is visible to administrators with moderation deletion action."""
        self.login_admin()

        # View feedback on admin dashboard
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Elena explained budgeting in such an approachable way', response.data)
        self.assertIn(b'Alex Johnson', response.data)

        # Admin deletes feedback 1
        delete_res = self.client.post('/admin/feedback/delete/1', follow_redirects=True)
        self.assertEqual(delete_res.status_code, 200)
        self.assertIn(b'Feedback review removed successfully', delete_res.data)

        with app.app_context():
            db = get_db()
            fb = db.execute("SELECT * FROM feedback WHERE id = 1").fetchone()
            self.assertIsNone(fb)


if __name__ == '__main__':
    unittest.main()
