"""
Database initialisation for MedBridge Ukraine.
Uses SQLite with WAL mode for performance.
"""

from __future__ import annotations
import os
import sqlite3
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DB_PATH: str = os.getenv("DATABASE_PATH", "./data/medbridge.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_conn():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)

    with db_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                language TEXT DEFAULT 'uk',
                language_other TEXT,
                age INTEGER,
                voice_note_text TEXT,
                additional_notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence_files (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                evidence_category TEXT DEFAULT 'other',
                gemma_extraction TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );

            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                raw_extractions TEXT,
                structured_data TEXT,
                timeline_data TEXT,
                risk_report TEXT,
                verification_checklist TEXT,
                passport_data TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );

            CREATE TABLE IF NOT EXISTS verifications (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                doctor_name TEXT,
                verification_data TEXT,
                overall_status TEXT DEFAULT 'pending',
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs(id)
            );
        """)

        # ── Idempotent migration: add language_other column on older DBs ──
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(patients)").fetchall()}
        if "language_other" not in cols:
            conn.execute("ALTER TABLE patients ADD COLUMN language_other TEXT")
            print("[DB] Migrated patients table: added language_other column")
    print("[DB] MedBridge database initialised")
