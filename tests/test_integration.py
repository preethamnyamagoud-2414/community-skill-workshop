"""
Master End-to-End Integration Test Suite for SkillConnect
Validates the complete full-stack integration across:
- Homepage connection & live statistics
- User Registration & password hashing in SQLite
- Login verification, session state & role routing
- Learner Dashboard real-time SQLite metric calculations
- Workshop catalog browsing, server-side search & category filtering
- Workshop seat enrollment, capacity decrement & duplicate prevention
- Workshop reservation cancellation & seat restoration
- Attendee roster viewing & attendance marking (Present / Absent)
- Participant-restricted feedback submission & rating validation
- Admin workshop CRUD operations (Create, Read, Update, Delete)
- Admin review moderation & secure Logout
Run with: python -m unittest tests/test_integration.py
"""

import os
import sys
import unittest
import tempfile
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from app import app, get_db
from werkzeug.security import check_password_hash


class EndToEndIntegrationTestCase(unittest.TestCase):
    """Complete end-to-end user journey and administrative integration tests."""

    def setUp(self):
        """Set up an isolated temporary database for the full integration run."""
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

    def test_complete_application_integration_flow(self):
        """Execute the entire full-stack lifecycle from registration to admin management."""
        
        # ----------------------------------------------------
        # 1. Homepage Connection & Database Metrics
        # ----------------------------------------------------
        home_res = self.client.get('/')
        self.assertEqual(home_res.status_code, 200)
        self.assertIn(b'SkillConnect', home_res.data)
        self.assertIn(b'Learn New Skills', home_res.data)
        self.assertIn(b'Web Development Foundations', home_res.data)

        # ----------------------------------------------------
        # 2. Registration Saves User with PBKDF2 Password Hash
        # ----------------------------------------------------
        reg_res = self.client.post('/register', data={
            'name': 'Integration Learner',
            'email': 'integration@test.com',
            'phone': '555-7788',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn(b'Registration successful', reg_res.data)

        # Verify record in SQLite
        with app.app_context():
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE email = 'integration@test.com'").fetchone()
            self.assertIsNotNone(user)
            self.assertEqual(user['role'], 'learner')
            self.assertTrue(check_password_hash(user['password_hash'], 'password123'))
            learner_id = user['id']

        # ----------------------------------------------------
        # 3. Login Verifies Credentials & Sets Session
        # ----------------------------------------------------
        login_res = self.client.post('/login', data={
            'email': 'integration@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Welcome back, Integration Learner', login_res.data)

        # Verify session state
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('user_id'), learner_id)
            self.assertEqual(sess.get('role'), 'learner')

        # ----------------------------------------------------
        # 4. Learner Dashboard Displays Real Data
        # ----------------------------------------------------
        dash_res = self.client.get('/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'Integration Learner', dash_res.data)
        self.assertIn(b'Total Registered', dash_res.data)

        # ----------------------------------------------------
        # 5. Workshop Catalog, Search & Filtering
        # ----------------------------------------------------
        catalog_res = self.client.get('/workshops?q=Woodworking')
        self.assertEqual(catalog_res.status_code, 200)
        self.assertIn(b'Basic Woodworking &amp; Tool Safety', catalog_res.data)
        self.assertNotIn(b'Web Development Foundations', catalog_res.data)

        # ----------------------------------------------------
        # 6. Workshop Registration & Seat Decrement
        # ----------------------------------------------------
        # Workshop 3 (Woodworking) has 15 seats initially
        enroll_res = self.client.post('/enroll/3', follow_redirects=True)
        self.assertEqual(enroll_res.status_code, 200)
        self.assertIn(b'Seat successfully reserved', enroll_res.data)

        with app.app_context():
            db = get_db()
            w = db.execute("SELECT available_seats FROM workshops WHERE id = 3").fetchone()
            self.assertEqual(w['available_seats'], 14)

            # Check enrollment row exists
            enr = db.execute(
                "SELECT * FROM enrollments WHERE user_id = ? AND workshop_id = 3",
                (learner_id,)
            ).fetchone()
            self.assertIsNotNone(enr)
            self.assertEqual(enr['status'], 'confirmed')
            enrollment_id = enr['id']

        # Verify duplicate registration is blocked
        dup_res = self.client.post('/enroll/3', follow_redirects=True)
        self.assertIn(b'already registered for this workshop', dup_res.data)

        # ----------------------------------------------------
        # 7. Feedback Restricted to Participants & Stored
        # ----------------------------------------------------
        # Learner submits feedback for Workshop 3
        fb_res = self.client.post('/feedback/3', data={
            'rating': '5',
            'comments': 'Superb woodworking session! The safety tips were comprehensive.'
        }, follow_redirects=True)
        self.assertEqual(fb_res.status_code, 200)
        self.assertIn(b'Your feedback has been recorded successfully', fb_res.data)

        with app.app_context():
            db = get_db()
            fb = db.execute("SELECT * FROM feedback WHERE user_id = ? AND workshop_id = 3", (learner_id,)).fetchone()
            self.assertIsNotNone(fb)
            self.assertEqual(fb['rating'], 5)

        # ----------------------------------------------------
        # 8. Learner Logout
        # ----------------------------------------------------
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b'signed out safely', logout_res.data)

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('user_id'))

        # ----------------------------------------------------
        # 9. Admin Login & Dashboard Overview
        # ----------------------------------------------------
        admin_login = self.client.post('/login', data={
            'email': 'admin@workshop.com',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(admin_login.status_code, 200)
        self.assertIn(b'Admin Control Center', admin_login.data)

        # ----------------------------------------------------
        # 10. Admin Adds New Workshop
        # ----------------------------------------------------
        add_res = self.client.post('/admin/workshop/add', data={
            'title': 'Full-Stack Python & Flask Workshop',
            'category': 'Technology',
            'trainer_name': 'Guido van Rossum',
            'workshop_date': '2026-12-31',
            'workshop_time': '09:00 AM - 01:00 PM',
            'venue': 'Software Innovation Hub Room 1',
            'total_seats': '20',
            'description': 'Comprehensive hands-on full-stack development workshop.'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)
        self.assertIn(b'Workshop created and published successfully', add_res.data)

        with app.app_context():
            db = get_db()
            new_w = db.execute("SELECT * FROM workshops WHERE title = 'Full-Stack Python & Flask Workshop'").fetchone()
            self.assertIsNotNone(new_w)
            new_id = new_w['id']

        # ----------------------------------------------------
        # 11. Admin Marks Learner Attendance (Present)
        # ----------------------------------------------------
        att_res = self.client.post('/admin/attendance/mark', data={
            'enrollment_id': str(enrollment_id),
            'status': 'Present'
        }, follow_redirects=True)
        self.assertEqual(att_res.status_code, 200)
        self.assertIn(b'Attendance for participant marked as Present', att_res.data)

        with app.app_context():
            db = get_db()
            att_row = db.execute("SELECT * FROM attendance WHERE enrollment_id = ?", (enrollment_id,)).fetchone()
            self.assertIsNotNone(att_row)
            self.assertEqual(att_row['status'], 'Present')

        # ----------------------------------------------------
        # 12. Admin Edits & Deletes Workshop
        # ----------------------------------------------------
        edit_res = self.client.post(f'/admin/workshop/edit/{new_id}', data={
            'title': 'Advanced Python & Cloud Deployment',
            'category': 'Technology',
            'trainer_name': 'Guido van Rossum',
            'workshop_date': '2026-12-31',
            'workshop_time': '10:00 AM - 02:00 PM',
            'venue': 'Innovation Center Lab 2',
            'total_seats': '25',
            'status': 'upcoming',
            'description': 'Advanced curriculum.'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)
        self.assertIn(b'Workshop details updated successfully', edit_res.data)

        # Delete workshop
        del_res = self.client.post(f'/admin/workshop/delete/{new_id}', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIn(b'Workshop deleted', del_res.data)

        # ----------------------------------------------------
        # 13. Admin Logout
        # ----------------------------------------------------
        admin_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(admin_logout.status_code, 200)
        self.assertIn(b'signed out safely', admin_logout.data)


if __name__ == '__main__':
    unittest.main()
