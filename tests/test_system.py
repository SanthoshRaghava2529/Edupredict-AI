"""Automated checks for database, auth, validation, ML and reports."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, FEATURE_COLUMNS, MODEL_PATH
from database.db import Database
from database.security import hash_password, verify_password
from models.dataset import generate_dataset, label_from_features
from models.predictor import PerformancePredictor, build_recommendations
from models.train_model import train_and_save
from tkinter_app.reports import generate_class_report, generate_student_report
from tkinter_app.session import Session
from tkinter_app.validators import ValidationError, student_payload, validate_password, validate_score


class SecurityTests(unittest.TestCase):
    def test_password_hash_is_not_plaintext(self) -> None:
        hashed = hash_password("Admin@123")
        self.assertNotIn("Admin@123", hashed)
        self.assertTrue(verify_password("Admin@123", hashed))
        self.assertFalse(verify_password("wrong", hashed))


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "test.db", seed_demo=False)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_default_admin_and_login(self) -> None:
        user = self.db.authenticate(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD)
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "admin")
        self.assertEqual(user["must_change_password"], 1)
        self.assertIsNone(self.db.authenticate("admin", "wrong-pass"))

    def test_student_crud_and_duplicate_id(self) -> None:
        payload = {
            "student_id": "CSE99901",
            "full_name": "Test Student",
            "email": "cse99901@edupredict.edu",
            "department": "CSE",
            "semester": 3,
            "section": "A",
            "phone": "9998887776",
            "attendance_percentage": 80,
            "internal_examination_marks": 70,
            "assignment_score": 72,
            "previous_semester_performance": 68,
            "study_hours": 4,
        }
        self.db.add_student(payload)
        self.assertTrue(self.db.student_exists("CSE99901"))
        login = self.db.authenticate("CSE99901", "Student@123")
        self.assertIsNotNone(login)
        self.assertEqual(login["role"], "student")
        with self.assertRaises(Exception):
            self.db.add_student(payload)
        self.db.update_student("CSE99901", {"full_name": "Test Student Updated"})
        self.assertEqual(self.db.get_student("CSE99901")["full_name"], "Test Student Updated")
        self.db.delete_student("CSE99901")
        self.assertIsNone(self.db.get_student("CSE99901"))
        self.assertIsNone(self.db.authenticate("CSE99901", "Student@123"))

    def test_attendance_percentage(self) -> None:
        self.db.add_student(
            {
                "student_id": "CSE99902",
                "full_name": "Attend Student",
                "email": "cse99902@edupredict.edu",
                "department": "CSE",
                "semester": 3,
                "section": "A",
                "phone": "9998887775",
                "attendance_percentage": 0,
                "internal_examination_marks": 60,
                "assignment_score": 60,
                "previous_semester_performance": 60,
                "study_hours": 3,
            }
        )
        subject_id = self.db.add_subject("CS999", "Test Subject", "CSE", 3, 100)
        self.db.record_attendance("CSE99902", subject_id, "2026-01-01", "Present")
        self.db.record_attendance("CSE99902", subject_id, "2026-01-02", "Present")
        self.db.record_attendance("CSE99902", subject_id, "2026-01-03", "Absent")
        self.db.record_attendance("CSE99902", subject_id, "2026-01-04", "Present")
        pct = self.db.refresh_attendance_percentage("CSE99902")
        self.assertEqual(pct, 75.0)
        self.db.set_attendance_threshold(80)
        low = self.db.low_attendance_students()
        self.assertTrue(any(s["student_id"] == "CSE99902" for s in low))

    def test_marks_validation_and_average(self) -> None:
        self.db.add_student(
            {
                "student_id": "CSE99903",
                "full_name": "Marks Student",
                "email": "cse99903@edupredict.edu",
                "department": "CSE",
                "semester": 3,
                "section": "B",
                "phone": "9998887774",
                "attendance_percentage": 90,
                "internal_examination_marks": 0,
                "assignment_score": 0,
                "previous_semester_performance": 70,
                "study_hours": 5,
            }
        )
        sid = self.db.add_subject("CS998", "Algorithms", "CSE", 3, 100)
        with self.assertRaises(ValueError):
            self.db.upsert_mark("CSE99903", sid, 120, 100)
        self.db.upsert_mark("CSE99903", sid, 80, 100)
        sid2 = self.db.add_subject("CS997", "Networks", "CSE", 3, 50)
        self.db.upsert_mark("CSE99903", sid2, 40, 50)
        avg = self.db.refresh_internal_average("CSE99903")
        self.assertEqual(avg, 80.0)
        stats = self.db.dashboard_stats()
        self.assertEqual(stats["total_students"], 1)
        self.assertGreater(stats["avg_marks"], 0)

    def test_class_stats_and_student_isolation(self) -> None:
        self.db.seed_demonstration_data()
        cse = self.db.class_stats(department="CSE", semester=3)
        self.assertGreater(cse["student_count"], 0)
        self.assertTrue(all(s["department"] == "CSE" for s in self.db.list_students(department="CSE")))
        student = self.db.get_student("CSE23001")
        other = self.db.get_student("ECE23001")
        self.assertIsNotNone(student)
        self.assertIsNotNone(other)
        self.assertNotEqual(student["student_id"], other["student_id"])
        user = self.db.authenticate("CSE23001", "Student@123")
        self.assertEqual(user["student_id"], "CSE23001")
        self.assertEqual(user["role"], "student")


class ValidationTests(unittest.TestCase):
    def test_student_payload_and_password_rules(self) -> None:
        with self.assertRaises(ValidationError):
            student_payload(
                {
                    "student_id": "x",
                    "full_name": "A",
                    "email": "bad",
                    "department": "CSE",
                    "semester": 3,
                    "section": "A",
                    "phone": "123",
                    "attendance_percentage": 120,
                    "internal_examination_marks": 10,
                    "assignment_score": 10,
                    "previous_semester_performance": 10,
                    "study_hours": 2,
                }
            )
        with self.assertRaises(ValidationError):
            validate_score(40, 30, "Marks")
        validate_password("NewPass12", "NewPass12")
        with self.assertRaises(ValidationError):
            validate_password("short", "short")


class MachineLearningTests(unittest.TestCase):
    def test_dataset_and_model_are_real(self) -> None:
        frame = generate_dataset(400, seed=7)
        self.assertTrue(set(FEATURE_COLUMNS).issubset(frame.columns))
        self.assertIn("synthetic_demonstration", set(frame["data_source"]))
        self.assertGreaterEqual(frame["performance_category"].nunique(), 3)
        sample = frame.iloc[0]
        self.assertIsInstance(
            label_from_features(
                sample.attendance_percentage,
                sample.internal_examination_marks,
                sample.assignment_score,
                sample.previous_semester_performance,
                sample.study_hours,
            ),
            str,
        )

        metrics = train_and_save()
        self.assertGreater(metrics["accuracy"], 0.75)
        self.assertLess(metrics["accuracy"], 1.0000001)
        self.assertIn("classification_report", metrics)
        predictor = PerformancePredictor()
        self.assertTrue(predictor.is_ready())
        result = predictor.predict_student(
            {
                "attendance_percentage": 95,
                "internal_examination_marks": 92,
                "assignment_score": 90,
                "previous_semester_performance": 88,
                "study_hours": 7,
            }
        )
        self.assertIn(result["predicted_category"], ["Excellent", "Good", "Average", "At Risk"])
        self.assertTrue(result["probabilities"])
        batch = predictor.predict_many(
            [
                {
                    "attendance_percentage": 40,
                    "internal_examination_marks": 35,
                    "assignment_score": 30,
                    "previous_semester_performance": 42,
                    "study_hours": 1,
                },
                {
                    "attendance_percentage": 95,
                    "internal_examination_marks": 92,
                    "assignment_score": 90,
                    "previous_semester_performance": 88,
                    "study_hours": 7,
                },
            ]
        )
        self.assertEqual(len(batch), 2)
        self.assertIn(batch[0]["predicted_category"], ["Excellent", "Good", "Average", "At Risk"])


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "report.db", seed_demo=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_pdf_generation(self) -> None:
        out_dir = Path(self.tmp.name)
        path = generate_student_report(self.db, "CSE23001", out_dir / "one.pdf")
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 500)
        class_path = generate_class_report(self.db, "CSE", 3, out_dir / "class.pdf")
        self.assertTrue(class_path.exists())


if __name__ == "__main__":
    unittest.main()
