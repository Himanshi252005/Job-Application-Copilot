import sqlite3
from datetime import datetime

DB_PATH = "applications.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT,
            ats_score INTEGER,
            status TEXT DEFAULT 'generated',
            resume_path TEXT,
            cover_letter_path TEXT,
            created_at TEXT,
            applied_at TEXT,
            notes TEXT
        )
    """)
    # If upgrading from an older version of this file that had no
    # session_id column, add it without wiping existing data.
    cols = [row[1] for row in conn.execute("PRAGMA table_info(applications)").fetchall()]
    if "session_id" not in cols:
        conn.execute("ALTER TABLE applications ADD COLUMN session_id TEXT")
    conn.commit()
    conn.close()


def add_application(session_id, job, ats_score, resume_path, cover_letter_path):
    conn = _connect()
    # Composite key so the SAME job re-generated in a DIFFERENT session
    # doesn't overwrite another visitor's row.
    row_id = f"{session_id}:{job['id']}"
    conn.execute(
        """INSERT OR REPLACE INTO applications
           (id, session_id, title, company, location, url, ats_score, status,
            resume_path, cover_letter_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'generated', ?, ?, ?)""",
        (row_id, session_id, job["title"], job["company"], job.get("location", ""),
         job.get("url", ""), ats_score, resume_path, cover_letter_path,
         datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def mark_applied(session_id, job_id, notes=""):
    conn = _connect()
    row_id = f"{session_id}:{job_id}"
    conn.execute(
        "UPDATE applications SET status='applied', applied_at=?, notes=? WHERE id=? AND session_id=?",
        (datetime.utcnow().isoformat(), notes, row_id, session_id),
    )
    conn.commit()
    conn.close()


def get_all(session_id):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM applications WHERE session_id=? ORDER BY created_at DESC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
