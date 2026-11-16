"""Load the trained Random Forest model and produce predictions plus recommendations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from config import FEATURE_COLUMNS, FEATURE_COLUMNS_PATH, METRICS_PATH, MODEL_PATH
from models.dataset import label_from_features


class ModelNotTrainedError(RuntimeError):
    pass


def build_recommendations(student: dict[str, Any], category: str) -> tuple[str, str]:
    reasons = []
    actions = []
    attendance = float(student.get("attendance_percentage") or 0)
    internals = float(student.get("internal_examination_marks") or 0)
    assignments = float(student.get("assignment_score") or 0)
    previous = float(student.get("previous_semester_performance") or 0)
    hours = float(student.get("study_hours") or 0)

    if attendance < 75:
        reasons.append(f"attendance is {attendance:.1f}% (below 75%)")
        actions.append("Attend remaining lectures regularly and meet the class advisor about shortfall hours.")
    if internals < 50:
        reasons.append(f"internal marks are {internals:.1f}/100")
        actions.append("Revise weak subjects weekly and attempt extra internal practice tests.")
    if assignments < 50:
        reasons.append(f"assignment score is {assignments:.1f}/100")
        actions.append("Submit pending assignments on time and request faculty feedback.")
    if previous < 55:
        reasons.append(f"previous semester performance is {previous:.1f}")
        actions.append("Join peer-study groups for subjects carried forward from last semester.")
    if hours < 3:
        reasons.append(f"reported study hours are {hours:.1f} per day")
        actions.append("Increase focused study time to at least 4 hours each weekday.")

    if category == "Excellent":
        actions.append("Maintain consistency and mentor a peer who needs academic support.")
        reason = "Strong attendance, internals and assignment performance."
        text = "Continue the current study plan. Consider advanced topics and leadership in group projects."
    elif category == "Good":
        reason = "Solid overall performance with room to reach the excellent band."
        text = "Target 85%+ internals in remaining tests and keep attendance above 85%."
        if actions:
            text = " ".join(actions)
    elif category == "Average":
        reason = "; ".join(reasons) if reasons else "Overall academic indicators are in the moderate range."
        text = (
            "Follow a weekly revision timetable, complete all assignments before the deadline, "
            "and meet faculty during office hours for difficult topics."
        )
        if actions:
            text = " ".join(actions)
    else:
        reason = "; ".join(reasons) if reasons else "Multiple academic indicators are below safe thresholds."
        text = (
            "This student may need structured academic support. Recommended actions: "
            + (" ".join(actions) if actions else "meet the mentor, improve attendance, and complete pending work.")
        )
    return reason, text


class PerformancePredictor:
    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self.model = None
        self.feature_columns = FEATURE_COLUMNS
        self.metrics: dict[str, Any] | None = None
        self._load()

    def is_ready(self) -> bool:
        return self.model is not None

    def _load(self) -> None:
        if not self.model_path.exists():
            self.model = None
            return
        self.model = joblib.load(self.model_path)
        if FEATURE_COLUMNS_PATH.exists():
            self.feature_columns = list(joblib.load(FEATURE_COLUMNS_PATH))
        if METRICS_PATH.exists():
            self.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    def reload(self) -> None:
        self._load()
        if not self.is_ready():
            raise ModelNotTrainedError(
                "No trained model was found. Train the model from the Prediction screen or run python -m models.train_model"
            )

    def features_from_student(self, student: dict[str, Any]) -> pd.DataFrame:
        row = {col: float(student.get(col) or 0) for col in self.feature_columns}
        return pd.DataFrame([row], columns=self.feature_columns)

    def predict_student(self, student: dict[str, Any]) -> dict[str, Any]:
        if not self.is_ready():
            raise ModelNotTrainedError(
                "The Random Forest model has not been trained yet. Use Train Model before predicting."
            )
        frame = self.features_from_student(student)
        category = str(self.model.predict(frame)[0])
        proba = {}
        if hasattr(self.model, "predict_proba"):
            values = self.model.predict_proba(frame)[0]
            proba = {cls: float(val) for cls, val in zip(self.model.classes_, values)}
        reason, recommendations = build_recommendations(student, category)
        heuristic = label_from_features(
            float(student.get("attendance_percentage") or 0),
            float(student.get("internal_examination_marks") or 0),
            float(student.get("assignment_score") or 0),
            float(student.get("previous_semester_performance") or 0),
            float(student.get("study_hours") or 0),
        )
        return {
            "predicted_category": category,
            "probabilities": proba,
            "recommendations": recommendations,
            "reason": reason,
            "heuristic_category": heuristic,
            "model_version": (self.metrics or {}).get("trained_at", "unknown"),
            "confidence": max(proba.values()) if proba else None,
        }

    def predict_many(self, students: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Predict a list of students in one model call (safer on Windows than many sequential calls)."""
        if not self.is_ready():
            raise ModelNotTrainedError(
                "The Random Forest model has not been trained yet. Use Train Model before predicting."
            )
        if not students:
            return []
        frame = pd.DataFrame(
            [{col: float(student.get(col) or 0) for col in self.feature_columns} for student in students],
            columns=self.feature_columns,
        )
        categories = [str(value) for value in self.model.predict(frame)]
        proba_rows = None
        if hasattr(self.model, "predict_proba"):
            proba_rows = self.model.predict_proba(frame)
        results = []
        for index, student in enumerate(students):
            category = categories[index]
            proba = {}
            if proba_rows is not None:
                proba = {cls: float(val) for cls, val in zip(self.model.classes_, proba_rows[index])}
            reason, recommendations = build_recommendations(student, category)
            heuristic = label_from_features(
                float(student.get("attendance_percentage") or 0),
                float(student.get("internal_examination_marks") or 0),
                float(student.get("assignment_score") or 0),
                float(student.get("previous_semester_performance") or 0),
                float(student.get("study_hours") or 0),
            )
            results.append(
                {
                    "predicted_category": category,
                    "probabilities": proba,
                    "recommendations": recommendations,
                    "reason": reason,
                    "heuristic_category": heuristic,
                    "model_version": (self.metrics or {}).get("trained_at", "unknown"),
                    "confidence": max(proba.values()) if proba else None,
                }
            )
        return results
