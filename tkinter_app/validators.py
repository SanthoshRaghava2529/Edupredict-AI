"""Shared input validation for student, marks and authentication forms."""

from __future__ import annotations

import re
from typing import Any

from config import DEPARTMENTS, MAX_STUDY_HOURS, PASSWORD_MIN_LENGTH, SECTIONS, SEMESTERS

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
STUDENT_ID_RE = re.compile(r"^[A-Za-z0-9]{3,20}$")
PHONE_RE = re.compile(r"^[0-9]{10}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .']{1,79}$")


class ValidationError(ValueError):
    pass


def require(value: str, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValidationError(f"{field} is required.")
    return text


def validate_student_id(value: str) -> str:
    text = require(value, "Student ID").upper()
    if not STUDENT_ID_RE.match(text):
        raise ValidationError("Student ID must be 3-20 letters or digits with no spaces.")
    return text


def validate_name(value: str) -> str:
    text = require(value, "Full name")
    if not NAME_RE.match(text):
        raise ValidationError("Full name should contain letters and spaces only.")
    return text


def validate_email(value: str) -> str:
    text = require(value, "Email").lower()
    if not EMAIL_RE.match(text):
        raise ValidationError("Enter a valid email address.")
    return text


def validate_phone(value: str) -> str:
    text = require(value, "Phone number")
    if not PHONE_RE.match(text):
        raise ValidationError("Phone number must be exactly 10 digits.")
    return text


def validate_department(value: str) -> str:
    text = require(value, "Department")
    if text not in DEPARTMENTS:
        raise ValidationError("Select a valid department.")
    return text


def validate_section(value: str) -> str:
    text = require(value, "Section").upper()
    if text not in SECTIONS:
        raise ValidationError("Select a valid section.")
    return text


def validate_semester(value: Any) -> int:
    try:
        semester = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Semester must be a number from 1 to 8.")
    if semester not in SEMESTERS:
        raise ValidationError("Semester must be between 1 and 8.")
    return semester


def validate_percentage(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number.")
    if number < 0 or number > 100:
        raise ValidationError(f"{field} must be between 0 and 100.")
    return round(number, 2)


def validate_study_hours(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError("Study hours must be a number.")
    if number < 0 or number > MAX_STUDY_HOURS:
        raise ValidationError(f"Study hours must be between 0 and {MAX_STUDY_HOURS}.")
    return round(number, 2)


def validate_score(value: Any, maximum: Any, field: str = "Score") -> tuple[float, float]:
    try:
        score = float(value)
        max_score = float(maximum)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} and maximum must be numbers.")
    if max_score <= 0:
        raise ValidationError("Maximum score must be greater than zero.")
    if score < 0:
        raise ValidationError(f"{field} cannot be negative.")
    if score > max_score:
        raise ValidationError(f"{field} cannot exceed the maximum of {max_score}.")
    return round(score, 2), round(max_score, 2)


def validate_password(password: str, confirm: str | None = None) -> str:
    text = password or ""
    if len(text) < PASSWORD_MIN_LENGTH:
        raise ValidationError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if not re.search(r"[A-Z]", text) or not re.search(r"[a-z]", text) or not re.search(r"[0-9]", text):
        raise ValidationError("Password must include uppercase, lowercase and a number.")
    if confirm is not None and text != confirm:
        raise ValidationError("Password confirmation does not match.")
    return text


def student_payload(form: dict[str, Any]) -> dict[str, Any]:
    return {
        "student_id": validate_student_id(form["student_id"]),
        "full_name": validate_name(form["full_name"]),
        "email": validate_email(form["email"]),
        "department": validate_department(form["department"]),
        "semester": validate_semester(form["semester"]),
        "section": validate_section(form["section"]),
        "phone": validate_phone(form["phone"]),
        "attendance_percentage": validate_percentage(form.get("attendance_percentage", 0), "Attendance"),
        "internal_examination_marks": validate_percentage(
            form.get("internal_examination_marks", 0), "Internal marks"
        ),
        "assignment_score": validate_percentage(form.get("assignment_score", 0), "Assignment score"),
        "previous_semester_performance": validate_percentage(
            form.get("previous_semester_performance", 0), "Previous semester performance"
        ),
        "study_hours": validate_study_hours(form.get("study_hours", 0)),
    }
