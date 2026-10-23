
import sqlite3
from pathlib import Path

# Database file path
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "study_pattern.db"


def get_connection():
    """Create and return a database connection."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """Create database tables if they do not exist."""

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_name TEXT NOT NULL UNIQUE
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                start_time TEXT,
                duration_minutes INTEGER NOT NULL
                    CHECK (duration_minutes > 0),
                study_method TEXT NOT NULL,
                questions_practiced INTEGER NOT NULL DEFAULT 0
                    CHECK (questions_practiced >= 0),
                quiz_score REAL
                    CHECK (
                        quiz_score IS NULL
                        OR (quiz_score >= 0 AND quiz_score <= 100)
                    ),
                notes TEXT,
                FOREIGN KEY (subject_id)
                    REFERENCES subjects(subject_id)
            )
        """)


def add_study_session(
    subject_name,
    session_date,
    duration_minutes,
    study_method,
    start_time=None,
    questions_practiced=0,
    quiz_score=None,
    notes=""
):
    """Save a study session in the database."""

    subject_name = subject_name.strip()

    if not subject_name:
        raise ValueError("Subject name cannot be empty.")

    if duration_minutes <= 0:
        raise ValueError("Duration must be greater than zero.")

    if questions_practiced < 0:
        raise ValueError("Questions practiced cannot be negative.")

    if quiz_score is not None and not 0 <= quiz_score <= 100:
        raise ValueError("Quiz score must be between 0 and 100.")

    with get_connection() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO subjects (subject_name) VALUES (?)",
            (subject_name,)
        )

        subject = connection.execute(
            "SELECT subject_id FROM subjects WHERE subject_name = ?",
            (subject_name,)
        ).fetchone()

        subject_id = subject[0]

        connection.execute("""
            INSERT INTO study_sessions (
                subject_id,
                session_date,
                start_time,
                duration_minutes,
                study_method,
                questions_practiced,
                quiz_score,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subject_id,
            str(session_date),
            start_time,
            duration_minutes,
            study_method,
            questions_practiced,
            quiz_score,
            notes
        ))


def get_all_sessions():
    """Return all study sessions as a list of dictionaries."""

    with get_connection() as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT
                ss.session_id,
                s.subject_name,
                ss.session_date,
                ss.start_time,
                ss.duration_minutes,
                ss.study_method,
                ss.questions_practiced,
                ss.quiz_score,
                ss.notes
            FROM study_sessions AS ss
            JOIN subjects AS s
                ON ss.subject_id = s.subject_id
            ORDER BY ss.session_date DESC, ss.session_id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def delete_study_session(session_id):
    """Delete a study session using its ID."""

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM study_sessions WHERE session_id = ?",
            (session_id,)
        )


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")
    print(f"Database location: {DB_PATH}")
