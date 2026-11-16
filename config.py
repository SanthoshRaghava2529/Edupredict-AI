"""Application-wide constants for the Student Performance Prediction System."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "AI-Powered Student Performance Prediction System"
APP_SHORT_NAME = "EduPredict AI"
APP_VERSION = "1.1.0"

DATABASE_PATH = PROJECT_ROOT / "database" / "student_performance.db"
MODEL_DIR = PROJECT_ROOT / "models" / "artifacts"
MODEL_PATH = MODEL_DIR / "random_forest_model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
FEATURE_COLUMNS_PATH = MODEL_DIR / "feature_columns.joblib"
SAMPLE_DATASET_PATH = PROJECT_ROOT / "data" / "sample_student_performance.csv"
FULL_DATASET_PATH = PROJECT_ROOT / "data" / "training_student_performance.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@123"
DEFAULT_STUDENT_PASSWORD = "Student@123"

ATTENDANCE_THRESHOLD_DEFAULT = 75.0
WELL_PERFORMING_MARKS = 80.0
ATTENTION_MARKS = 50.0
MAX_MARKS_DEFAULT = 100.0
MAX_STUDY_HOURS = 16.0

FEATURE_COLUMNS = [
    "attendance_percentage",
    "internal_examination_marks",
    "assignment_score",
    "previous_semester_performance",
    "study_hours",
]

PERFORMANCE_CATEGORIES = ["Excellent", "Good", "Average", "At Risk"]

DEPARTMENTS = ["CSE", "ECE", "ME", "Civil", "EEE"]
SECTIONS = ["A", "B", "C"]
SEMESTERS = list(range(1, 9))

PASSWORD_MIN_LENGTH = 8
