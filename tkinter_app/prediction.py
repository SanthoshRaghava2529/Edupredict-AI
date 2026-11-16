"""ML prediction workspace and at-risk identification."""

from __future__ import annotations

import csv
import tkinter as tk
from tkinter import filedialog, ttk

from config import MODEL_PATH, REPORTS_DIR
from database.db import Database
from models.predictor import ModelNotTrainedError, PerformancePredictor
from models.train_model import train_and_save
from tkinter_app.charting import confusion_heatmap, embed_figure, pie_chart, new_figure
from tkinter_app.theme import ACCENT, ACCENT_HOVER, CONTENT, DANGER, NAVY, SUCCESS, WARNING
from tkinter_app.widgets import Card, DataTable, HoverButton, PageHeader, error, info, warn


class PredictionPage(tk.Frame):
    def __init__(self, master, db: Database) -> None:
        super().__init__(master, bg=CONTENT)
        self.db = db
        self.predictor = PerformancePredictor()
        PageHeader(
            self,
            "Machine learning predictions",
            "Random Forest classifier trained on synthetic demonstration data, then applied to SQLite student records.",
        ).pack(fill="x", padx=24, pady=(20, 8))

        toolbar = Card(self)
        toolbar.pack(fill="x", padx=24, pady=6)
        HoverButton(toolbar.body, NAVY, ACCENT, text="Train / retrain model", command=self._train).pack(side="left", padx=4)
        HoverButton(toolbar.body, ACCENT, ACCENT_HOVER, text="Predict selected student", command=self._predict_one).pack(
            side="left", padx=4
        )
        HoverButton(toolbar.body, ACCENT, ACCENT_HOVER, text="Predict all students", command=self._predict_all).pack(
            side="left", padx=4
        )
        self.status = tk.Label(toolbar.body, text="", bg="white", fg=NAVY)
        self.status.pack(side="left", padx=12)

        body = tk.Frame(self, bg=CONTENT)
        body.pack(fill="both", expand=True, padx=24, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        list_card = Card(body, "Students")
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.table = DataTable(
            list_card.body,
            [
                ("id", "Student ID", 100),
                ("name", "Name", 150),
                ("att", "Att %", 70),
                ("marks", "Internals", 80),
                ("asg", "Assign", 70),
                ("prev", "Prev", 70),
                ("hrs", "Hours", 60),
            ],
            height=14,
        )
        self.table.pack(fill="both", expand=True)

        result_card = Card(body, "Prediction result")
        result_card.grid(row=0, column=1, sticky="nsew")
        self.result_title = tk.Label(result_card.body, text="No prediction yet", bg="white", fg=NAVY, font=("Segoe UI", 16, "bold"))
        self.result_title.pack(anchor="w")
        self.result_meta = tk.Label(result_card.body, text="Train the model if this is the first run.", bg="white", justify="left", wraplength=420)
        self.result_meta.pack(anchor="w", pady=8)
        self.metrics_label = tk.Label(result_card.body, text="", bg="white", justify="left", wraplength=420)
        self.metrics_label.pack(anchor="w", pady=4)
        self.reco = tk.Label(result_card.body, text="", bg="white", justify="left", wraplength=420, fg="#334155")
        self.reco.pack(anchor="w", pady=8)
        self.fig = new_figure(4.6, 2.8)
        self.canvas = embed_figure(result_card.body, self.fig)

        self._refresh_model_status()

    def refresh(self) -> None:
        if MODEL_PATH.exists():
            try:
                self.predictor.reload()
            except ModelNotTrainedError:
                pass
        rows = self.db.list_students()
        self.table.fill(
            [
                (
                    r["student_id"],
                    r["full_name"],
                    f"{r['attendance_percentage']:.1f}",
                    f"{r['internal_examination_marks']:.1f}",
                    f"{r['assignment_score']:.1f}",
                    f"{r['previous_semester_performance']:.1f}",
                    f"{r['study_hours']:.1f}",
                )
                for r in rows
            ]
        )
        self._refresh_model_status()

    def _refresh_model_status(self) -> None:
        if not self.predictor.is_ready():
            self.status.configure(text="Model not trained", fg=DANGER)
            self.metrics_label.configure(
                text="No joblib model found. Click Train / retrain model. Until then, predictions are disabled."
            )
            if hasattr(self, "fig"):
                confusion_heatmap(self.fig, None, [], "Held-out confusion matrix")
                self.canvas.draw()
            return
        metrics = self.predictor.metrics or {}
        self.status.configure(text=f"Model ready · accuracy {metrics.get('accuracy', 0):.3f}", fg=SUCCESS)
        self.metrics_label.configure(
            text=(
                f"Held-out accuracy: {metrics.get('accuracy', 0):.3f}   "
                f"Precision: {metrics.get('precision_weighted', 0):.3f}   "
                f"Recall: {metrics.get('recall_weighted', 0):.3f}   "
                f"F1: {metrics.get('f1_weighted', 0):.3f}\n"
                f"{metrics.get('disclaimer', '')}"
            )
        )
        confusion_heatmap(
            self.fig,
            metrics.get("confusion_matrix"),
            metrics.get("classes") or [],
            "Held-out confusion matrix",
        )
        self.canvas.draw()

    def _train(self) -> None:
        try:
            metrics = train_and_save()
            self.predictor.reload()
            self._refresh_model_status()
            info(
                self,
                "Training complete",
                f"Random Forest saved.\nAccuracy: {metrics['accuracy']:.3f}\n"
                f"F1 (weighted): {metrics['f1_weighted']:.3f}\n\n{metrics['disclaimer']}",
            )
        except Exception as exc:
            error(self, "Training failed", str(exc))

    def _selected_student(self):
        values = self.table.selected_values()
        if not values:
            return None
        return self.db.get_student(values[0])

    def _predict_one(self) -> None:
        student = self._selected_student()
        if not student:
            error(self, "No selection", "Select a student from the table.")
            return
        try:
            result = self.predictor.predict_student(student)
            self.db.save_prediction(
                student["student_id"],
                result["predicted_category"],
                result["probabilities"],
                result["recommendations"],
                result["reason"],
                result["model_version"],
            )
            self._render_result(student, result)
        except ModelNotTrainedError as exc:
            error(self, "Model unavailable", str(exc))
        except Exception as exc:
            error(self, "Prediction failed", str(exc))

    def _predict_all(self) -> None:
        if not self.predictor.is_ready():
            error(self, "Model unavailable", "Train the model before predicting.")
            return
        students = self.db.list_students()
        try:
            results = self.predictor.predict_many(students)
        except ModelNotTrainedError as exc:
            error(self, "Model unavailable", str(exc))
            return
        except Exception as exc:
            error(self, "Prediction failed", str(exc))
            return
        for student, result in zip(students, results):
            self.db.save_prediction(
                student["student_id"],
                result["predicted_category"],
                result["probabilities"],
                result["recommendations"],
                result["reason"],
                result["model_version"],
            )
        info(self, "Batch complete", f"Stored predictions for {len(results)} students.")

    def _render_result(self, student: dict, result: dict) -> None:
        color = {"Excellent": SUCCESS, "Good": ACCENT, "Average": WARNING, "At Risk": DANGER}.get(
            result["predicted_category"], NAVY
        )
        self.result_title.configure(text=result["predicted_category"], fg=color)
        probs = result.get("probabilities") or {}
        prob_text = "   ".join(f"{k}: {v:.2f}" for k, v in probs.items())
        self.result_meta.configure(
            text=(
                f"{student['full_name']} ({student['student_id']})\n"
                f"Reason: {result['reason']}\n"
                f"Class probabilities: {prob_text or 'n/a'}"
            )
        )
        self.reco.configure(text=result["recommendations"])


class AtRiskPage(tk.Frame):
    def __init__(self, master, db: Database) -> None:
        super().__init__(master, bg=CONTENT)
        self.db = db
        self.predictor = PerformancePredictor()
        PageHeader(
            self,
            "At-risk student identification",
            "Combines the trained classifier with transparent attendance and marks thresholds.",
        ).pack(fill="x", padx=24, pady=(20, 8))

        toolbar = Card(self)
        toolbar.pack(fill="x", padx=24)
        self.filter_var = tk.StringVar(value="All concerns")
        ttk.Combobox(
            toolbar.body,
            textvariable=self.filter_var,
            values=["All concerns", "ML: At Risk", "Attendance alert", "Low internals"],
            state="readonly",
            width=22,
        ).pack(side="left")
        HoverButton(toolbar.body, ACCENT, ACCENT_HOVER, text="Refresh list", command=self.refresh).pack(side="left", padx=8)
        HoverButton(toolbar.body, NAVY, ACCENT, text="Export CSV", command=self._export).pack(side="left", padx=4)

        split = tk.Frame(self, bg=CONTENT)
        split.pack(fill="both", expand=True, padx=24, pady=10)
        split.grid_columnconfigure(0, weight=3)
        split.grid_columnconfigure(1, weight=2)
        split.grid_rowconfigure(0, weight=1)

        table_card = Card(split, "Students who may need support")
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.table = DataTable(
            table_card.body,
            [
                ("id", "Student ID", 100),
                ("name", "Name", 150),
                ("att", "Attendance", 90),
                ("marks", "Internals", 80),
                ("asg", "Assignments", 90),
                ("pred", "Predicted", 90),
                ("why", "Reason for concern", 240),
            ],
            height=14,
        )
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", lambda _e: self._show_actions())

        side = Card(split, "Suggested improvement actions")
        side.grid(row=0, column=1, sticky="nsew")
        self.actions = tk.Label(side.body, text="Select a student.", bg="white", wraplength=320, justify="left")
        self.actions.pack(anchor="w")
        self.fig = new_figure(4.4, 2.6)
        self.canvas = embed_figure(side.body, self.fig)
        self._rows: list[dict] = []

    def refresh(self) -> None:
        if MODEL_PATH.exists() and not self.predictor.is_ready():
            try:
                self.predictor.reload()
            except ModelNotTrainedError:
                pass
        threshold = self.db.get_attendance_threshold()
        students = self.db.list_students()
        missing = [s for s in students if self.db.latest_prediction(s["student_id"]) is None]
        if missing and self.predictor.is_ready():
            try:
                for student, result in zip(missing, self.predictor.predict_many(missing)):
                    self.db.save_prediction(
                        student["student_id"],
                        result["predicted_category"],
                        result["probabilities"],
                        result["recommendations"],
                        result["reason"],
                        result["model_version"],
                    )
            except Exception:
                pass
        combined = []
        for student in students:
            prediction = self.db.latest_prediction(student["student_id"])
            category = prediction["predicted_category"] if prediction else None
            reasons = []
            if category == "At Risk":
                reasons.append("ML category: At Risk")
            if student["attendance_percentage"] < threshold:
                reasons.append(f"attendance {student['attendance_percentage']:.1f}% < {threshold:.0f}%")
            if student["internal_examination_marks"] < 50:
                reasons.append(f"internals {student['internal_examination_marks']:.1f}")
            if student["assignment_score"] < 50:
                reasons.append(f"assignments {student['assignment_score']:.1f}")
            if not reasons:
                continue
            combined.append(
                {
                    **student,
                    "predicted_category": category or "Not predicted",
                    "reason": "; ".join(reasons),
                    "recommendations": (prediction or {}).get("recommendations", "Meet the academic advisor."),
                }
            )

        choice = self.filter_var.get()
        if choice == "ML: At Risk":
            combined = [r for r in combined if r["predicted_category"] == "At Risk"]
        elif choice == "Attendance alert":
            combined = [r for r in combined if f"< {threshold:.0f}%" in r["reason"]]
        elif choice == "Low internals":
            combined = [r for r in combined if "internals" in r["reason"]]

        self._rows = combined
        self.table.fill(
            [
                (
                    r["student_id"],
                    r["full_name"],
                    f"{r['attendance_percentage']:.1f}",
                    f"{r['internal_examination_marks']:.1f}",
                    f"{r['assignment_score']:.1f}",
                    r["predicted_category"],
                    r["reason"],
                )
                for r in combined
            ]
        )
        counts = {"At Risk": 0, "Attendance": 0, "Low internals": 0}
        for row in combined:
            if row["predicted_category"] == "At Risk":
                counts["At Risk"] += 1
            if "attendance" in row["reason"]:
                counts["Attendance"] += 1
            if "internals" in row["reason"]:
                counts["Low internals"] += 1
        pie_chart(self.fig, list(counts.keys()), list(counts.values()), "Concern mix")
        self.canvas.draw()

    def _show_actions(self) -> None:
        values = self.table.selected_values()
        if not values:
            return
        match = next((r for r in self._rows if r["student_id"] == values[0]), None)
        if match:
            self.actions.configure(text=f"{match['full_name']}\n\n{match['recommendations']}")

    def _export(self) -> None:
        if not self._rows:
            warn(self, "Nothing to export", "Refresh the list first.")
            return
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir=REPORTS_DIR,
            filetypes=[("CSV", "*.csv")],
            initialfile="at_risk_students.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "student_id",
                    "full_name",
                    "attendance_percentage",
                    "internal_examination_marks",
                    "assignment_score",
                    "predicted_category",
                    "reason",
                    "recommendations",
                ],
            )
            writer.writeheader()
            for row in self._rows:
                writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
        info(self, "Exported", path)
