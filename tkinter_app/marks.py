"""Examination marks and assignment management."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from config import DEPARTMENTS, SEMESTERS
from database.db import Database
from tkinter_app.charting import embed_figure, horizontal_bar, new_figure
from tkinter_app.theme import ACCENT, ACCENT_HOVER, CONTENT, NAVY, WHITE
from tkinter_app.validators import ValidationError, validate_score
from tkinter_app.widgets import Card, DataTable, HoverButton, PageHeader, error, info


class MarksPage(tk.Frame):
    def __init__(self, master, db: Database) -> None:
        super().__init__(master, bg=CONTENT)
        self.db = db
        self._student_map: dict = {}
        self._subject_map: dict = {}
        PageHeader(
            self,
            "Marks and assignments",
            "Enter subject scores, update internals and compare academic performance.",
        ).pack(fill="x", padx=24, pady=(20, 8))

        layout = tk.Frame(self, bg=CONTENT)
        layout.pack(fill="both", expand=True, padx=24, pady=8)
        layout.grid_columnconfigure(0, weight=1)
        layout.grid_columnconfigure(1, weight=1)

        form_card = Card(layout, "Enter scores")
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        form = form_card.body
        self.student_var = tk.StringVar()
        self.subject_var = tk.StringVar()
        self.marks_var = tk.StringVar()
        self.max_marks_var = tk.StringVar(value="100")
        self.assign_title_var = tk.StringVar(value="Assignment 1")
        self.assign_score_var = tk.StringVar()
        self.assign_max_var = tk.StringVar(value="100")

        tk.Label(form, text="Student", bg=WHITE, fg=NAVY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.student_combo = ttk.Combobox(form, textvariable=self.student_var, state="readonly", width=36)
        self.student_combo.pack(fill="x", pady=(2, 8))
        tk.Label(form, text="Subject", bg=WHITE, fg=NAVY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.subject_combo = ttk.Combobox(form, textvariable=self.subject_var, state="readonly", width=36)
        self.subject_combo.pack(fill="x", pady=(2, 8))

        tk.Label(form, text="Internal marks / maximum", bg=WHITE, fg=NAVY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        row = tk.Frame(form, bg=WHITE)
        row.pack(fill="x", pady=4)
        ttk.Entry(row, textvariable=self.marks_var, width=10).pack(side="left")
        tk.Label(row, text=" / ", bg=WHITE).pack(side="left")
        ttk.Entry(row, textvariable=self.max_marks_var, width=10).pack(side="left")
        HoverButton(row, ACCENT, ACCENT_HOVER, text="Save internal marks", command=self._save_marks).pack(
            side="left", padx=8
        )

        tk.Label(form, text="Assignment title and score / maximum", bg=WHITE, fg=NAVY, font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(8, 0)
        )
        row2 = tk.Frame(form, bg=WHITE)
        row2.pack(fill="x", pady=8)
        ttk.Entry(row2, textvariable=self.assign_title_var, width=16).pack(side="left")
        ttk.Entry(row2, textvariable=self.assign_score_var, width=8).pack(side="left", padx=4)
        tk.Label(row2, text="/", bg=WHITE).pack(side="left")
        ttk.Entry(row2, textvariable=self.assign_max_var, width=8).pack(side="left", padx=4)
        HoverButton(row2, NAVY, ACCENT, text="Save assignment", command=self._save_assignment).pack(side="left", padx=8)

        HoverButton(form, NAVY, ACCENT, text="Load student performance", command=self._load_detail).pack(anchor="w", pady=8)
        HoverButton(form, NAVY, ACCENT, text="Add subject", command=self._add_subject).pack(anchor="w", pady=4)

        detail = Card(layout, "Individual student performance")
        detail.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        self.summary = tk.Label(detail.body, text="Select a student to view subject-wise scores.", bg="white", justify="left")
        self.summary.pack(anchor="w", pady=(0, 8))
        self.marks_table = DataTable(
            detail.body,
            [("code", "Subject", 90), ("name", "Name", 160), ("marks", "Marks", 70), ("max", "Max", 60), ("pct", "%", 60)],
            height=6,
        )
        self.marks_table.pack(fill="x")
        self.assign_table = DataTable(
            detail.body,
            [("title", "Assignment", 140), ("subject", "Subject", 80), ("score", "Score", 70), ("max", "Max", 60)],
            height=5,
        )
        self.assign_table.pack(fill="x", pady=(8, 0))

        chart_card = Card(layout, "Subject-wise average marks")
        chart_card.grid(row=1, column=0, columnspan=2, sticky="nsew")
        layout.grid_rowconfigure(1, weight=1)
        self.fig = new_figure(9.8, 3.0)
        self.canvas = embed_figure(chart_card.body, self.fig)

    def refresh(self) -> None:
        students = self.db.list_students()
        self._student_map = {f"{s['student_id']} — {s['full_name']}": s for s in students}
        self.student_combo["values"] = list(self._student_map)
        subjects = self.db.list_subjects()
        self._subject_map = {f"{s['code']} — {s['name']}": s for s in subjects}
        self.subject_combo["values"] = list(self._subject_map)
        averages = self.db.subject_average_marks()
        labels = [f"{r['code']}" for r in averages] or ["No data"]
        values = [float(r["avg_percentage"] or 0) for r in averages] or [0]
        horizontal_bar(self.fig, labels, values, "Average percentage by subject")
        self.canvas.draw()

    def _add_subject(self) -> None:
        SubjectForm(self, self.db, on_saved=self.refresh)

    def _current_student(self):
        return self._student_map.get(self.student_var.get())

    def _current_subject(self):
        return self._subject_map.get(self.subject_var.get())

    def _save_marks(self) -> None:
        student, subject = self._current_student(), self._current_subject()
        if not student or not subject:
            error(self, "Incomplete", "Select a student and a subject.")
            return
        try:
            score, maximum = validate_score(self.marks_var.get(), self.max_marks_var.get(), "Marks")
            self.db.upsert_mark(student["student_id"], subject["id"], score, maximum, "Internal")
            info(self, "Saved", "Internal marks were stored and the student average was updated.")
            self._load_detail()
            self.refresh()
        except ValidationError as exc:
            error(self, "Validation error", str(exc))
        except Exception as exc:
            error(self, "Save failed", str(exc))

    def _save_assignment(self) -> None:
        student, subject = self._current_student(), self._current_subject()
        if not student or not subject:
            error(self, "Incomplete", "Select a student and a subject.")
            return
        title = self.assign_title_var.get().strip()
        if not title:
            error(self, "Incomplete", "Enter an assignment title.")
            return
        try:
            score, maximum = validate_score(self.assign_score_var.get(), self.assign_max_var.get(), "Assignment score")
            self.db.upsert_assignment(student["student_id"], subject["id"], title, score, maximum)
            info(self, "Saved", "Assignment score stored.")
            self._load_detail()
            self.refresh()
        except ValidationError as exc:
            error(self, "Validation error", str(exc))
        except Exception as exc:
            error(self, "Save failed", str(exc))

    def _load_detail(self) -> None:
        student = self._current_student()
        if not student:
            error(self, "No student", "Select a student first.")
            return
        fresh = self.db.get_student(student["student_id"])
        self.summary.configure(
            text=(
                f"{fresh['full_name']} ({fresh['student_id']})  ·  {fresh['department']} Sem {fresh['semester']}\n"
                f"Average internals: {fresh['internal_examination_marks']:.1f}   "
                f"Assignment average: {fresh['assignment_score']:.1f}   "
                f"Attendance: {fresh['attendance_percentage']:.1f}%"
            )
        )
        marks = self.db.student_marks(fresh["student_id"])
        self.marks_table.fill(
            [
                (
                    m["subject_code"],
                    m["subject_name"],
                    f"{m['marks']:.1f}",
                    f"{m['max_marks']:.0f}",
                    f"{100 * m['marks'] / m['max_marks']:.1f}",
                )
                for m in marks
            ]
        )
        assignments = self.db.student_assignments(fresh["student_id"])
        self.assign_table.fill(
            [
                (a["title"], a["subject_code"], f"{a['score']:.1f}", f"{a['max_score']:.0f}")
                for a in assignments
            ]
        )


class SubjectForm(tk.Toplevel):
    def __init__(self, master, db: Database, on_saved) -> None:
        super().__init__(master)
        self.db = db
        self.on_saved = on_saved
        self.title("Add subject")
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.code = tk.StringVar()
        self.name = tk.StringVar()
        self.dept = tk.StringVar(value=DEPARTMENTS[0])
        self.sem = tk.StringVar(value="3")
        self.max_marks = tk.StringVar(value="100")
        body = tk.Frame(self, bg=WHITE)
        body.pack(padx=20, pady=16)
        for label, var in (("Code", self.code), ("Name", self.name), ("Max marks", self.max_marks)):
            tk.Label(body, text=label, bg=WHITE, fg=NAVY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            ttk.Entry(body, textvariable=var).pack(fill="x", pady=(2, 8))
        ttk.Combobox(body, textvariable=self.dept, values=DEPARTMENTS, state="readonly").pack(fill="x", pady=4)
        ttk.Combobox(body, textvariable=self.sem, values=[str(s) for s in SEMESTERS], state="readonly").pack(
            fill="x", pady=4
        )
        HoverButton(body, ACCENT, ACCENT_HOVER, text="Save subject", command=self._save).pack(fill="x", pady=8)

    def _save(self) -> None:
        try:
            code = self.code.get().strip()
            name = self.name.get().strip()
            if not code or not name:
                raise ValidationError("Subject code and name are required.")
            maximum = float(self.max_marks.get())
            if maximum <= 0:
                raise ValidationError("Maximum marks must be greater than zero.")
            self.db.add_subject(code, name, self.dept.get(), int(self.sem.get()), maximum)
            info(self, "Subject added", f"{code.upper()} was saved.")
            self.on_saved()
            self.destroy()
        except ValidationError as exc:
            error(self, "Validation error", str(exc))
        except Exception as exc:
            error(self, "Save failed", str(exc))
