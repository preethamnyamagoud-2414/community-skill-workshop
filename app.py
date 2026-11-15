"""
Community Skill-Building Workshop Platform
Backend Application Entry Point
Built with Python Flask & SQLite
"""

import os
import re
import sqlite3
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def is_valid_email(email_str: str) -> bool:
    """Validates email format using standard RFC-compatible regex."""
    return bool(email_str and EMAIL_REGEX.match(email_str))

# ----------------------------------------------------
# Application Setup & Path Configuration
# ----------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DATABASE_PATH = os.path.join(INSTANCE_DIR, 'workshop.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'database', 'schema.sql')

# Ensure instance directory exists
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.config['SECRET_KEY'] = 'community-skill-workshop-secret-key-2026'
app.config['DATABASE'] = DATABASE_PATH


# ----------------------------------------------------
# Database Helpers
# ----------------------------------------------------
def get_db():
    """Opens a new database connection if not already open in current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Closes the database connection at the end of each request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initializes SQLite tables and seed data from schema.sql."""
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()
    print("Database initialized successfully with sample seed data.")


# Auto-initialize database on first run if database file is missing or empty
if not os.path.exists(DATABASE_PATH) or os.path.getsize(DATABASE_PATH) == 0:
    init_db()


# ----------------------------------------------------
# Authentication Decorators
# ----------------------------------------------------
def login_required(f):
    """Ensures user is logged in before accessing the route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Ensures user is logged in as an Administrator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please sign in with administrator credentials.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash('Access restricted: Administrator rights required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ----------------------------------------------------
# Public & Learner Routes
# ----------------------------------------------------
@app.route('/')
def index():
    """Landing Page: Hero, statistics, and featured upcoming workshops."""
    db = get_db()
    featured = db.execute(
        "SELECT * FROM workshops WHERE status = 'upcoming' ORDER BY workshop_date ASC LIMIT 3"
    ).fetchall()

    total_workshops = db.execute("SELECT COUNT(*) FROM workshops").fetchone()[0]
    total_learners = db.execute("SELECT COUNT(*) FROM users WHERE role = 'learner'").fetchone()[0]

    return render_template(
        'index.html',
        featured_workshops=featured,
        total_workshops=total_workshops,
        total_learners=total_learners
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Learner Account Registration with server-side validation and password hashing."""
    if session.get('user_id'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server-side validation
        if not name or len(name) < 2:
            flash('Full name is required and must be at least 2 characters long.', 'danger')
            return render_template('register.html', name=name, email=email, phone=phone)

        if not email or not is_valid_email(email):
            flash('Please provide a valid email address (e.g., name@example.com).', 'danger')
            return render_template('register.html', name=name, email=email, phone=phone)

        if not password or len(password) < 6:
            flash('Password is required and must be at least 6 characters long.', 'danger')
            return render_template('register.html', name=name, email=email, phone=phone)

        if password != confirm_password:
            flash('Passwords do not match. Please verify and re-enter.', 'danger')
            return render_template('register.html', name=name, email=email, phone=phone)

        db = get_db()
        # Parameterized query to prevent duplicate accounts and SQL injection
        existing_user = db.execute(
            "SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (email,)
        ).fetchone()

        if existing_user:
            flash('An account with this email address already exists. Please sign in.', 'warning')
            return render_template('register.html', name=name, email=email, phone=phone)

        # Secure password hashing using Werkzeug
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        db.execute(
            """INSERT INTO users (name, email, password_hash, role, phone) 
               VALUES (?, ?, ?, 'learner', ?)""",
            (name, email, hashed_password, phone or None)
        )
        db.commit()

        flash('Registration successful! You can now log in with your credentials.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User & Administrator Sign In with role-based routing and session management."""
    if session.get('user_id'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    next_page = request.args.get('next', '')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_page = request.form.get('next', '').strip()

        # Input presence validation
        if not email or not password:
            flash('Please enter both your email address and password.', 'danger')
            return render_template('login.html', email=email, next=next_page)

        db = get_db()
        # Parameterized SQL query
        user = db.execute(
            "SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)
        ).fetchone()

        # Verify password securely against stored hash
        if user and check_password_hash(user['password_hash'], password):
            # Regenerate/clear old session to prevent session fixation attacks
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['role'] = user['role']
            session.permanent = True

            flash(f'Welcome back, {user["name"]}! You are signed in as {user["role"].capitalize()}.', 'success')

            # Safe open-redirect validation for 'next' parameter
            if next_page and next_page.startswith('/') and not next_page.startswith('//'):
                return redirect(next_page)

            # Role-based dashboard routing
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please verify your credentials and try again.', 'danger')
            return render_template('login.html', email=email, next=next_page)

    return render_template('login.html', next=next_page)


@app.route('/logout')
def logout():
    """Securely terminates the active user session and redirects to the login page."""
    user_name = session.get('user_name', '')
    session.clear()
    if user_name:
        flash(f'Goodbye, {user_name}. You have been signed out safely.', 'info')
    else:
        flash('You have been signed out safely.', 'info')
    return redirect(url_for('login'))


@app.route('/workshops')
def workshops():
    """Catalog of all workshops with server-side query filtering & client-side live search."""
    db = get_db()
    
    # URL Query Parameters (Search & Category Filter)
    search_query = request.args.get('q', '').strip()
    selected_cat = request.args.get('cat', '').strip()

    sql = "SELECT * FROM workshops WHERE 1=1"
    params = []

    if search_query:
        sql += " AND (LOWER(title) LIKE ? OR LOWER(trainer_name) LIKE ? OR LOWER(description) LIKE ?)"
        wildcard = f"%{search_query.lower()}%"
        params.extend([wildcard, wildcard, wildcard])

    if selected_cat and selected_cat.lower() != 'all':
        sql += " AND LOWER(category) = LOWER(?)"
        params.append(selected_cat)

    sql += " ORDER BY workshop_date ASC"
    all_workshops = db.execute(sql, params).fetchall()

    categories = [
        row[0] for row in db.execute(
            "SELECT DISTINCT category FROM workshops ORDER BY category ASC"
        ).fetchall()
    ]

    # If logged in as learner, fetch IDs of workshops already enrolled in
    user_enrolled_ids = []
    if session.get('user_id') and session.get('role') == 'learner':
        rows = db.execute(
            "SELECT workshop_id FROM enrollments WHERE user_id = ? AND status != 'cancelled'",
            (session['user_id'],)
        ).fetchall()
        user_enrolled_ids = [r['workshop_id'] for r in rows]

    return render_template(
        'workshops.html',
        workshops=all_workshops,
        categories=categories,
        search_query=search_query,
        selected_category=selected_cat,
        user_enrolled_ids=user_enrolled_ids
    )


@app.route('/workshop/<int:workshop_id>')
def workshop_details(workshop_id):
    """Detailed view for a specific workshop, including trainer bio and attendee reviews."""
    db = get_db()
    workshop = db.execute("SELECT * FROM workshops WHERE id = ?", (workshop_id,)).fetchone()
    if not workshop:
        abort(404)

    is_enrolled = False
    enrollment_id = None
    if session.get('user_id'):
        enrollment = db.execute(
            "SELECT id, status FROM enrollments WHERE user_id = ? AND workshop_id = ? AND status != 'cancelled'",
            (session['user_id'], workshop_id)
        ).fetchone()
        if enrollment:
            is_enrolled = True
            enrollment_id = enrollment['id']

    # Retrieve attendee reviews
    feedback_list = db.execute(
        """SELECT f.*, u.name as user_name 
           FROM feedback f 
           JOIN users u ON f.user_id = u.id 
           WHERE f.workshop_id = ? 
           ORDER BY f.created_at DESC""",
        (workshop_id,)
    ).fetchall()

    return render_template(
        'workshop_details.html',
        workshop=workshop,
        is_enrolled=is_enrolled,
        enrollment_id=enrollment_id,
        feedback_list=feedback_list
    )


@app.route('/enroll/<int:workshop_id>', methods=['POST'])
@login_required
def enroll(workshop_id):
    """Enrolls a learner in a workshop and decrements available seats atomically."""
    if session.get('role') == 'admin':
        flash('Administrators cannot enroll as participants.', 'warning')
        return redirect(url_for('workshop_details', workshop_id=workshop_id))

    user_id = session['user_id']
    db = get_db()

    # Check workshop status and seats
    workshop = db.execute("SELECT * FROM workshops WHERE id = ?", (workshop_id,)).fetchone()
    if not workshop:
        flash('Workshop not found.', 'danger')
        return redirect(url_for('workshops'))

    if workshop['status'] != 'upcoming':
        flash('This workshop is no longer accepting enrollments.', 'warning')
        return redirect(url_for('workshop_details', workshop_id=workshop_id))

    if workshop['available_seats'] <= 0:
        flash('Sorry, this workshop is fully booked.', 'danger')
        return redirect(url_for('workshop_details', workshop_id=workshop_id))

    # Check existing enrollment
    existing = db.execute(
        "SELECT * FROM enrollments WHERE user_id = ? AND workshop_id = ?",
        (user_id, workshop_id)
    ).fetchone()

    if existing:
        if existing['status'] == 'confirmed':
            flash('You are already registered for this workshop.', 'info')
            return redirect(url_for('workshop_details', workshop_id=workshop_id))
        else:
            # Re-activate previous cancelled enrollment
            db.execute("UPDATE enrollments SET status = 'confirmed' WHERE id = ?", (existing['id'],))
            db.execute("UPDATE workshops SET available_seats = available_seats - 1 WHERE id = ?", (workshop_id,))
            db.commit()
            flash('Your registration has been reactivated successfully!', 'success')
            return redirect(url_for('my_workshops'))

    # New enrollment
    db.execute(
        "INSERT INTO enrollments (user_id, workshop_id, status) VALUES (?, ?, 'confirmed')",
        (user_id, workshop_id)
    )
    db.execute("UPDATE workshops SET available_seats = available_seats - 1 WHERE id = ?", (workshop_id,))
    db.commit()

    flash('Seat successfully reserved! We look forward to seeing you there.', 'success')
    return redirect(url_for('my_workshops'))


@app.route('/cancel-enrollment/<int:enrollment_id>', methods=['POST'])
@login_required
def cancel_enrollment(enrollment_id):
    """Allows a learner to cancel an active enrollment and restore the seat."""
    db = get_db()
    enrollment = db.execute(
        "SELECT * FROM enrollments WHERE id = ? AND user_id = ?",
        (enrollment_id, session['user_id'])
    ).fetchone()

    if not enrollment:
        flash('Enrollment record not found.', 'danger')
        return redirect(url_for('my_workshops'))

    if enrollment['status'] == 'confirmed':
        db.execute("UPDATE enrollments SET status = 'cancelled' WHERE id = ?", (enrollment_id,))
        db.execute(
            "UPDATE workshops SET available_seats = available_seats + 1 WHERE id = ?",
            (enrollment['workshop_id'],)
        )
        db.commit()
        flash('Your workshop reservation has been cancelled and your seat released.', 'info')
    else:
        flash('This registration is not active.', 'warning')

    return redirect(url_for('my_workshops'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Learner personal summary dashboard with real-time SQLite data and profile analytics."""
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))

    user_id = session['user_id']
    db = get_db()
    
    # 1. Fetch complete user profile information
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    # 2. Fetch full registration history with workshop logistics
    enrollments = db.execute(
        """SELECT e.id as enrollment_id, e.status, e.enrollment_date,
                  w.id as workshop_id, w.title, w.category, w.trainer_name,
                  w.workshop_date, w.workshop_time, w.venue, w.status as workshop_status,
                  w.available_seats, w.total_seats
           FROM enrollments e
           JOIN workshops w ON e.workshop_id = w.id
           WHERE e.user_id = ?
           ORDER BY w.workshop_date ASC""",
        (user_id,)
    ).fetchall()

    # 3. Categorize registrations for clean dashboard tab views
    upcoming_workshops = [e for e in enrollments if e['status'] == 'confirmed']
    completed_workshops = [e for e in enrollments if e['status'] in ('attended', 'Present')]
    cancelled_workshops = [e for e in enrollments if e['status'] == 'cancelled']

    # 4. Compute real statistics directly from database records
    total_registered = len(upcoming_workshops) + len(completed_workshops)
    upcoming_count = len(upcoming_workshops)
    completed_count = len(completed_workshops)
    feedback_count = db.execute(
        "SELECT COUNT(*) FROM feedback WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    # 5. Fetch recommended learning opportunities not yet enrolled by this learner
    recommended = db.execute(
        """SELECT * FROM workshops 
           WHERE status = 'upcoming' AND available_seats > 0
           AND id NOT IN (
               SELECT workshop_id FROM enrollments 
               WHERE user_id = ? AND status != 'cancelled'
           )
           ORDER BY workshop_date ASC LIMIT 3""",
        (user_id,)
    ).fetchall()

    return render_template(
        'dashboard.html',
        user=user,
        enrollments=enrollments,
        upcoming_workshops=upcoming_workshops,
        completed_workshops=completed_workshops,
        cancelled_workshops=cancelled_workshops,
        total_registered=total_registered,
        upcoming_count=upcoming_count,
        completed_count=completed_count,
        feedback_count=feedback_count,
        recommended_workshops=recommended
    )


@app.route('/my-workshops')
@login_required
def my_workshops():
    """Full table view of user's registered workshops."""
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))

    user_id = session['user_id']
    db = get_db()
    registered = db.execute(
        """SELECT e.id as enrollment_id, e.status, e.enrollment_date,
                  w.id as workshop_id, w.title, w.category, w.trainer_name,
                  w.workshop_date, w.workshop_time, w.venue, w.status as workshop_status
           FROM enrollments e
           JOIN workshops w ON e.workshop_id = w.id
           WHERE e.user_id = ?
           ORDER BY w.workshop_date ASC""",
        (user_id,)
    ).fetchall()

    return render_template('my_workshops.html', my_workshops=registered)


@app.route('/feedback', methods=['GET'])
@app.route('/feedback/<int:workshop_id>', methods=['GET', 'POST'])
@login_required
def feedback_page(workshop_id=None):
    """View community reviews or submit a review for an enrolled workshop (restricted to participants)."""
    db = get_db()
    workshop = None
    existing_feedback = None

    if workshop_id:
        workshop = db.execute("SELECT * FROM workshops WHERE id = ?", (workshop_id,)).fetchone()
        if not workshop:
            abort(404)

        # Security check: Restrict feedback submission to registered participants only
        enrollment = db.execute(
            """SELECT * FROM enrollments 
               WHERE user_id = ? AND workshop_id = ? AND status != 'cancelled'""",
            (session['user_id'], workshop_id)
        ).fetchone()

        if not enrollment:
            flash('Access denied: You must be a registered participant of this workshop to submit feedback.', 'danger')
            return redirect(url_for('workshop_details', workshop_id=workshop_id))

        # Check existing feedback for pre-filling
        existing_feedback = db.execute(
            "SELECT * FROM feedback WHERE user_id = ? AND workshop_id = ?",
            (session['user_id'], workshop_id)
        ).fetchone()

    if request.method == 'POST' and workshop_id:
        rating = request.form.get('rating', type=int)
        comments = request.form.get('comments', '').strip()

        # Backend validations
        if not rating or rating < 1 or rating > 5:
            flash('Please select a valid star rating between 1 and 5.', 'danger')
            return redirect(url_for('feedback_page', workshop_id=workshop_id))

        if not comments or len(comments) < 3:
            flash('Please write a constructive comment (at least 3 characters).', 'danger')
            return redirect(url_for('feedback_page', workshop_id=workshop_id))

        # Parameterized upsert preventing duplicate feedback
        db.execute(
            """INSERT INTO feedback (user_id, workshop_id, rating, comments)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, workshop_id) DO UPDATE SET
               rating = excluded.rating,
               comments = excluded.comments,
               created_at = CURRENT_TIMESTAMP""",
            (session['user_id'], workshop_id, rating, comments)
        )
        db.commit()

        flash('Thank you! Your feedback has been recorded successfully.', 'success')
        return redirect(url_for('workshop_details', workshop_id=workshop_id))

    all_feedback = db.execute(
        """SELECT f.*, u.name as user_name, w.title as workshop_title
           FROM feedback f
           JOIN users u ON f.user_id = u.id
           JOIN workshops w ON f.workshop_id = w.id
           ORDER BY f.created_at DESC"""
    ).fetchall()

    return render_template(
        'feedback.html', 
        workshop=workshop, 
        existing_feedback=existing_feedback,
        all_feedback=all_feedback
    )


# ----------------------------------------------------
# Administrator Routes
# ----------------------------------------------------
@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Administrator Overview: live SQLite metrics, workshop inventory, and learner feedback."""
    db = get_db()
    admin_user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    workshops_list = db.execute("SELECT * FROM workshops ORDER BY workshop_date DESC").fetchall()

    total_workshops = len(workshops_list)
    total_learners = db.execute("SELECT COUNT(*) FROM users WHERE role = 'learner'").fetchone()[0]
    total_registrations = db.execute("SELECT COUNT(*) FROM enrollments WHERE status != 'cancelled'").fetchone()[0]
    total_attended = db.execute("SELECT COUNT(*) FROM enrollments WHERE status = 'attended'").fetchone()[0]
    
    upcoming_count = sum(1 for w in workshops_list if w['status'] == 'upcoming')
    completed_count = sum(1 for w in workshops_list if w['status'] == 'completed')
    cancelled_count = sum(1 for w in workshops_list if w['status'] == 'cancelled')

    # Fetch learner feedback for reviews section
    all_feedback = db.execute(
        """SELECT f.*, u.name as user_name, u.email as user_email, w.title as workshop_title
           FROM feedback f
           JOIN users u ON f.user_id = u.id
           JOIN workshops w ON f.workshop_id = w.id
           ORDER BY f.created_at DESC"""
    ).fetchall()
    total_feedbacks = len(all_feedback)

    return render_template(
        'admin_dashboard.html',
        admin_user=admin_user,
        workshops=workshops_list,
        total_workshops=total_workshops,
        total_learners=total_learners,
        total_registrations=total_registrations,
        total_attended=total_attended,
        upcoming_count=upcoming_count,
        completed_count=completed_count,
        cancelled_count=cancelled_count,
        total_feedbacks=total_feedbacks,
        all_feedback=all_feedback
    )


@app.route('/admin/feedback')
@admin_required
def admin_feedback():
    """Admin: Dedicated view to monitor and moderate all learner feedback reviews."""
    db = get_db()
    reviews = db.execute(
        """SELECT f.*, u.name as user_name, u.email as user_email, w.title as workshop_title, w.trainer_name
           FROM feedback f
           JOIN users u ON f.user_id = u.id
           JOIN workshops w ON f.workshop_id = w.id
           ORDER BY f.created_at DESC"""
    ).fetchall()
    return render_template('feedback.html', all_feedback=reviews, workshop=None)


@app.route('/admin/feedback/delete/<int:feedback_id>', methods=['POST'])
@admin_required
def delete_feedback(feedback_id):
    """Admin: Remove inappropriate review from database."""
    db = get_db()
    db.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
    db.commit()
    flash('Feedback review removed successfully.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/workshop/add', methods=['GET', 'POST'])
@admin_required
def add_workshop():
    """Admin: Publish a new workshop."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        trainer_name = request.form.get('trainer_name', '').strip()
        workshop_date = request.form.get('workshop_date', '').strip()
        workshop_time = request.form.get('workshop_time', '').strip()
        venue = request.form.get('venue', '').strip()
        total_seats = request.form.get('total_seats', type=int)
        description = request.form.get('description', '').strip()

        if not all([title, category, trainer_name, workshop_date, workshop_time, venue, total_seats, description]):
            flash('All workshop fields are required.', 'danger')
            return render_template('add_workshop.html')

        db = get_db()
        db.execute(
            """INSERT INTO workshops (title, description, category, trainer_name,
                                      workshop_date, workshop_time, venue, total_seats,
                                      available_seats, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'upcoming')""",
            (title, description, category, trainer_name, workshop_date, workshop_time, venue, total_seats, total_seats)
        )
        db.commit()

        flash('Workshop created and published successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_workshop.html')


@app.route('/admin/workshop/edit/<int:workshop_id>', methods=['GET', 'POST'])
@admin_required
def edit_workshop(workshop_id):
    """Admin: Edit an existing workshop."""
    db = get_db()
    workshop = db.execute("SELECT * FROM workshops WHERE id = ?", (workshop_id,)).fetchone()
    if not workshop:
        abort(404)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        trainer_name = request.form.get('trainer_name', '').strip()
        workshop_date = request.form.get('workshop_date', '').strip()
        workshop_time = request.form.get('workshop_time', '').strip()
        venue = request.form.get('venue', '').strip()
        total_seats = request.form.get('total_seats', type=int)
        status = request.form.get('status', 'upcoming')
        description = request.form.get('description', '').strip()

        # Recalculate available seats based on confirmed attendees
        enrolled_count = db.execute(
            "SELECT COUNT(*) FROM enrollments WHERE workshop_id = ? AND status = 'confirmed'",
            (workshop_id,)
        ).fetchone()[0]
        new_available = max(0, total_seats - enrolled_count)

        db.execute(
            """UPDATE workshops
               SET title = ?, category = ?, trainer_name = ?, workshop_date = ?,
                   workshop_time = ?, venue = ?, total_seats = ?, available_seats = ?,
                   status = ?, description = ?
               WHERE id = ?""",
            (title, category, trainer_name, workshop_date, workshop_time, venue,
             total_seats, new_available, status, description, workshop_id)
        )
        db.commit()

        flash('Workshop details updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_workshop.html', workshop=workshop)


@app.route('/admin/workshop/delete/<int:workshop_id>', methods=['POST'])
@admin_required
def delete_workshop(workshop_id):
    """Admin: Permanently delete a workshop."""
    db = get_db()
    db.execute("DELETE FROM workshops WHERE id = ?", (workshop_id,))
    db.commit()
    flash('Workshop deleted.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/participants')
@admin_required
def participants():
    """Admin: Attendee roster with optional per-workshop filter & attendance records."""
    db = get_db()
    workshop_filter_id = request.args.get('workshop_id', type=int)

    # Fetch workshops for dropdown selector
    all_workshops = db.execute("SELECT id, title FROM workshops ORDER BY title ASC").fetchall()

    sql = """SELECT e.id as enrollment_id, e.status as enrollment_status, e.enrollment_date,
                    u.id as user_id, u.name as user_name, u.email as user_email, u.phone as user_phone,
                    w.id as workshop_id, w.title as workshop_title, w.workshop_date, w.workshop_time,
                    a.status as attendance_status, a.marked_at as attendance_marked_at
             FROM enrollments e
             JOIN users u ON e.user_id = u.id
             JOIN workshops w ON e.workshop_id = w.id
             LEFT JOIN attendance a ON e.user_id = a.user_id AND e.workshop_id = a.workshop_id"""
    params = []

    if workshop_filter_id:
        sql += " WHERE w.id = ?"
        params.append(workshop_filter_id)

    sql += " ORDER BY e.enrollment_date DESC"
    roster = db.execute(sql, params).fetchall()

    return render_template(
        'participants.html',
        participants=roster,
        all_workshops=all_workshops,
        selected_workshop_id=workshop_filter_id
    )


@app.route('/admin/attendance/mark', methods=['POST'])
@admin_required
def mark_attendance():
    """Admin: Mark learner attendance as Present or Absent and prevent duplicate entries."""
    enrollment_id = request.form.get('enrollment_id', type=int)
    status = request.form.get('status', '').strip().capitalize()
    workshop_id = request.form.get('workshop_id', type=int)

    if not enrollment_id or status not in ['Present', 'Absent']:
        flash('Invalid attendance status provided. Must be Present or Absent.', 'danger')
        return redirect(url_for('participants', workshop_id=workshop_id if workshop_id else None))

    db = get_db()
    enrollment = db.execute(
        "SELECT * FROM enrollments WHERE id = ?", (enrollment_id,)
    ).fetchone()

    if not enrollment:
        flash('Enrollment record not found.', 'danger')
        return redirect(url_for('participants', workshop_id=workshop_id if workshop_id else None))

    # 1. Upsert attendance record with UNIQUE(user_id, workshop_id) preventing duplicates
    db.execute(
        """INSERT INTO attendance (enrollment_id, user_id, workshop_id, status)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, workshop_id) DO UPDATE SET
           status = excluded.status,
           marked_at = CURRENT_TIMESTAMP""",
        (enrollment_id, enrollment['user_id'], enrollment['workshop_id'], status)
    )

    # 2. Synchronize enrollment status
    db.execute("UPDATE enrollments SET status = ? WHERE id = ?", (status, enrollment_id))
    db.commit()

    flash(f"Attendance for participant marked as {status}.", 'success')
    return redirect(url_for('participants', workshop_id=workshop_id if workshop_id else None))


@app.route('/admin/mark-attended/<int:enrollment_id>', methods=['POST'])
@admin_required
def mark_attended(enrollment_id):
    """Backwards-compatible attendance marking endpoint."""
    db = get_db()
    enrollment = db.execute("SELECT * FROM enrollments WHERE id = ?", (enrollment_id,)).fetchone()
    if enrollment:
        db.execute(
            """INSERT INTO attendance (enrollment_id, user_id, workshop_id, status)
               VALUES (?, ?, ?, 'Present')
               ON CONFLICT(user_id, workshop_id) DO UPDATE SET
               status = 'Present',
               marked_at = CURRENT_TIMESTAMP""",
            (enrollment_id, enrollment['user_id'], enrollment['workshop_id'])
        )
        db.execute("UPDATE enrollments SET status = 'attended' WHERE id = ?", (enrollment_id,))
        db.commit()
        flash('Participant status updated to Attended.', 'success')
    return redirect(url_for('participants'))


# ----------------------------------------------------
# Global Error Handlers
# ----------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ----------------------------------------------------
# Application Execution Entry Point
# ----------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("Community Skill-Building Workshop Platform")
    print("Server starting at http://127.0.0.1:5000")
    print("Default Admin Login: admin@workshop.com / admin123")
    print("Default Learner Login: learner@workshop.com / learner123")
    print("=" * 60)
    app.run(debug=True, port=5000)
