"""SQLite database layer with parameterized queries, constraints, and seeding."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generator, Optional

from config import (
    ATTENDANCE_THRESHOLD_DEFAULT,
    DATABASE_PATH,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_STUDENT_PASSWORD,
)
from database.security import hash_password, verify_password

_DB_INSTANCE: Optional["Database"] = None


def get_db(db_path: Optional[Path] = None) -> "Database":
    global _DB_INSTANCE
    if db_path is not None:
        return Database(db_path)
    if _DB_INSTANCE is None:
        _DB_INSTANCE = Database(DATABASE_PATH)
    return _DB_INSTANCE


class Database:
    def __init__(self, db_path: Path | str = DATABASE_PATH, seed_demo: bool = True) -> None:
        self.db_path = Path(db_path)
        self.seed_demo = seed_demo
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            self._create_tables(conn)
        self._ensure_default_admin()
        self._ensure_settings()
        self._seed_if_empty()

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
                section TEXT NOT NULL,
                phone TEXT NOT NULL,
                attendance_percentage REAL NOT NULL DEFAULT 0
                    CHECK (attendance_percentage BETWEEN 0 AND 100),
                internal_examination_marks REAL NOT NULL DEFAULT 0
                    CHECK (internal_examination_marks BETWEEN 0 AND 100),
                assignment_score REAL NOT NULL DEFAULT 0
                    CHECK (assignment_score BETWEEN 0 AND 100),
                previous_semester_performance REAL NOT NULL DEFAULT 0
                    CHECK (previous_semester_performance BETWEEN 0 AND 100),
                study_hours REAL NOT NULL DEFAULT 0
                    CHECK (study_hours BETWEEN 0 AND 16),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'student')),
                student_id TEXT UNIQUE,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login TEXT,
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
                max_marks REAL NOT NULL DEFAULT 100 CHECK (max_marks > 0)
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                subject_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('Present', 'Absent')),
                UNIQUE (student_id, subject_id, attendance_date),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS marks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                subject_id INTEGER NOT NULL,
                exam_type TEXT NOT NULL DEFAULT 'Internal',
                marks REAL NOT NULL CHECK (marks >= 0),
                max_marks REAL NOT NULL CHECK (max_marks > 0),
                UNIQUE (student_id, subject_id, exam_type),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                subject_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                score REAL NOT NULL CHECK (score >= 0),
                max_score REAL NOT NULL CHECK (max_score > 0),
                submitted_on TEXT NOT NULL,
                UNIQUE (student_id, subject_id, title),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                predicted_category TEXT NOT NULL,
                probabilities_json TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                reason TEXT,
                model_version TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

    def _ensure_default_admin(self) -> None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,)
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO users (username, password_hash, role, student_id,
                                       must_change_password, created_at)
                    VALUES (?, ?, 'admin', NULL, 1, ?)
                    """,
                    (
                        DEFAULT_ADMIN_USERNAME,
                        hash_password(DEFAULT_ADMIN_PASSWORD),
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )

    def _ensure_settings(self) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                ("attendance_threshold", str(ATTENDANCE_THRESHOLD_DEFAULT)),
            )
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                ("well_performing_marks", "80"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                ("attention_marks", "50"),
            )

    def _seed_if_empty(self) -> None:
        with self.connection() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
        if count == 0 and self.seed_demo:
            self.seed_demonstration_data()

    # ------------------------------------------------------------------ settings
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    def get_attendance_threshold(self) -> float:
        return float(self.get_setting("attendance_threshold", str(ATTENDANCE_THRESHOLD_DEFAULT)))

    def set_attendance_threshold(self, value: float) -> None:
        if not 0 <= value <= 100:
            raise ValueError("Attendance threshold must be between 0 and 100.")
        self.set_setting("attendance_threshold", str(value))

    # ------------------------------------------------------------------ users
    def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username.strip(),)
            ).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            return None
        with self.connection() as conn:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), row["id"]),
            )
            refreshed = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
        return dict(refreshed) if refreshed else dict(row)

    def check_password(self, username: str, password: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE username = ?", (username.strip(),)
            ).fetchone()
        if row is None:
            return False
        return verify_password(password, row["password_hash"])

    def get_user_by_username(self, username: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
            return dict(row) if row else None

    def change_password(
        self,
        username: str,
        new_password: str,
        clear_flag: bool = True,
        current_password: str | None = None,
    ) -> None:
        if current_password is not None and not self.check_password(username, current_password):
            raise ValueError("Current password is incorrect.")
        hashed = hash_password(new_password)
        with self.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE users
                SET password_hash = ?, must_change_password = ?
                WHERE username = ?
                """,
                (hashed, 0 if clear_flag else 1, username.strip()),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"User {username} was not found.")

    def create_student_user(self, student_id: str, password: str = DEFAULT_STUDENT_PASSWORD) -> None:
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ? OR student_id = ?",
                (student_id, student_id),
            ).fetchone()
            if existing:
                return
            conn.execute(
                """
                INSERT INTO users (username, password_hash, role, student_id,
                                   must_change_password, created_at)
                VALUES (?, ?, 'student', ?, 0, ?)
                """,
                (
                    student_id,
                    hash_password(password),
                    student_id,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

    # ------------------------------------------------------------------ students
    def add_student(self, data: dict[str, Any], create_login: bool = True) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        payload = {
            "student_id": data["student_id"].strip().upper(),
            "full_name": data["full_name"].strip(),
            "email": data["email"].strip().lower(),
            "department": data["department"].strip(),
            "semester": int(data["semester"]),
            "section": data["section"].strip().upper(),
            "phone": data["phone"].strip(),
            "attendance_percentage": float(data.get("attendance_percentage", 0)),
            "internal_examination_marks": float(data.get("internal_examination_marks", 0)),
            "assignment_score": float(data.get("assignment_score", 0)),
            "previous_semester_performance": float(data.get("previous_semester_performance", 0)),
            "study_hours": float(data.get("study_hours", 0)),
            "created_at": now,
            "updated_at": now,
        }
        try:
            with self.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO students (
                        student_id, full_name, email, department, semester, section, phone,
                        attendance_percentage, internal_examination_marks, assignment_score,
                        previous_semester_performance, study_hours, created_at, updated_at
                    ) VALUES (
                        :student_id, :full_name, :email, :department, :semester, :section, :phone,
                        :attendance_percentage, :internal_examination_marks, :assignment_score,
                        :previous_semester_performance, :study_hours, :created_at, :updated_at
                    )
                    """,
                    payload,
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Student ID or email already exists.") from exc
        if create_login:
            self.create_student_user(payload["student_id"])

    def update_student(self, student_id: str, data: dict[str, Any]) -> None:
        allowed = [
            "full_name",
            "email",
            "department",
            "semester",
            "section",
            "phone",
            "attendance_percentage",
            "internal_examination_marks",
            "assignment_score",
            "previous_semester_performance",
            "study_hours",
        ]
        fields = []
        values: list[Any] = []
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if not fields:
            return
        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat(timespec="seconds"))
        values.append(student_id)
        try:
            with self.connection() as conn:
                conn.execute(f"UPDATE students SET {', '.join(fields)} WHERE student_id = ?", values)
                if conn.total_changes == 0:
                    raise ValueError(f"Student {student_id} was not found.")
        except sqlite3.IntegrityError as exc:
            raise ValueError("Email already exists for another student.") from exc

    def delete_student(self, student_id: str) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM users WHERE student_id = ?", (student_id,))
            cursor = conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
            if cursor.rowcount == 0:
                raise ValueError(f"Student {student_id} was not found.")

    def get_student(self, student_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM students WHERE student_id = ?", (student_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_students(
        self,
        search: str = "",
        department: str = "",
        semester: str | int = "",
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM students WHERE 1=1"
        params: list[Any] = []
        if search:
            query += " AND (student_id LIKE ? OR full_name LIKE ?)"
            like = f"%{search.strip()}%"
            params.extend([like, like])
        if department:
            query += " AND department = ?"
            params.append(department)
        if semester not in ("", None):
            query += " AND semester = ?"
            params.append(int(semester))
        query += " ORDER BY student_id"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def student_exists(self, student_id: str) -> bool:
        return self.get_student(student_id) is not None

    def email_taken(self, email: str, exclude_id: str | None = None) -> bool:
        with self.connection() as conn:
            if exclude_id:
                row = conn.execute(
                    "SELECT student_id FROM students WHERE email = ? AND student_id <> ?",
                    (email.lower(), exclude_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT student_id FROM students WHERE email = ?", (email.lower(),)
                ).fetchone()
            return row is not None

    # ------------------------------------------------------------------ dashboard stats
    def dashboard_stats(self) -> dict[str, Any]:
        threshold = self.get_attendance_threshold()
        well_marks = float(self.get_setting("well_performing_marks", "80") or 80)
        attention_marks = float(self.get_setting("attention_marks", "50") or 50)
        with self.connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
            averages = conn.execute(
                """
                SELECT
                    COALESCE(AVG(attendance_percentage), 0) AS avg_attendance,
                    COALESCE(AVG(internal_examination_marks), 0) AS avg_marks,
                    COALESCE(AVG(assignment_score), 0) AS avg_assignment
                FROM students
                """
            ).fetchone()
            well = conn.execute(
                """
                SELECT COUNT(*) AS c FROM students
                WHERE internal_examination_marks >= ? AND attendance_percentage >= ?
                """,
                (well_marks, threshold),
            ).fetchone()["c"]
            attention = conn.execute(
                """
                SELECT COUNT(*) AS c FROM students
                WHERE attendance_percentage < ? OR internal_examination_marks < ?
                """,
                (threshold, attention_marks),
            ).fetchone()["c"]
            latest = conn.execute(
                "SELECT * FROM students ORDER BY created_at DESC, student_id DESC LIMIT 8"
            ).fetchall()
        return {
            "total_students": total,
            "avg_attendance": round(float(averages["avg_attendance"]), 2),
            "avg_marks": round(float(averages["avg_marks"]), 2),
            "avg_assignment": round(float(averages["avg_assignment"]), 2),
            "performing_well": well,
            "requiring_attention": attention,
            "latest": [dict(r) for r in latest],
        }

    def performance_distribution(self) -> dict[str, int]:
        buckets = {"Excellent (85+)": 0, "Good (70-84)": 0, "Average (50-69)": 0, "At Risk (<50)": 0}
        with self.connection() as conn:
            rows = conn.execute("SELECT internal_examination_marks FROM students").fetchall()
        for row in rows:
            m = float(row["internal_examination_marks"])
            if m >= 85:
                buckets["Excellent (85+)"] += 1
            elif m >= 70:
                buckets["Good (70-84)"] += 1
            elif m >= 50:
                buckets["Average (50-69)"] += 1
            else:
                buckets["At Risk (<50)"] += 1
        return buckets

    def attendance_distribution(self) -> dict[str, int]:
        buckets = {"90-100%": 0, "75-89%": 0, "60-74%": 0, "Below 60%": 0}
        with self.connection() as conn:
            rows = conn.execute("SELECT attendance_percentage FROM students").fetchall()
        for row in rows:
            a = float(row["attendance_percentage"])
            if a >= 90:
                buckets["90-100%"] += 1
            elif a >= 75:
                buckets["75-89%"] += 1
            elif a >= 60:
                buckets["60-74%"] += 1
            else:
                buckets["Below 60%"] += 1
        return buckets

    def class_stats(self, department: str = "", semester: str | int = "") -> dict[str, Any]:
        students = self.list_students(department=department, semester=semester)
        if not students:
            return {
                "student_count": 0,
                "avg_attendance": 0.0,
                "avg_marks": 0.0,
                "avg_assignment": 0.0,
            }
        n = len(students)
        return {
            "student_count": n,
            "avg_attendance": round(sum(s["attendance_percentage"] for s in students) / n, 2),
            "avg_marks": round(sum(s["internal_examination_marks"] for s in students) / n, 2),
            "avg_assignment": round(sum(s["assignment_score"] for s in students) / n, 2),
        }

    def department_averages(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT department,
                       AVG(internal_examination_marks) AS avg_marks,
                       AVG(attendance_percentage) AS avg_attendance,
                       COUNT(*) AS student_count
                FROM students
                GROUP BY department
                ORDER BY department
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def top_students(self, limit: int = 8) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM students
                ORDER BY internal_examination_marks DESC, attendance_percentage DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ subjects
    def add_subject(self, code: str, name: str, department: str, semester: int, max_marks: float = 100) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO subjects (code, name, department, semester, max_marks)
                VALUES (?, ?, ?, ?, ?)
                """,
                (code.strip().upper(), name.strip(), department, int(semester), float(max_marks)),
            )
            return int(cursor.lastrowid)

    def list_subjects(self, department: str = "", semester: str | int = "") -> list[dict[str, Any]]:
        query = "SELECT * FROM subjects WHERE 1=1"
        params: list[Any] = []
        if department:
            query += " AND department = ?"
            params.append(department)
        if semester not in ("", None):
            query += " AND semester = ?"
            params.append(int(semester))
        query += " ORDER BY department, semester, code"
        with self.connection() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def get_subject(self, subject_id: int) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------ attendance
    def record_attendance(self, student_id: str, subject_id: int, date: str, status: str) -> None:
        if status not in ("Present", "Absent"):
            raise ValueError("Status must be Present or Absent.")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO attendance (student_id, subject_id, attendance_date, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(student_id, subject_id, attendance_date)
                DO UPDATE SET status = excluded.status
                """,
                (student_id, subject_id, date, status),
            )
        self.refresh_attendance_percentage(student_id)

    def attendance_history(self, student_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT a.*, s.code AS subject_code, s.name AS subject_name
                FROM attendance a
                JOIN subjects s ON s.id = a.subject_id
                WHERE a.student_id = ?
                ORDER BY a.attendance_date DESC
                """,
                (student_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def class_attendance_on_date(self, date: str, department: str = "", semester: str | int = "") -> list[dict[str, Any]]:
        students = self.list_students(department=department, semester=semester)
        results = []
        with self.connection() as conn:
            for student in students:
                rows = conn.execute(
                    """
                    SELECT status FROM attendance
                    WHERE student_id = ? AND attendance_date = ?
                    """,
                    (student["student_id"], date),
                ).fetchall()
                if not rows:
                    status = "Not marked"
                elif all(r["status"] == "Present" for r in rows):
                    status = "Present"
                elif all(r["status"] == "Absent" for r in rows):
                    status = "Absent"
                else:
                    status = "Partial"
                results.append({**student, "day_status": status})
        return results

    def refresh_attendance_percentage(self, student_id: str) -> float:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count
                FROM attendance
                WHERE student_id = ?
                """,
                (student_id,),
            ).fetchone()
            total = int(row["total"] or 0)
            present = int(row["present_count"] or 0)
            if total == 0:
                student_row = conn.execute(
                    "SELECT attendance_percentage FROM students WHERE student_id = ?",
                    (student_id,),
                ).fetchone()
                return float(student_row["attendance_percentage"]) if student_row else 0.0
            pct = round(100.0 * present / total, 2)
            conn.execute(
                "UPDATE students SET attendance_percentage = ?, updated_at = ? WHERE student_id = ?",
                (pct, datetime.now().isoformat(timespec="seconds"), student_id),
            )
            return pct

    def low_attendance_students(self, threshold: float | None = None) -> list[dict[str, Any]]:
        if threshold is None:
            threshold = self.get_attendance_threshold()
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM students
                WHERE attendance_percentage < ?
                ORDER BY attendance_percentage ASC
                """,
                (threshold,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ marks
    def upsert_mark(
        self,
        student_id: str,
        subject_id: int,
        marks: float,
        max_marks: float,
        exam_type: str = "Internal",
    ) -> None:
        if marks > max_marks:
            raise ValueError("Marks cannot exceed the maximum permitted score.")
        if marks < 0 or max_marks <= 0:
            raise ValueError("Invalid marks or maximum score.")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO marks (student_id, subject_id, exam_type, marks, max_marks)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(student_id, subject_id, exam_type)
                DO UPDATE SET marks = excluded.marks, max_marks = excluded.max_marks
                """,
                (student_id, subject_id, exam_type, float(marks), float(max_marks)),
            )
        self.refresh_internal_average(student_id)

    def student_marks(self, student_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT m.*, s.code AS subject_code, s.name AS subject_name, s.department
                FROM marks m
                JOIN subjects s ON s.id = m.subject_id
                WHERE m.student_id = ?
                ORDER BY s.code
                """,
                (student_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def refresh_internal_average(self, student_id: str) -> float:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT AVG(100.0 * marks / max_marks) AS avg_pct
                FROM marks WHERE student_id = ?
                """,
                (student_id,),
            ).fetchone()
            avg = row["avg_pct"]
            if avg is None:
                student_row = conn.execute(
                    "SELECT internal_examination_marks FROM students WHERE student_id = ?",
                    (student_id,),
                ).fetchone()
                return float(student_row["internal_examination_marks"]) if student_row else 0.0
            avg = round(float(avg), 2)
            conn.execute(
                "UPDATE students SET internal_examination_marks = ?, updated_at = ? WHERE student_id = ?",
                (avg, datetime.now().isoformat(timespec="seconds"), student_id),
            )
            return avg

    def subject_average_marks(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT s.code, s.name, s.department,
                       AVG(100.0 * m.marks / m.max_marks) AS avg_percentage,
                       COUNT(m.id) AS entries
                FROM subjects s
                JOIN marks m ON m.subject_id = s.id
                GROUP BY s.id
                ORDER BY s.department, s.code
                """
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ assignments
    def upsert_assignment(
        self,
        student_id: str,
        subject_id: int,
        title: str,
        score: float,
        max_score: float,
    ) -> None:
        if score > max_score:
            raise ValueError("Assignment score cannot exceed the maximum permitted score.")
        if score < 0 or max_score <= 0:
            raise ValueError("Invalid assignment score.")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO assignments (student_id, subject_id, title, score, max_score, submitted_on)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, subject_id, title)
                DO UPDATE SET score = excluded.score, max_score = excluded.max_score,
                              submitted_on = excluded.submitted_on
                """,
                (
                    student_id,
                    subject_id,
                    title.strip(),
                    float(score),
                    float(max_score),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        self.refresh_assignment_average(student_id)

    def student_assignments(self, student_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT a.*, s.code AS subject_code, s.name AS subject_name
                FROM assignments a
                JOIN subjects s ON s.id = a.subject_id
                WHERE a.student_id = ?
                ORDER BY a.submitted_on DESC
                """,
                (student_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def refresh_assignment_average(self, student_id: str) -> float:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT AVG(100.0 * score / max_score) AS avg_pct
                FROM assignments WHERE student_id = ?
                """,
                (student_id,),
            ).fetchone()
            avg = row["avg_pct"]
            if avg is None:
                student_row = conn.execute(
                    "SELECT assignment_score FROM students WHERE student_id = ?",
                    (student_id,),
                ).fetchone()
                return float(student_row["assignment_score"]) if student_row else 0.0
            avg = round(float(avg), 2)
            conn.execute(
                "UPDATE students SET assignment_score = ?, updated_at = ? WHERE student_id = ?",
                (avg, datetime.now().isoformat(timespec="seconds"), student_id),
            )
            return avg

    # ------------------------------------------------------------------ predictions
    def save_prediction(
        self,
        student_id: str,
        category: str,
        probabilities: dict[str, float],
        recommendations: str,
        reason: str,
        model_version: str,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO predictions (
                    student_id, predicted_category, probabilities_json,
                    recommendations, reason, model_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    category,
                    json.dumps(probabilities),
                    recommendations,
                    reason,
                    model_version,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

    def latest_prediction(self, student_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM predictions
                WHERE student_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (student_id,),
            ).fetchone()
            return dict(row) if row else None

    def latest_predictions_all(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT p.*, st.full_name, st.department, st.semester, st.section,
                       st.attendance_percentage, st.internal_examination_marks, st.assignment_score
                FROM predictions p
                JOIN students st ON st.student_id = p.student_id
                WHERE p.id = (
                    SELECT p2.id
                    FROM predictions p2
                    WHERE p2.student_id = p.student_id
                    ORDER BY p2.created_at DESC, p2.id DESC
                    LIMIT 1
                )
                ORDER BY st.student_id
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def prediction_category_counts(self) -> dict[str, int]:
        counts = {"Excellent": 0, "Good": 0, "Average": 0, "At Risk": 0}
        for row in self.latest_predictions_all():
            cat = row["predicted_category"]
            if cat in counts:
                counts[cat] += 1
        return counts

    # ------------------------------------------------------------------ seeding
    def seed_demonstration_data(self) -> None:
        """Insert labeled demonstration records. These are not real institutional data."""
        subjects_spec = [
            ("CS301", "Data Structures", "CSE", 3),
            ("CS302", "Database Systems", "CSE", 3),
            ("CS303", "Operating Systems", "CSE", 3),
            ("EC301", "Digital Electronics", "ECE", 3),
            ("EC302", "Signals and Systems", "ECE", 3),
            ("ME301", "Thermodynamics", "ME", 3),
            ("ME302", "Strength of Materials", "ME", 3),
            ("CE301", "Structural Analysis", "Civil", 3),
            ("EE301", "Electrical Machines", "EEE", 3),
            ("HS301", "Professional Communication", "CSE", 3),
        ]
        with self.connection() as conn:
            existing = conn.execute("SELECT COUNT(*) AS c FROM subjects").fetchone()["c"]
        if existing == 0:
            for code, name, dept, sem in subjects_spec:
                self.add_subject(code, name, dept, sem, 100)

        demo_students = [
            ("CSE23001", "Aarav Sharma", "CSE", "A", 92, 88, 90, 85, 6.5, "Excellent"),
            ("CSE23002", "Diya Patel", "CSE", "A", 88, 81, 84, 79, 5.5, "Good"),
            ("CSE23003", "Rohan Mehta", "CSE", "B", 71, 64, 68, 62, 3.5, "Average"),
            ("CSE23004", "Ananya Iyer", "CSE", "B", 58, 42, 48, 51, 2.0, "At Risk"),
            ("CSE23005", "Vikram Nair", "CSE", "A", 96, 93, 91, 90, 7.5, "Excellent"),
            ("ECE23001", "Sneha Reddy", "ECE", "A", 84, 77, 80, 74, 5.0, "Good"),
            ("ECE23002", "Karthik Rao", "ECE", "B", 69, 58, 61, 60, 3.0, "Average"),
            ("ECE23003", "Meera Joshi", "ECE", "A", 54, 39, 44, 47, 1.8, "At Risk"),
            ("ME23001", "Arjun Das", "ME", "A", 90, 86, 83, 82, 6.0, "Excellent"),
            ("ME23002", "Pooja Kulkarni", "ME", "B", 76, 72, 70, 69, 4.2, "Good"),
            ("ME23003", "Nikhil Verma", "ME", "A", 61, 49, 52, 55, 2.5, "At Risk"),
            ("CIV23001", "Ishita Banerjee", "Civil", "A", 87, 80, 82, 78, 5.4, "Good"),
            ("CIV23002", "Rahul Gupta", "Civil", "B", 73, 66, 64, 63, 3.8, "Average"),
            ("EEE23001", "Fatima Khan", "EEE", "A", 91, 89, 88, 86, 6.8, "Excellent"),
            ("EEE23002", "Siddharth Menon", "EEE", "B", 66, 54, 57, 58, 2.8, "Average"),
            ("CSE23006", "Neha Chawla", "CSE", "C", 80, 75, 78, 73, 4.8, "Good"),
            ("CSE23007", "Aditya Bansal", "CSE", "C", 47, 36, 40, 42, 1.5, "At Risk"),
            ("ECE23004", "Lakshmi Krishnan", "ECE", "C", 82, 79, 77, 76, 5.2, "Good"),
        ]

        subjects = self.list_subjects()
        subjects_by_dept: dict[str, list[dict[str, Any]]] = {}
        for subject in subjects:
            subjects_by_dept.setdefault(subject["department"], []).append(subject)
        # Professional Communication is stored under CSE; reuse it for all departments.
        common = [s for s in subjects if s["code"] == "HS301"]

        today = datetime.now().date()
        for idx, (sid, name, dept, section, att, marks, assign, prev, hours, _label) in enumerate(demo_students):
            if self.student_exists(sid):
                continue
            self.add_student(
                {
                    "student_id": sid,
                    "full_name": name,
                    "email": f"{sid.lower()}@edupredict.edu",
                    "department": dept,
                    "semester": 3,
                    "section": section,
                    "phone": f"98765{10000 + idx:05d}"[-10:],
                    "attendance_percentage": att,
                    "internal_examination_marks": marks,
                    "assignment_score": assign,
                    "previous_semester_performance": prev,
                    "study_hours": hours,
                }
            )
            dept_subjects = subjects_by_dept.get(dept, []) + common
            # Keep unique subjects
            seen = set()
            unique_subjects = []
            for subj in dept_subjects:
                if subj["id"] not in seen:
                    seen.add(subj["id"])
                    unique_subjects.append(subj)

            present_days = int(round(att / 10))  # 10 session days
            for day in range(10):
                date_str = (today - timedelta(days=12 - day)).isoformat()
                status = "Present" if day < present_days else "Absent"
                for subj in unique_subjects[:3]:
                    self.record_attendance(sid, subj["id"], date_str, status)

            for subj in unique_subjects[:3]:
                variation = (hash(sid + subj["code"]) % 7) - 3
                score = min(100, max(0, marks + variation))
                self.upsert_mark(sid, subj["id"], score, 100, "Internal")
                self.upsert_assignment(
                    sid,
                    subj["id"],
                    f"{subj['code']} Assignment 1",
                    min(100, max(0, assign + variation)),
                    100,
                )
