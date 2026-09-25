"""Local SQLite tracker so your application history survives between runs."""
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
    conn.commit()
    conn.close()


def add_application(job, ats_score, resume_path, cover_letter_path):
    conn = _connect()
    conn.execute(
        """INSERT OR REPLACE INTO applications
           (id, title, company, location, url, ats_score, status, resume_path,
            cover_letter_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'generated', ?, ?, ?)""",
        (job["id"], job["title"], job["company"], job.get("location", ""),
         job.get("url", ""), ats_score, resume_path, cover_letter_path,
         datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def mark_applied(job_id, notes=""):
    conn = _connect()
    conn.execute(
        "UPDATE applications SET status='applied', applied_at=?, notes=? WHERE id=?",
        (datetime.utcnow().isoformat(), notes, job_id),
    )
    conn.commit()
    conn.close()


def get_all():
    conn = _connect()
    rows = conn.execute("SELECT * FROM applications ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
