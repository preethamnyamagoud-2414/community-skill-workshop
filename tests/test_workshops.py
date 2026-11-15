"""
Automated Test Suite for Workshop Management Module
Covers: Catalog Browsing, Search & Filter, Workshop Details, Registration,
        Duplicate Prevention, Seat Capacity Guards, Admin CRUD & Attendee Rosters.
Run with: python -m unittest tests/test_workshops.py
"""

import os
import sys
import unittest
import tempfile
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from app import app, get_db


class WorkshopManagementTestCase(unittest.TestCase):
    """Test case for Workshop Catalog, Enrollment Engine, and Admin Management."""

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

    # Helper Methods
    def login_learner(self):
        """Logs in as the pre-seeded demo learner."""
        return self.client.post('/login', data={
            'email': 'learner@workshop.com',
            'password': 'learner123'
        }, follow_redirects=True)

    def login_admin(self):
        """Logs in as the pre-seeded administrator."""
        return self.client.post('/login', data={
            'email': 'admin@workshop.com',
            'password': 'admin123'
        }, follow_redirects=True)

    # ----------------------------------------------------
    # 1. Learner Workshop Discovery & Filtering
    # ----------------------------------------------------
    def test_view_all_workshops(self):
        """Test public viewing of workshop catalog."""
        response = self.client.get('/workshops')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Web Development Foundations', response.data)
        self.assertIn(b'Urban Gardening &amp; Composting', response.data)
        self.assertIn(b'Basic Woodworking &amp; Tool Safety', response.data)

    def test_search_workshops_by_name(self):
        """Test server-side search by title keyword."""
        response = self.client.get('/workshops?q=Woodworking')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Basic Woodworking', response.data)
        self.assertNotIn(b'Web Development Foundations', response.data)

    def test_filter_workshops_by_category(self):
        """Test filtering workshops by category."""
        response = self.client.get('/workshops?cat=Technology')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Web Development Foundations', response.data)
        self.assertNotIn(b'Urban Gardening', response.data)

    def test_view_workshop_details(self):
        """Test viewing detailed workshop page including trainer, venue, and seats."""
        response = self.client.get('/workshop/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Web Development Foundations', response.data)
        self.assertIn(b'Sarah Connor', response.data)
        self.assertIn(b'Computer Lab 2', response.data)
        self.assertIn(b'seats available', response.data)
        self.assertIn(b'WORKSHOP ID: #1', response.data)

    # ----------------------------------------------------
    # 2. Workshop Enrollment & Capacity Management
    # ----------------------------------------------------
    def test_learner_enroll_success(self):
        """Test learner successfully reserves a seat and available seats decrement."""
        self.login_learner()

        # Workshop 3 has 15 of 15 seats available initially
        with app.app_context():
            db = get_db()
            before_seats = db.execute("SELECT available_seats FROM workshops WHERE id = 3").fetchone()[0]
            self.assertEqual(before_seats, 15)

        response = self.client.post('/enroll/3', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Seat successfully reserved', response.data)

        # Check seats decremented by 1
        with app.app_context():
            db = get_db()
            after_seats = db.execute("SELECT available_seats FROM workshops WHERE id = 3").fetchone()[0]
            self.assertEqual(after_seats, 14)

            # Check enrollment record in DB
            enrollment = db.execute(
                "SELECT * FROM enrollments WHERE user_id = 2 AND workshop_id = 3"
            ).fetchone()
            self.assertIsNotNone(enrollment)
            self.assertEqual(enrollment['status'], 'confirmed')

    def test_duplicate_registration_prevented(self):
        """Test learner cannot enroll twice in the same workshop."""
        self.login_learner()

        # Workshop 1 is already enrolled by user 2 in seed data
        response = self.client.post('/enroll/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'already registered for this workshop', response.data)

        # Ensure available seats were not decremented again
        with app.app_context():
            db = get_db()
            seats = db.execute("SELECT available_seats FROM workshops WHERE id = 1").fetchone()[0]
            self.assertEqual(seats, 24)

    def test_full_seats_registration_prevented(self):
        """Test enrollment is blocked when available seats is 0."""
        self.login_learner()

        # Artificially set workshop 3 available seats to 0
        with app.app_context():
            db = get_db()
            db.execute("UPDATE workshops SET available_seats = 0 WHERE id = 3")
            db.commit()

        response = self.client.post('/enroll/3', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'fully booked', response.data)

    def test_learner_cancel_enrollment(self):
        """Test learner can cancel enrollment and seat is returned to inventory."""
        self.login_learner()

        # User 2 has active enrollment 1 on workshop 1
        with app.app_context():
            db = get_db()
            initial_seats = db.execute("SELECT available_seats FROM workshops WHERE id = 1").fetchone()[0]

        response = self.client.post('/cancel-enrollment/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'cancelled and your seat released', response.data)

        # Verify seat incremented
        with app.app_context():
            db = get_db()
            restored_seats = db.execute("SELECT available_seats FROM workshops WHERE id = 1").fetchone()[0]
            self.assertEqual(restored_seats, initial_seats + 1)

            # Verify status in database
            status = db.execute("SELECT status FROM enrollments WHERE id = 1").fetchone()[0]
            self.assertEqual(status, 'cancelled')

    # ----------------------------------------------------
    # 3. Administrator Workshop Management
    # ----------------------------------------------------
    def test_admin_add_workshop(self):
        """Test administrator can create a new workshop."""
        self.login_admin()

        response = self.client.post('/admin/workshop/add', data={
            'title': 'Robotics & Arduino Workshop',
            'category': 'Technology',
            'trainer_name': 'Dr. Alan Turing',
            'workshop_date': '2026-12-28',
            'workshop_time': '10:00 AM - 02:00 PM',
            'venue': 'Engineering Hall Lab 4',
            'total_seats': '30',
            'description': 'Hands-on robotics prototyping with microcontrollers.'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Workshop created and published successfully', response.data)

        with app.app_context():
            db = get_db()
            w = db.execute("SELECT * FROM workshops WHERE title = 'Robotics & Arduino Workshop'").fetchone()
            self.assertIsNotNone(w)
            self.assertEqual(w['trainer_name'], 'Dr. Alan Turing')
            self.assertEqual(w['total_seats'], 30)
            self.assertEqual(w['available_seats'], 30)
            self.assertEqual(w['status'], 'upcoming')

    def test_admin_edit_workshop(self):
        """Test administrator can edit workshop logistics and recalculate available seats."""
        self.login_admin()

        response = self.client.post('/admin/workshop/edit/1', data={
            'title': 'Advanced Web Development & APIs',
            'category': 'Technology',
            'trainer_name': 'Sarah Connor',
            'workshop_date': '2026-12-10',
            'workshop_time': '02:00 PM - 05:00 PM',
            'venue': 'Innovation Center Bay 1',
            'total_seats': '40',
            'status': 'upcoming',
            'description': 'Expanded curriculum with backend APIs and database connectivity.'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Workshop details updated successfully', response.data)

        with app.app_context():
            db = get_db()
            w = db.execute("SELECT * FROM workshops WHERE id = 1").fetchone()
            self.assertEqual(w['title'], 'Advanced Web Development & APIs')
            self.assertEqual(w['total_seats'], 40)
            # 1 confirmed enrollment exists for workshop 1, so available = 40 - 1 = 39
            self.assertEqual(w['available_seats'], 39)

    def test_admin_delete_workshop(self):
        """Test administrator can delete a workshop and clean up database."""
        self.login_admin()

        response = self.client.post('/admin/workshop/delete/3', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Workshop deleted', response.data)

        with app.app_context():
            db = get_db()
            w = db.execute("SELECT * FROM workshops WHERE id = 3").fetchone()
            self.assertIsNone(w)

    def test_admin_view_roster_and_mark_attendance(self):
        """Test administrator can view attendee roster and mark participant as attended."""
        self.login_admin()

        # View participants page
        response = self.client.get('/admin/participants?workshop_id=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Alex Johnson', response.data)
        self.assertIn(b'Web Development Foundations', response.data)

        # Mark attendance for enrollment 1
        mark_res = self.client.post('/admin/mark-attended/1', follow_redirects=True)
        self.assertEqual(mark_res.status_code, 200)
        self.assertIn(b'Participant status updated to Attended', mark_res.data)

        with app.app_context():
            db = get_db()
            status = db.execute("SELECT status FROM enrollments WHERE id = 1").fetchone()[0]
            self.assertEqual(status, 'attended')


if __name__ == '__main__':
    unittest.main()
