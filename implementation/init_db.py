import os
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    instructor TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    grade TEXT,
    score REAL,
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
);
"""

SEED_SQL = """
-- Seed students
INSERT OR IGNORE INTO students (id, name, cohort, email) VALUES
(1, 'Alice Nguyen', 'A1', 'alice@example.com'),
(2, 'Bob Tran', 'A1', 'bob@example.com'),
(3, 'Charlie Le', 'B2', 'charlie@example.com'),
(4, 'David Pham', 'B2', 'david@example.com'),
(5, 'Eve Vo', 'A1', 'eve@example.com');

-- Seed courses
INSERT OR IGNORE INTO courses (id, title, instructor, credits) VALUES
(1, 'Intro to AI', 'Dr. Smith', 4),
(2, 'Database Systems', 'Prof. Jones', 3),
(3, 'Software Engineering', 'Dr. Taylor', 4);

-- Seed enrollments
INSERT OR IGNORE INTO enrollments (student_id, course_id, grade, score) VALUES
(1, 1, 'A', 95.0),
(1, 2, 'B+', 88.5),
(2, 1, 'A-', 91.0),
(2, 3, 'A', 96.5),
(3, 2, 'C', 72.0),
(3, 3, 'B', 83.0),
(4, 1, 'B-', 80.0),
(4, 2, 'B', 85.0),
(5, 1, 'A', 98.0),
(5, 3, 'A-', 92.0);
"""


def create_database(db_path: str = "sqlite_lab.db") -> str:
    """
    Initializes the SQLite database with schemas and seed data.
    Returns the absolute path to the database.
    """
    db_abs_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(db_abs_path), exist_ok=True)
    
    conn = sqlite3.connect(db_abs_path)
    try:
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Execute schema
        conn.executescript(SCHEMA_SQL)
        
        # Execute seed data
        conn.executescript(SEED_SQL)
        
        conn.commit()
    finally:
        conn.close()
        
    return db_abs_path

if __name__ == "__main__":
    path = create_database()
    print(f"Database created and seeded successfully at: {path}")
