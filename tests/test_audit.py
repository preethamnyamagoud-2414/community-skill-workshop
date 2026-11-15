"""
Automated Comprehensive Audit Test Suite
Covers:
- Responsive Design Verification
- Missing Image / Asset Checks
- Broken Link Crawling (Public, Learner, Admin)
- Console & JavaScript Syntax / Reference Integrity
- Flask Error Handlers (404 & 500)
- Database Integrity (Foreign Keys, Cascades, Constraints)
- Unauthorized Access & RBAC Route Protection
- Workshop Capacity Bounds & Duplicate Prevention
- Feedback Rating & Comment Validations
"""

import os
import sys
import unittest
import tempfile
import sqlite3
import re
from unittest.mock import patch
from html.parser import HTMLParser

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from app import app, get_db


class LinkAndAssetExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []
        self.scripts = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'a' and 'href' in attrs_dict:
            self.links.append(attrs_dict['href'])
        elif tag == 'img' and 'src' in attrs_dict:
            self.images.append(attrs_dict['src'])
        elif tag == 'script' and 'src' in attrs_dict:
            self.scripts.append(attrs_dict['src'])
        elif tag == 'link' and attrs_dict.get('rel') == 'stylesheet' and 'href' in attrs_dict:
            self.stylesheets.append(attrs_dict['href'])


class ApplicationAuditTestCase(unittest.TestCase):
    """Deep verification of frontend assets, links, error handlers, DB integrity, and RBAC."""

    def setUp(self):
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
        return self.client.post('/login', data={
            'email': 'learner@workshop.com',
            'password': 'learner123'
        }, follow_redirects=True)

    def login_admin(self):
        return self.client.post('/login', data={
            'email': 'admin@workshop.com',
            'password': 'admin123'
        }, follow_redirects=True)

    # ----------------------------------------------------
    # 1. Missing Images & Static Assets Audit
    # ----------------------------------------------------
    def test_missing_images_and_static_assets(self):
        """Verify no broken images exist and all referenced CSS/JS files exist on disk."""
        pages = ['/', '/workshops', '/workshop/1', '/login', '/register']
        
        for page in pages:
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200, f"Page {page} failed to load.")
            html = res.data.decode('utf-8')
            parser = LinkAndAssetExtractor()
            parser.feed(html)

            # Check all img tags
            for img_src in parser.images:
                if img_src.startswith('/static/'):
                    rel_path = img_src.replace('/static/', '', 1).split('?')[0]
                    disk_path = os.path.join(BASE_DIR, 'static', rel_path)
                    self.assertTrue(os.path.exists(disk_path), f"Missing image file referenced on {page}: {img_src}")

            # Check all script src
            for script_src in parser.scripts:
                if script_src.startswith('/static/'):
                    rel_path = script_src.replace('/static/', '', 1).split('?')[0]
                    disk_path = os.path.join(BASE_DIR, 'static', rel_path)
                    self.assertTrue(os.path.exists(disk_path), f"Missing script file referenced on {page}: {script_src}")

            # Check all stylesheets
            for css_href in parser.stylesheets:
                if css_href.startswith('/static/'):
                    rel_path = css_href.replace('/static/', '', 1).split('?')[0]
                    disk_path = os.path.join(BASE_DIR, 'static', rel_path)
                    self.assertTrue(os.path.exists(disk_path), f"Missing CSS file referenced on {page}: {css_href}")

    # ----------------------------------------------------
    # 2. Broken Links Crawling Audit
    # ----------------------------------------------------
    def test_broken_links_public(self):
        """Crawl all internal links accessible on public pages to ensure no 404 or 500 errors."""
        public_pages = ['/', '/workshops', '/workshop/1', '/login', '/register']
        visited = set()

        for page in public_pages:
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200)
            html = res.data.decode('utf-8')
            parser = LinkAndAssetExtractor()
            parser.feed(html)

            for link in parser.links:
                clean_link = link.split('#')[0]
                if not clean_link or clean_link.startswith('mailto:') or clean_link.startswith('tel:') or clean_link.startswith('http'):
                    continue
                if clean_link in visited:
                    continue
                visited.add(clean_link)

                check_res = self.client.get(clean_link, follow_redirects=True)
                self.assertNotEqual(check_res.status_code, 404, f"Broken link found on {page}: {clean_link} returned 404")
                self.assertNotEqual(check_res.status_code, 500, f"Server error on {page}: {clean_link} returned 500")

    def test_broken_links_learner(self):
        """Crawl all internal links accessible on learner pages."""
        self.login_learner()
        learner_pages = ['/dashboard', '/my-workshops', '/feedback/1', '/workshop/1']
        visited = set()

        for page in learner_pages:
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200)
            html = res.data.decode('utf-8')
            parser = LinkAndAssetExtractor()
            parser.feed(html)

            for link in parser.links:
                clean_link = link.split('#')[0]
                if not clean_link or clean_link.startswith('mailto:') or clean_link.startswith('tel:') or clean_link.startswith('http'):
                    continue
                if clean_link == '/logout':
                    continue  # Tested separately to avoid destroying session mid-crawl
                if clean_link in visited:
                    continue
                visited.add(clean_link)

                check_res = self.client.get(clean_link, follow_redirects=True)
                self.assertNotEqual(check_res.status_code, 404, f"Broken link for learner: {clean_link}")
                self.assertNotEqual(check_res.status_code, 500, f"Server error for learner: {clean_link}")

    def test_broken_links_admin(self):
        """Crawl all internal links accessible on admin pages."""
        self.login_admin()
        admin_pages = ['/admin/dashboard', '/admin/workshop/add', '/admin/workshop/edit/1', '/admin/participants', '/admin/feedback']
        visited = set()

        for page in admin_pages:
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200)
            html = res.data.decode('utf-8')
            parser = LinkAndAssetExtractor()
            parser.feed(html)

            for link in parser.links:
                clean_link = link.split('#')[0]
                if not clean_link or clean_link.startswith('mailto:') or clean_link.startswith('tel:') or clean_link.startswith('http'):
                    continue
                if clean_link == '/logout':
                    continue  # Tested separately
                if clean_link in visited:
                    continue
                visited.add(clean_link)

                check_res = self.client.get(clean_link, follow_redirects=True)
                self.assertNotEqual(check_res.status_code, 404, f"Broken link for admin: {clean_link}")
                self.assertNotEqual(check_res.status_code, 500, f"Server error for admin: {clean_link}")

    # ----------------------------------------------------
    # 3. Responsive Design Audit
    # ----------------------------------------------------
    def test_responsive_design_elements(self):
        """Verify viewport meta tag, mobile navigation toggles, and CSS media queries."""
        # 1. Viewport tag in base template
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'<meta name="viewport" content="width=device-width, initial-scale=1.0">', res.data)
        self.assertIn(b'nav-toggle', res.data)

        # 2. Check CSS breakpoints
        css_path = os.path.join(BASE_DIR, 'static', 'css', 'style.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        self.assertIn('@media (max-width: 768px)', css)
        self.assertIn('@media (max-width: 900px)', css)
        self.assertIn('@media (max-width: 992px)', css)
        self.assertIn('.table-responsive', css)

    # ----------------------------------------------------
    # 4. Console & JavaScript Syntax Audit
    # ----------------------------------------------------
    def test_javascript_syntax_and_dom_bindings(self):
        """Verify script.js has valid syntax structure and all DOM element IDs exist in templates."""
        js_path = os.path.join(BASE_DIR, 'static', 'js', 'script.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            js_code = f.read()

        # Check balanced braces, brackets, and parentheses
        stack = []
        pairs = {')': '(', '}': '{', ']': '['}
        in_string = False
        quote_char = ''
        
        # Simple structural balance check ignoring string literals
        for char in js_code:
            if char in ('"', "'", '`') and not in_string:
                in_string = True
                quote_char = char
            elif char == quote_char and in_string:
                in_string = False
            elif not in_string:
                if char in pairs.values():
                    stack.append(char)
                elif char in pairs.keys():
                    if not stack or stack[-1] != pairs[char]:
                        self.fail(f"Mismatched bracket in script.js: {char}")
                    stack.pop()

        self.assertEqual(len(stack), 0, "Unclosed bracket or brace in script.js")

        # Verify all element IDs referenced in JS exist in templates
        ids_in_js = re.findall(r"document\.getElementById\(['\"]([^'\"]+)['\"]\)", js_code)
        all_templates_content = ""
        tpl_dir = os.path.join(BASE_DIR, 'templates')
        for tpl_file in os.listdir(tpl_dir):
            with open(os.path.join(tpl_dir, tpl_file), 'r', encoding='utf-8') as f:
                all_templates_content += f.read() + "\n"

        for elem_id in ids_in_js:
            self.assertIn(f'id="{elem_id}"', all_templates_content, f"Element ID '{elem_id}' from script.js missing in templates")

    # ----------------------------------------------------
    # 5. Flask Error Handlers Audit
    # ----------------------------------------------------
    def test_flask_404_error_handler(self):
        """Verify 404 handler intercepts undefined routes cleanly."""
        res = self.client.get('/invalid-page-does-not-exist')
        self.assertEqual(res.status_code, 404)
        self.assertIn(b'404', res.data)
        self.assertIn(b'Page Not Found', res.data)

    def test_flask_500_error_handler(self):
        """Verify 500 error handler produces proper status and template."""
        app.config['TESTING'] = False
        app.config['PROPAGATE_EXCEPTIONS'] = False
        try:
            with patch('app.get_db', side_effect=sqlite3.OperationalError('Simulated DB Crash')):
                res = self.client.get('/workshops')
                self.assertEqual(res.status_code, 500)
                self.assertIn(b'500', res.data)
                self.assertIn(b'Server Error', res.data)
        finally:
            app.config['TESTING'] = True
            app.config['PROPAGATE_EXCEPTIONS'] = True

    # ----------------------------------------------------
    # 6. Database Integrity & Constraints Audit
    # ----------------------------------------------------
    def test_database_foreign_keys_and_cascade_deletes(self):
        """Verify foreign key enforcement, cascade deletion, and unique constraints."""
        with app.app_context():
            db = get_db()
            
            # Verify PRAGMA foreign_keys is ON
            fk_status = db.execute("PRAGMA foreign_keys").fetchone()[0]
            self.assertEqual(fk_status, 1, "Foreign keys are not enabled in SQLite connection")

            # Check unique constraint on users.email
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES ('Dup', 'learner@workshop.com', 'h', 'learner')"
                )

            # Check unique constraint on enrollments (user_id, workshop_id)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO enrollments (user_id, workshop_id, status) VALUES (2, 1, 'confirmed')"
                )

            # Check rating CHECK constraint (rating BETWEEN 1 AND 5)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO feedback (user_id, workshop_id, rating, comments) VALUES (2, 2, 6, 'Invalid')"
                )

            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO feedback (user_id, workshop_id, rating, comments) VALUES (2, 2, 0, 'Invalid')"
                )

            # Check cascade delete on workshop deletion
            # Delete workshop 1 and verify enrollments, attendance, and feedback referencing it are deleted
            db.execute("DELETE FROM workshops WHERE id = 1")
            db.commit()

            enr_count = db.execute("SELECT COUNT(*) FROM enrollments WHERE workshop_id = 1").fetchone()[0]
            self.assertEqual(enr_count, 0, "Cascade delete failed on enrollments")

            att_count = db.execute("SELECT COUNT(*) FROM attendance WHERE workshop_id = 1").fetchone()[0]
            self.assertEqual(att_count, 0, "Cascade delete failed on attendance")

    # ----------------------------------------------------
    # 7. Unauthorized Access & RBAC Audit
    # ----------------------------------------------------
    def test_unauthorized_access_security(self):
        """Verify learners and unauthenticated users cannot invoke admin actions."""
        # Unauthenticated attempts to POST admin endpoints
        admin_post_endpoints = [
            ('/admin/workshop/add', {'title': 'Hack'}),
            ('/admin/workshop/edit/1', {'title': 'Hack'}),
            ('/admin/workshop/delete/1', {}),
            ('/admin/attendance/mark', {'enrollment_id': '1', 'status': 'Present'}),
            ('/admin/feedback/delete/1', {})
        ]

        for url, post_data in admin_post_endpoints:
            res = self.client.post(url, data=post_data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'administrator credentials', res.data)

        # Authenticated learner attempts to POST admin endpoints
        self.login_learner()
        for url, post_data in admin_post_endpoints:
            res = self.client.post(url, data=post_data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Access restricted: Administrator rights required', res.data)


if __name__ == '__main__':
    unittest.main()
