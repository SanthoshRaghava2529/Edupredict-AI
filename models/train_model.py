"""Train a Random Forest classifier and persist evaluation metrics."""

from __future__ import annotations

import json
from datetime import datetime

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from pathlib import Path

from config import FEATURE_COLUMNS, FEATURE_COLUMNS_PATH, METRICS_PATH, MODEL_PATH
from models.dataset import generate_dataset, load_training_frame, save_datasets


def _assert_no_leakage(frame) -> None:
    leaked = [col for col in FEATURE_COLUMNS if col in {"performance_category", "student_id", "full_name", "data_source"}]
    if leaked:
        raise ValueError(f"Target or identity columns leaked into features: {leaked}")
    if frame["performance_category"].nunique() < 2:
        raise ValueError("Training labels do not contain more than one class.")


def train_and_save(
    random_state: int = 42,
    *,
    n_samples: int = 2500,
    persist_csv: bool = True,
    model_path: Path | None = None,
    metrics_path: Path | None = None,
    feature_path: Path | None = None,
) -> dict:
    if persist_csv:
        save_datasets()
        frame = load_training_frame()
    else:
        frame = generate_dataset(n_samples, seed=random_state)
    _assert_no_leakage(frame)
    x = frame[FEATURE_COLUMNS]
    y = frame["performance_category"]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.20, random_state=random_state, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=220,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=1,
    )
    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)

    labels = list(model.classes_)
    metrics = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "model_type": "RandomForestClassifier",
        "n_estimators": 220,
        "training_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "feature_columns": FEATURE_COLUMNS,
        "classes": labels,
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision_weighted": float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
        "recall_weighted": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
        "f1_weighted": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
        "classification_report": classification_report(y_test, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=labels).tolist(),
        "feature_importances": {
            name: float(value) for name, value in zip(FEATURE_COLUMNS, model.feature_importances_)
        },
        "data_source": "synthetic_demonstration",
        "disclaimer": (
            "Metrics are measured on a held-out split of synthetic demonstration data. "
            "They are not a claim of production accuracy on real institutional records."
        ),
    }

    model_path = Path(model_path or MODEL_PATH)
    metrics_path = Path(metrics_path or METRICS_PATH)
    feature_path = Path(feature_path or FEATURE_COLUMNS_PATH)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    joblib.dump(FEATURE_COLUMNS, feature_path)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    metrics = train_and_save()
    print("Model trained and saved to", MODEL_PATH)
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision (weighted): {metrics['precision_weighted']:.4f}")
    print(f"Recall (weighted): {metrics['recall_weighted']:.4f}")
    print(f"F1 (weighted): {metrics['f1_weighted']:.4f}")
    print("\nClassification report:\n")
    print(metrics["classification_report"])
    print("Confusion matrix (rows=true, cols=predicted, labels=", metrics["classes"], "):")
    print(np.array(metrics["confusion_matrix"]))
    print("\n", metrics["disclaimer"])


if __name__ == "__main__":
    main()
