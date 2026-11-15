"""
SkillConnect - Cloud database setup (TiDB Cloud / MySQL)

Creates the database, tables and sample workshops, and creates or updates ONE
administrator account from environment variables. No demo accounts are created.

Settings are read from environment variables or a local .env file (never committed):
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
    ADMIN_NAME, ADMIN_EMAIL, ADMIN_PASSWORD   (password: at least 12 characters)

Usage:
    python scripts/init_cloud_db.py
"""

import os
import re
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from werkzeug.security import generate_password_hash  # noqa: E402
import app as webapp  # noqa: E402  (loads .env and the DB connection helper)


def split_sql(sql):
    sql = "\n".join(l for l in sql.splitlines() if not l.strip().startswith('--'))
    stmts, buf, quote = [], [], None
    for i, ch in enumerate(sql):
        if quote:
            if ch == quote and sql[i - 1] != '\\':
                quote = None
        elif ch in ("'", '"', '`'):
            quote = ch
        elif ch == ';':
            stmts.append(''.join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    stmts.append(''.join(buf).strip())
    return [s for s in stmts if s]


def main():
    if not webapp.USE_MYSQL:
        sys.exit('DB_HOST is not set. Put the cloud database settings in .env first.')

    admin_name = os.getenv('ADMIN_NAME', 'Administrator').strip()
    admin_email = os.getenv('ADMIN_EMAIL', '').strip().lower()
    admin_password = os.getenv('ADMIN_PASSWORD', '')
    if not webapp.is_valid_email(admin_email):
        sys.exit('Set ADMIN_EMAIL in .env to a valid email address.')
    if len(admin_password) < 12:
        sys.exit('Set ADMIN_PASSWORD in .env (at least 12 characters).')

    db_name = os.getenv('DB_NAME', 'skillconnect_db')
    if not re.fullmatch(r'[A-Za-z0-9_]+', db_name):
        sys.exit('DB_NAME may only contain letters, numbers and underscores.')

    print(f"Connecting to {os.environ['DB_HOST']} ...")
    server = webapp.connect_mysql(database='')
    with server.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    server.commit()
    server.close()

    conn = webapp.connect_mysql()
    try:
        with open(os.path.join(BASE_DIR, 'database', 'schema_mysql.sql'), encoding='utf-8') as f:
            stmts = split_sql(f.read())
        with conn.cursor() as cur:
            for s in stmts:
                cur.execute(s)

            pw_hash = generate_password_hash(admin_password)
            cur.execute("SELECT id FROM users WHERE LOWER(email) = %s", (admin_email,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE users SET name=%s, password_hash=%s, role='admin' WHERE id=%s",
                            (admin_name, pw_hash, row['id']))
                print(f"Updated administrator account: {admin_email}")
            else:
                cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin')",
                            (admin_name, admin_email, pw_hash))
                print(f"Created administrator account: {admin_email}")
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            print("Tables:", ', '.join(list(r.values())[0] for r in cur.fetchall()))
            cur.execute("SELECT COUNT(*) AS n FROM workshops")
            print("Workshops:", cur.fetchone()['n'])
        print("Done.")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
