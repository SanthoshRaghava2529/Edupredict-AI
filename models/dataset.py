"""Generate a clearly labeled demonstration educational dataset.

This data is synthetic. It is intended for training and college project
demonstration only. It is not real institutional student data.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import FEATURE_COLUMNS, FULL_DATASET_PATH, SAMPLE_DATASET_PATH


def academic_composite_score(
    attendance: np.ndarray,
    internals: np.ndarray,
    assignments: np.ndarray,
    previous: np.ndarray,
    study_hours: np.ndarray,
) -> np.ndarray:
    hours_scaled = np.clip(study_hours / 12.0 * 100.0, 0, 100)
    return (
        0.25 * attendance
        + 0.30 * internals
        + 0.20 * assignments
        + 0.20 * previous
        + 0.05 * hours_scaled
    )


def label_from_features(
    attendance: float,
    internals: float,
    assignments: float,
    previous: float,
    study_hours: float,
) -> str:
    score = float(
        academic_composite_score(
            np.array([attendance]),
            np.array([internals]),
            np.array([assignments]),
            np.array([previous]),
            np.array([study_hours]),
        )[0]
    )
    if attendance < 65 or internals < 45 or score < 50:
        return "At Risk"
    if score >= 85 and attendance >= 85 and internals >= 82:
        return "Excellent"
    if score >= 70:
        return "Good"
    return "Average"


def generate_dataset(n_samples: int = 2500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # Mix of performance clusters so the classifier has a realistic class balance.
    cluster = rng.choice(["excellent", "good", "average", "risk"], size=n_samples, p=[0.18, 0.32, 0.32, 0.18])

    attendance = np.empty(n_samples)
    internals = np.empty(n_samples)
    assignments = np.empty(n_samples)
    previous = np.empty(n_samples)
    hours = np.empty(n_samples)

    for i, c in enumerate(cluster):
        if c == "excellent":
            attendance[i] = rng.normal(92, 4)
            internals[i] = rng.normal(90, 5)
            assignments[i] = rng.normal(91, 5)
            previous[i] = rng.normal(88, 6)
            hours[i] = rng.normal(7.0, 1.2)
        elif c == "good":
            attendance[i] = rng.normal(82, 6)
            internals[i] = rng.normal(76, 6)
            assignments[i] = rng.normal(78, 6)
            previous[i] = rng.normal(74, 7)
            hours[i] = rng.normal(5.2, 1.1)
        elif c == "average":
            attendance[i] = rng.normal(72, 7)
            internals[i] = rng.normal(62, 7)
            assignments[i] = rng.normal(64, 7)
            previous[i] = rng.normal(61, 8)
            hours[i] = rng.normal(3.6, 1.0)
        else:
            attendance[i] = rng.normal(55, 8)
            internals[i] = rng.normal(40, 8)
            assignments[i] = rng.normal(43, 8)
            previous[i] = rng.normal(45, 9)
            hours[i] = rng.normal(2.0, 0.9)

    attendance = np.clip(attendance, 20, 100)
    internals = np.clip(internals, 15, 100)
    assignments = np.clip(assignments, 15, 100)
    previous = np.clip(previous, 15, 100)
    hours = np.clip(hours, 0.5, 12)

    labels = [
        label_from_features(a, i, s, p, h)
        for a, i, s, p, h in zip(attendance, internals, assignments, previous, hours)
    ]

    # Small label noise keeps evaluation honest (the model should not claim 100% accuracy).
    noise_idx = rng.choice(n_samples, size=max(1, n_samples // 40), replace=False)
    alternatives = ["Excellent", "Good", "Average", "At Risk"]
    noisy = list(labels)
    for idx in noise_idx:
        options = [x for x in alternatives if x != noisy[idx]]
        noisy[idx] = options[int(rng.integers(0, len(options)))]

    frame = pd.DataFrame(
        {
            "attendance_percentage": np.round(attendance, 2),
            "internal_examination_marks": np.round(internals, 2),
            "assignment_score": np.round(assignments, 2),
            "previous_semester_performance": np.round(previous, 2),
            "study_hours": np.round(hours, 2),
            "performance_category": noisy,
            "data_source": "synthetic_demonstration",
        }
    )
    return frame


def save_datasets(full_path: Path = FULL_DATASET_PATH, sample_path: Path = SAMPLE_DATASET_PATH) -> pd.DataFrame:
    frame = generate_dataset()
    full_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(full_path, index=False)
    frame.sample(n=min(200, len(frame)), random_state=42).sort_index().to_csv(sample_path, index=False)
    return frame


def load_training_frame() -> pd.DataFrame:
    if FULL_DATASET_PATH.exists():
        frame = pd.read_csv(FULL_DATASET_PATH)
    else:
        frame = save_datasets()
    if any(col in FEATURE_COLUMNS for col in ("performance_category", "student_id", "full_name")):
        raise ValueError("Feature list includes identity or target columns; refusing to train.")
    required = FEATURE_COLUMNS + ["performance_category"]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"Training dataset is missing columns: {missing}")
    cleaned = frame.dropna(subset=required).copy()
    for col in FEATURE_COLUMNS:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
    cleaned = cleaned.dropna(subset=FEATURE_COLUMNS)
    cleaned = cleaned[(cleaned["attendance_percentage"] >= 0) & (cleaned["attendance_percentage"] <= 100)]
    cleaned = cleaned[(cleaned["internal_examination_marks"] >= 0) & (cleaned["internal_examination_marks"] <= 100)]
    cleaned = cleaned[(cleaned["assignment_score"] >= 0) & (cleaned["assignment_score"] <= 100)]
    cleaned = cleaned[(cleaned["previous_semester_performance"] >= 0) & (cleaned["previous_semester_performance"] <= 100)]
    cleaned = cleaned[(cleaned["study_hours"] >= 0) & (cleaned["study_hours"] <= 16)]
    return cleaned
