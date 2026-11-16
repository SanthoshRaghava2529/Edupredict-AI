"""Student-facing dashboard restricted to the signed-in student."""

from __future__ import annotations

import tkinter as tk

from database.db import Database
from models.predictor import ModelNotTrainedError, PerformancePredictor
from tkinter_app.reports import generate_student_report
from tkinter_app.session import Session
from tkinter_app.theme import ACCENT, ACCENT_HOVER, CONTENT, DANGER, NAVY, SUCCESS, WARNING
from tkinter_app.widgets import Card, DataTable, HoverButton, PageHeader, StatCard, error, info


class StudentPortal(tk.Frame):
    def __init__(self, master, db: Database, session: Session) -> None:
        super().__init__(master, bg=CONTENT)
        self.db = db
        self.session = session
        self.predictor = PerformancePredictor()
        PageHeader(self, "My academic workspace", "You can only view your own records.").pack(
            fill="x", padx=24, pady=(20, 8)
        )

        self.cards = tk.Frame(self, bg=CONTENT)
        self.cards.pack(fill="x", padx=24, pady=8)
        for i in range(4):
            self.cards.grid_columnconfigure(i, weight=1)
        self.att_card = StatCard(self.cards, "Attendance", "—", "Overall percentage", ACCENT)
        self.mark_card = StatCard(self.cards, "Internal marks", "—", "Average score", SUCCESS)
        self.asg_card = StatCard(self.cards, "Assignments", "—", "Average score", ACCENT)
        self.prev_card = StatCard(self.cards, "Previous semester", "—", "Recorded performance", WARNING)
        for i, card in enumerate((self.att_card, self.mark_card, self.asg_card, self.prev_card)):
            card.grid(row=0, column=i, sticky="nsew", padx=6)

        split = tk.Frame(self, bg=CONTENT)
        split.pack(fill="both", expand=True, padx=24, pady=8)
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, weight=1)

        profile = Card(split, "Personal profile")
        profile.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self.profile_label = tk.Label(profile.body, text="", bg="white", justify="left", font=("Segoe UI", 10))
        self.profile_label.pack(anchor="w")

        pred_card = Card(split, "Predicted performance")
        pred_card.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        self.pred_title = tk.Label(pred_card.body, text="—", bg="white", fg=NAVY, font=("Segoe UI", 18, "bold"))
        self.pred_title.pack(anchor="w")
        self.pred_body = tk.Label(pred_card.body, text="", bg="white", justify="left", wraplength=420)
        self.pred_body.pack(anchor="w", pady=8)
        HoverButton(pred_card.body, ACCENT, ACCENT_HOVER, text="Refresh my prediction", command=self._predict).pack(anchor="w")
        HoverButton(pred_card.body, NAVY, ACCENT, text="Download my PDF report", command=self._report).pack(anchor="w", pady=6)

        marks_card = Card(split, "Subject-wise marks")
        marks_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.marks_table = DataTable(
            marks_card.body,
            [("code", "Code", 80), ("name", "Subject", 180), ("marks", "Marks", 70), ("max", "Max", 60)],
            height=8,
        )
        self.marks_table.pack(fill="both", expand=True)

        asg_card = Card(split, "Assignment performance")
        asg_card.grid(row=1, column=1, sticky="nsew")
        self.asg_table = DataTable(
            asg_card.body,
            [("title", "Title", 160), ("subject", "Subject", 80), ("score", "Score", 70), ("max", "Max", 60)],
            height=5,
        )
        self.asg_table.pack(fill="both", expand=True)
        hist_card = Card(split, "Recent attendance")
        hist_card.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        self.hist_table = DataTable(
            hist_card.body,
            [("date", "Date", 110), ("subject", "Subject", 120), ("status", "Status", 90)],
            height=6,
        )
        self.hist_table.pack(fill="both", expand=True)

    def _student(self) -> dict | None:
        if not self.session.student_id:
            return None
        return self.db.get_student(self.session.student_id)

    def refresh(self) -> None:
        student = self._student()
        if not student:
            error(self, "Profile missing", "No student record is linked to this login.")
            return
        self.att_card.update_values(f"{student['attendance_percentage']:.1f}%")
        self.mark_card.update_values(f"{student['internal_examination_marks']:.1f}")
        self.asg_card.update_values(f"{student['assignment_score']:.1f}")
        self.prev_card.update_values(f"{student['previous_semester_performance']:.1f}")
        self.profile_label.configure(
            text=(
                f"{student['full_name']}\n"
                f"ID: {student['student_id']}\n"
                f"{student['department']}  ·  Semester {student['semester']}  ·  Section {student['section']}\n"
                f"{student['email']}\n{student['phone']}\n"
                f"Study hours / day: {student['study_hours']:.1f}"
            )
        )
        marks = self.db.student_marks(student["student_id"])
        self.marks_table.fill(
            [(m["subject_code"], m["subject_name"], f"{m['marks']:.1f}", f"{m['max_marks']:.0f}") for m in marks]
        )
        assignments = self.db.student_assignments(student["student_id"])
        self.asg_table.fill(
            [(a["title"], a["subject_code"], f"{a['score']:.1f}", f"{a['max_score']:.0f}") for a in assignments]
        )
        history = self.db.attendance_history(student["student_id"])[:20]
        self.hist_table.fill([(h["attendance_date"], h["subject_code"], h["status"]) for h in history])
        stored = self.db.latest_prediction(student["student_id"])
        if stored:
            self._show_prediction(stored["predicted_category"], stored["recommendations"], stored.get("reason") or "")
        else:
            self.pred_title.configure(text="Not generated yet", fg=NAVY)
            self.pred_body.configure(text="Click Refresh my prediction to run the trained model on your record.")

    def _show_prediction(self, category: str, recommendations: str, reason: str) -> None:
        color = {"Excellent": SUCCESS, "Good": ACCENT, "Average": WARNING, "At Risk": DANGER}.get(category, NAVY)
        self.pred_title.configure(text=category, fg=color)
        self.pred_body.configure(text=f"{reason}\n\n{recommendations}")

    def _predict(self) -> None:
        student = self._student()
        if not student:
            return
        try:
            if not self.predictor.is_ready():
                self.predictor.reload()
            result = self.predictor.predict_student(student)
            self.db.save_prediction(
                student["student_id"],
                result["predicted_category"],
                result["probabilities"],
                result["recommendations"],
                result["reason"],
                result["model_version"],
            )
            self._show_prediction(result["predicted_category"], result["recommendations"], result["reason"])
        except ModelNotTrainedError as exc:
            error(self, "Model unavailable", str(exc))
        except Exception as exc:
            error(self, "Prediction failed", str(exc))

    def _report(self) -> None:
        student = self._student()
        if not student:
            return
        try:
            path = generate_student_report(self.db, student["student_id"])
            info(self, "Report saved", str(path))
        except Exception as exc:
            error(self, "Report failed", str(exc))
