# Community Skill-Building Workshop Platform

A complete, lightweight, and responsive web application designed for a college mini-project. The platform connects community members with practical skill-development workshops, mentors, and local learning opportunities.

---

## 🛠️ Technology Stack

* **Frontend**: HTML5, CSS3 (Custom Responsive Design), Vanilla JavaScript (ES6)
* **Backend**: Python Flask (Session-based Authentication, Jinja2 Server-Side Templates)
* **Database**: SQLite3 (ACID-compliant relational database, with automated initialization)
* **IDE**: Google Antigravity / Visual Studio Code

---

## 📂 Project Structure

```
community-skill-workshop/
│
├── app.py                      # Flask main entry point, routes, controllers & business logic
├── requirements.txt            # Python dependencies (Flask, Werkzeug)
├── README.md                   # Project documentation and setup guide
├── instance/                   # Runtime instance folder (contains SQLite workshop.db)
│
├── database/
│   └── schema.sql              # Database DDL schema and initial demo seed data
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Master layout with responsive navbar, flash alerts & footer
│   ├── index.html              # Landing page (hero banner, metrics & featured workshops)
│   ├── login.html              # User and Administrator sign-in page
│   ├── register.html           # New learner account registration page
│   ├── dashboard.html          # Learner personal overview (stats, enrolled sessions)
│   ├── workshops.html          # Browse all workshops (with live search & category filter)
│   ├── workshop_details.html   # Detailed workshop overview, trainer bio, reviews & enroll CTA
│   ├── my_workshops.html       # Full attendee schedule view with cancellation options
│   ├── admin_dashboard.html    # Admin management portal (KPI cards & workshop list)
│   ├── add_workshop.html       # Admin form to schedule and publish a new workshop
│   ├── edit_workshop.html      # Admin form to modify workshop details and status
│   ├── participants.html       # Attendee roster view with attendance tracking
│   └── feedback.html           # Workshop review submission & community testimonials
│
└── static/                     # Static assets served to the client
    ├── css/
    │   └── style.css           # Complete responsive stylesheet (cards, forms, alerts, tables)
    ├── js/
    │   └── script.js           # Client-side logic (menu toggle, search/filter, dialogs)
    └── images/                 # Image assets and workshop category illustrations
```

---

## 🚀 How to Run the Project

### 1. Navigate to the Project Directory
Open your terminal in the project directory:
```bash
cd "d:\Community skill development project\community-skill-workshop"
```

### 2. Install Dependencies
Install the required lightweight Python libraries:
```bash
pip install -r requirements.txt
```

### 3. Launch the Application
Run the main application script:
```bash
python app.py
```

### 4. Open in Browser
Open your browser and navigate to:
```
http://127.0.0.1:5000
```
> *Note: On the first run, `app.py` automatically initializes the SQLite database at `instance/workshop.db` using `database/schema.sql`, pre-populating it with demo workshops and test accounts.*

---

## 🧪 Running Automated Tests

Run the full automated test suite covering all modules:
```bash
# Run all unit and integration test suites
python -m unittest discover tests

# Or run individual test suites:
python -m unittest tests/test_auth.py
python -m unittest tests/test_workshops.py
python -m unittest tests/test_dashboard.py
python -m unittest tests/test_admin.py
python -m unittest tests/test_attendance_feedback.py
python -m unittest tests/test_integration.py
```

---

## 🔑 Demo Login Credentials

For quick testing, evaluation, and grading, the following pre-configured demo accounts are available:

| Role | Email Address | Password | Privileges |
|---|---|---|---|
| **Administrator** | `admin@workshop.com` | `admin123` | Full CRUD on workshops, view attendee roster, mark attendance |
| **Learner** | `learner@workshop.com` | `learner123` | Browse catalog, enroll/cancel seats, write workshop reviews |

You can also register a new learner account at any time via the `/register` page.

---

## 📋 Major Folder and File Explanations

### Root Files
* **`app.py`**: The central application file. Configures Flask, connects to SQLite with context-managed connections (`get_db()`, `close_db()`), defines route guards (`@login_required`, `@admin_required`), handles HTTP GET/POST requests, hashes passwords, and serves templates.
* **`requirements.txt`**: Specifies standard, clean Python packages (`Flask`, `Werkzeug`) without heavy third-party frameworks.
* **`README.md`**: Provides full documentation, setup steps, architecture explanations, and test credentials.

### Data Storage
* **`instance/`**: Stores instance-specific runtime data. The SQLite database (`workshop.db`) is automatically created and maintained here.
* **`database/schema.sql`**: Contains standard SQL DDL statements (`CREATE TABLE`, foreign keys, constraints) and realistic initial seed records (categories, trainers, workshops, and feedback).

### Presentation Layer (`templates/`)
* **`base.html`**: Master layout providing consistent branding, sticky navigation with responsive mobile toggle, flash messaging, and footer across all pages.
* **`index.html`**: Homepage displaying the hero CTA, live stats, and upcoming workshop highlights.
* **`login.html` & `register.html`**: Secure authentication views with input validation and credential hints.
* **`dashboard.html`**: Personalized learner portal summarizing attendance, upcoming dates, and quick actions.
* **`workshops.html`**: Public catalog with real-time client-side search and category filtering.
* **`workshop_details.html`**: In-depth view of a specific workshop, seat counter, and attendee ratings.
* **`my_workshops.html`**: Detailed view of a user's reservations with cancellation capabilities.
* **`admin_dashboard.html`**: Administrative command center showing platform KPIs and workshop management actions.
* **`add_workshop.html` & `edit_workshop.html`**: Forms for adding and editing workshop details.
* **`participants.html`**: Administrative roster for tracking registered attendees across sessions.
* **`feedback.html`**: Interactive 5-star rating submission form and community reviews wall.

### Static Assets (`static/`)
* **`css/style.css`**: Handcrafted CSS utilizing CSS custom properties, responsive flexbox/grid layouts, clean typography, alerts, and badges without requiring Bootstrap or external CDNs.
* **`js/script.js`**: Vanilla JavaScript handling mobile hamburger menu toggling, 5-second alert auto-dismissal, live search filtering, and confirmation modals.
* **`images/`**: Directory reserved for category icons and project imagery.
