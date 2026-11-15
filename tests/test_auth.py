"""
Automated Test Suite for User Authentication & Role-Based Authorization
Covers: Registration, Login, Logout, Password Hashing, Session State & Route Guards
Run with: python -m unittest tests/test_auth.py
"""

import os
import sys
import unittest
import tempfile
import sqlite3

# Add project root to sys.path so app can be imported cleanly
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from app import app, get_db, init_db
from werkzeug.security import check_password_hash


class AuthTestCase(unittest.TestCase):
    """Test case for User Registration, Login, Logout and RBAC."""

    def setUp(self):
        """Set up an isolated in-memory or temporary file SQLite database for each test."""
        self.db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        app.config['DATABASE'] = self.temp_db_path
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        # Initialize the fresh test database using project schema
        with app.app_context():
            schema_path = os.path.join(BASE_DIR, 'database', 'schema.sql')
            conn = sqlite3.connect(self.temp_db_path)
            with open(schema_path, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()

    def tearDown(self):
        """Clean up the temporary database after each test."""
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

    # ----------------------------------------------------
    # 1. Registration Tests
    # ----------------------------------------------------
    def test_registration_success(self):
        """Test successful registration of a new learner."""
        response = self.client.post('/register', data={
            'name': 'Test Learner',
            'email': 'newlearner@test.com',
            'phone': '555-9876',
            'password': 'securepassword123',
            'confirm_password': 'securepassword123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration successful', response.data)

        # Verify password is encrypted in database
        with app.app_context():
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE email = 'newlearner@test.com'").fetchone()
            self.assertIsNotNone(user)
            self.assertEqual(user['name'], 'Test Learner')
            self.assertEqual(user['role'], 'learner')
            # Verify password was hashed and never stored in plaintext
            self.assertNotEqual(user['password_hash'], 'securepassword123')
            self.assertTrue(check_password_hash(user['password_hash'], 'securepassword123'))

    def test_registration_duplicate_email(self):
        """Test duplicate email prevention."""
        # Attempt to register with the pre-seeded learner email
        response = self.client.post('/register', data={
            'name': 'Imposter Learner',
            'email': 'learner@workshop.com',  # Pre-existing in seed data
            'phone': '555-0000',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'An account with this email address already exists', response.data)

    def test_registration_password_mismatch(self):
        """Test registration rejects mismatching passwords."""
        response = self.client.post('/register', data={
            'name': 'Mismatch User',
            'email': 'mismatch@test.com',
            'password': 'password123',
            'confirm_password': 'differentpassword'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Passwords do not match', response.data)

    def test_registration_short_password(self):
        """Test registration rejects passwords shorter than 8 characters."""
        response = self.client.post('/register', data={
            'name': 'Short Pass',
            'email': 'short@test.com',
            'password': '123',
            'confirm_password': '123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'at least 8 characters long', response.data)

    def test_registration_invalid_email(self):
        """Test registration rejects malformed email addresses."""
        response = self.client.post('/register', data={
            'name': 'Bad Email',
            'email': 'not-an-email',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'valid email address', response.data)

    # ----------------------------------------------------
    # 2. Login & Session Tests
    # ----------------------------------------------------
    def test_login_learner_redirects_to_dashboard(self):
        """Test learner login succeeds and redirects to learner dashboard."""
        # Pre-register a fresh known learner
        self.client.post('/register', data={
            'name': 'Fresh Student',
            'email': 'fresh@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

        response = self.client.post('/login', data={
            'email': 'fresh@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome back, Fresh Student', response.data)
        # Check that dashboard page loaded
        self.assertIn(b'Your Registered Workshops', response.data)

        # Verify session is populated
        with self.client.session_transaction() as sess:
            self.assertIsNotNone(sess.get('user_id'))
            self.assertEqual(sess.get('role'), 'learner')
            self.assertEqual(sess.get('user_name'), 'Fresh Student')

    def test_login_invalid_password(self):
        """Test login fails with incorrect password."""
        response = self.client.post('/login', data={
            'email': 'learner@workshop.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email or password', response.data)

    def test_login_nonexistent_user(self):
        """Test login fails with unregistered email."""
        response = self.client.post('/login', data={
            'email': 'ghost@workshop.com',
            'password': 'somepassword'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email or password', response.data)

    # ----------------------------------------------------
    # 3. Role-Based Access Control (RBAC) Tests
    # ----------------------------------------------------
    def test_unauthenticated_user_blocked_from_dashboard(self):
        """Test anonymous user is redirected to login when trying to view dashboard."""
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please sign in to access this page', response.data)

    def test_unauthenticated_user_blocked_from_admin(self):
        """Test anonymous user is redirected to login when trying to view admin."""
        response = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please sign in with administrator credentials', response.data)

    def test_learner_blocked_from_admin_dashboard(self):
        """Test learner is strictly prohibited from accessing admin dashboard."""
        # Log in as a learner
        self.client.post('/register', data={
            'name': 'Regular Member',
            'email': 'regular@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.client.post('/login', data={'email': 'regular@test.com', 'password': 'password123'})

        # Attempt to access admin routes
        response = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Access restricted: Administrator rights required', response.data)

    # ----------------------------------------------------
    # 4. Logout Tests
    # ----------------------------------------------------
    def test_logout_clears_session(self):
        """Test logout clears session variables completely."""
        # Log in first
        self.client.post('/register', data={
            'name': 'Logout User',
            'email': 'logout@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.client.post('/login', data={'email': 'logout@test.com', 'password': 'password123'})

        # Now trigger logout
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You have been signed out safely', response.data)

        # Check session is completely empty
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('user_id'))
            self.assertIsNone(sess.get('role'))


if __name__ == '__main__':
    unittest.main()
