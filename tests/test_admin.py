"""
Automated Test Suite for Administrator Dashboard & RBAC Security
Covers: Route Protection, Live Metrics, Workshop Inventory,
        CRUD Operations, Attendee Rosters, and Feedback Moderation.
Run with: python -m unittest tests/test_admin.py
"""

import os
import sys
import unittest
import tempfile
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from app import app, get_db


class AdminDashboardTestCase(unittest.TestCase):
    """Test case for Administrator Dashboard analytics, CRUD, and strict route security."""

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

    def login_admin(self):
        """Logs in as the pre-seeded administrator."""
        return self.client.post('/login', data={
            'email': 'admin@workshop.com',
            'password': 'admin123'
        }, follow_redirects=True)

    def login_learner(self):
        """Logs in as the pre-seeded learner."""
        return self.client.post('/login', data={
            'email': 'learner@workshop.com',
            'password': 'learner123'
        }, follow_redirects=True)

    # ----------------------------------------------------
    # 1. Backend Route Protection & RBAC Tests
    # ----------------------------------------------------
    def test_anonymous_user_blocked_from_all_admin_routes(self):
        """Test anonymous visitors cannot access any admin endpoint."""
        admin_urls = [
            '/admin',
            '/admin/dashboard',
            '/admin/workshop/add',
            '/admin/workshop/edit/1',
            '/admin/participants',
            '/admin/feedback'
        ]
        for url in admin_urls:
            response = self.client.get(url, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'administrator credentials', response.data)

    def test_learner_blocked_from_all_admin_routes(self):
        """Test authenticated learners are forbidden from accessing admin endpoints."""
        self.login_learner()

        admin_urls = [
            '/admin',
            '/admin/dashboard',
            '/admin/workshop/add',
            '/admin/workshop/edit/1',
            '/admin/participants',
            '/admin/feedback'
        ]
        for url in admin_urls:
            response = self.client.get(url, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Access restricted: Administrator rights required', response.data)

    # ----------------------------------------------------
    # 2. Live Metrics & SQLite Analytics
    # ----------------------------------------------------
    def test_admin_dashboard_metrics_render(self):
        """Test admin dashboard renders accurate database metrics."""
        self.login_admin()
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)

        # Verify summary statistics labels
        self.assertIn(b'Total Learners', response.data)
        self.assertIn(b'Total Workshops', response.data)
        self.assertIn(b'Total Registrations', response.data)
        self.assertIn(b'Learner Reviews', response.data)

        # Verify initial database counts: 1 learner, 4 workshops, 2 registrations
        with app.app_context():
            db = get_db()
            learners_count = db.execute("SELECT COUNT(*) FROM users WHERE role = 'learner'").fetchone()[0]
            workshops_count = db.execute("SELECT COUNT(*) FROM workshops").fetchone()[0]
            self.assertEqual(learners_count, 1)
            self.assertEqual(workshops_count, 4)

    # ----------------------------------------------------
    # 3. Workshop Inventory & Search
    # ----------------------------------------------------
    def test_admin_workshop_table_renders(self):
        """Test admin workshop management table lists all workshops and schedules."""
        self.login_admin()
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)

        self.assertIn(b'Web Development Foundations', response.data)
        self.assertIn(b'Sarah Connor', response.data)
        self.assertIn(b'Urban Gardening &amp; Composting', response.data)
        self.assertIn(b'Basic Woodworking &amp; Tool Safety', response.data)

    # ----------------------------------------------------
    # 4. CRUD Operations & Feedback Moderation
    # ----------------------------------------------------
    def test_admin_create_edit_delete_lifecycle(self):
        """Test full workshop lifecycle through admin CRUD routes."""
        self.login_admin()

        # 1. Create Workshop
        create_res = self.client.post('/admin/workshop/add', data={
            'title': 'AI & Prompt Engineering Basics',
            'category': 'Technology',
            'trainer_name': 'Dr. Ada Lovelace',
            'workshop_date': '2026-12-29',
            'workshop_time': '11:00 AM - 02:00 PM',
            'venue': 'Tech Innovation Hub',
            'total_seats': '35',
            'description': 'Master prompting and generative AI workflows.'
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)
        self.assertIn(b'Workshop created and published successfully', create_res.data)

        # Check in DB
        with app.app_context():
            db = get_db()
            created = db.execute("SELECT * FROM workshops WHERE title = 'AI & Prompt Engineering Basics'").fetchone()
            self.assertIsNotNone(created)
            workshop_id = created['id']

        # 2. Edit Workshop
        edit_res = self.client.post(f'/admin/workshop/edit/{workshop_id}', data={
            'title': 'Applied Generative AI & Automation',
            'category': 'Technology',
            'trainer_name': 'Dr. Ada Lovelace',
            'workshop_date': '2026-12-30',
            'workshop_time': '10:00 AM - 01:00 PM',
            'venue': 'Tech Innovation Hub Room 2',
            'total_seats': '45',
            'status': 'upcoming',
            'description': 'Updated curriculum covering practical workflows.'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)
        self.assertIn(b'Workshop details updated successfully', edit_res.data)

        with app.app_context():
            db = get_db()
            updated = db.execute("SELECT * FROM workshops WHERE id = ?", (workshop_id,)).fetchone()
            self.assertEqual(updated['title'], 'Applied Generative AI & Automation')
            self.assertEqual(updated['total_seats'], 45)

        # 3. Delete Workshop
        delete_res = self.client.post(f'/admin/workshop/delete/{workshop_id}', follow_redirects=True)
        self.assertEqual(delete_res.status_code, 200)
        self.assertIn(b'Workshop deleted', delete_res.data)

        with app.app_context():
            db = get_db()
            deleted = db.execute("SELECT * FROM workshops WHERE id = ?", (workshop_id,)).fetchone()
            self.assertIsNone(deleted)

    def test_admin_feedback_moderation(self):
        """Test administrator can delete inappropriate learner reviews."""
        self.login_admin()

        # Seed data has 1 feedback (id 1)
        with app.app_context():
            db = get_db()
            fb = db.execute("SELECT * FROM feedback WHERE id = 1").fetchone()
            self.assertIsNotNone(fb)

        response = self.client.post('/admin/feedback/delete/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Feedback review removed successfully', response.data)

        with app.app_context():
            db = get_db()
            fb_after = db.execute("SELECT * FROM feedback WHERE id = 1").fetchone()
            self.assertIsNone(fb_after)


if __name__ == '__main__':
    unittest.main()
