"""Student CRUD, search and filters."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from config import DEPARTMENTS, SECTIONS, SEMESTERS
from database.db import Database
from tkinter_app.theme import ACCENT, ACCENT_HOVER, CONTENT, DANGER, NAVY, WHITE
from tkinter_app.validators import ValidationError, student_payload
from tkinter_app.widgets import Card, DataTable, HoverButton, PageHeader, ScrollableFrame, confirm, error, info


class StudentsPage(tk.Frame):
    def __init__(self, master, db: Database) -> None:
        super().__init__(master, bg=CONTENT)
        self.db = db
        PageHeader(self, "Student management", "Create, update, search and remove academic records.").pack(
            fill="x", padx=24, pady=(20, 8)
        )

        toolbar = Card(self)
        toolbar.pack(fill="x", padx=24, pady=6)
        filters = toolbar.body
        self.search_var = tk.StringVar()
        self.dept_var = tk.StringVar(value="All")
        self.sem_var = tk.StringVar(value="All")

        search_entry = ttk.Entry(filters, textvariable=self.search_var, width=28)
        search_entry.pack(side="left", padx=(0, 8))
        search_entry.bind("<Return>", lambda _e: self.refresh())
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh())
        dept_combo = ttk.Combobox(filters, textvariable=self.dept_var, values=["All", *DEPARTMENTS], width=12, state="readonly")
        dept_combo.pack(side="left", padx=4)
        dept_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        sem_combo = ttk.Combobox(
            filters, textvariable=self.sem_var, values=["All", *[str(s) for s in SEMESTERS]], width=8, state="readonly"
        )
        sem_combo.pack(side="left", padx=4)
        sem_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        tk.Label(filters, text="Search name or ID", bg="white", fg="#64748B", font=("Segoe UI", 8)).pack(
            side="left", padx=(0, 4)
        )
        HoverButton(filters, ACCENT, ACCENT_HOVER, text="Search", command=self.refresh).pack(side="left", padx=8)
        HoverButton(filters, NAVY, ACCENT, text="Add student", command=self._open_form).pack(side="right", padx=4)
        HoverButton(filters, NAVY, ACCENT, text="Edit selected", command=self._edit_selected).pack(side="right", padx=4)
        HoverButton(filters, NAVY, ACCENT, text="View details", command=self._view_selected).pack(side="right", padx=4)
        HoverButton(filters, DANGER, "#B91C1C", text="Delete", command=self._delete_selected).pack(side="right", padx=4)

        table_card = Card(self, "Registered students")
        table_card.pack(fill="both", expand=True, padx=24, pady=(6, 20))
        self.table = DataTable(
            table_card.body,
            [
                ("id", "Student ID", 110),
                ("name", "Full name", 170),
                ("email", "Email", 190),
                ("dept", "Dept", 70),
                ("sem", "Sem", 50),
                ("sec", "Sec", 50),
                ("phone", "Phone", 110),
                ("att", "Attendance", 90),
                ("marks", "Internals", 80),
                ("asg", "Assignments", 90),
                ("prev", "Previous", 80),
                ("hrs", "Study hrs", 80),
            ],
            height=16,
        )
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", lambda _e: self._view_selected())

    def refresh(self) -> None:
        dept = "" if self.dept_var.get() == "All" else self.dept_var.get()
        sem = "" if self.sem_var.get() == "All" else self.sem_var.get()
        rows = self.db.list_students(search=self.search_var.get(), department=dept, semester=sem)
        self.table.fill(
            [
                (
                    r["student_id"],
                    r["full_name"],
                    r["email"],
                    r["department"],
                    r["semester"],
                    r["section"],
                    r["phone"],
                    f"{r['attendance_percentage']:.1f}",
                    f"{r['internal_examination_marks']:.1f}",
                    f"{r['assignment_score']:.1f}",
                    f"{r['previous_semester_performance']:.1f}",
                    f"{r['study_hours']:.1f}",
                )
                for r in rows
            ]
        )

    def _selected_id(self) -> str | None:
        values = self.table.selected_values()
        return values[0] if values else None

    def _open_form(self, student: dict | None = None) -> None:
        StudentForm(self, self.db, student, on_saved=self.refresh)

    def _view_selected(self) -> None:
        sid = self._selected_id()
        if not sid:
            error(self, "No selection", "Select a student to view.")
            return
        student = self.db.get_student(sid)
        if not student:
            error(self, "Missing record", "That student no longer exists.")
            return
        StudentDetailDialog(self, self.db, student)

    def _edit_selected(self) -> None:
        sid = self._selected_id()
        if not sid:
            error(self, "No selection", "Select a student to edit.")
            return
        student = self.db.get_student(sid)
        if not student:
            error(self, "Missing record", "That student no longer exists.")
            return
        self._open_form(student)

    def _delete_selected(self) -> None:
        sid = self._selected_id()
        if not sid:
            error(self, "No selection", "Select a student to delete.")
            return
        if not confirm(self, "Delete student", f"Permanently delete {sid} and related academic records?"):
            return
        try:
            self.db.delete_student(sid)
            self.refresh()
            info(self, "Deleted", f"{sid} was removed.")
        except Exception as exc:
            error(self, "Delete failed", str(exc))


class StudentDetailDialog(tk.Toplevel):
    def __init__(self, master, db: Database, student: dict) -> None:
        super().__init__(master)
        self.title(f"{student['student_id']} — details")
        self.configure(bg=WHITE)
        self.geometry("640x560")
        self.transient(master)
        self.grab_set()
        tk.Label(
            self,
            text=student["full_name"],
            bg=WHITE,
            fg=NAVY,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(
            self,
            text=(
                f"{student['student_id']}  ·  {student['department']} Sem {student['semester']} "
                f"Section {student['section']}\n{student['email']}  ·  {student['phone']}\n"
                f"Attendance {student['attendance_percentage']:.1f}%  ·  "
                f"Internals {student['internal_examination_marks']:.1f}  ·  "
                f"Assignments {student['assignment_score']:.1f}  ·  "
                f"Previous {student['previous_semester_performance']:.1f}  ·  "
                f"Study hours {student['study_hours']:.1f}"
            ),
            bg=WHITE,
            justify="left",
        ).pack(anchor="w", padx=20)

        marks = db.student_marks(student["student_id"])
        mark_table = DataTable(
            self,
            [("code", "Subject", 80), ("name", "Name", 180), ("marks", "Marks", 70), ("max", "Max", 60)],
            height=6,
        )
        mark_table.pack(fill="both", expand=True, padx=20, pady=8)
        mark_table.fill(
            [(m["subject_code"], m["subject_name"], f"{m['marks']:.1f}", f"{m['max_marks']:.0f}") for m in marks]
        )
        prediction = db.latest_prediction(student["student_id"])
        pred_text = (
            f"Latest ML category: {prediction['predicted_category']}\n{prediction['recommendations']}"
            if prediction
            else "No stored ML prediction yet."
        )
        tk.Label(self, text=pred_text, bg=WHITE, justify="left", wraplength=580).pack(anchor="w", padx=20, pady=(0, 16))


class StudentForm(tk.Toplevel):
    def __init__(self, master, db: Database, student: dict | None, on_saved) -> None:
        super().__init__(master)
        self.db = db
        self.existing = student
        self.on_saved = on_saved
        self.title("Student record")
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        fields = [
            ("student_id", "Student ID"),
            ("full_name", "Full name"),
            ("email", "Email"),
            ("phone", "Phone"),
            ("attendance_percentage", "Attendance %"),
            ("internal_examination_marks", "Internal marks"),
            ("assignment_score", "Assignment score"),
            ("previous_semester_performance", "Previous semester"),
            ("study_hours", "Study hours / day"),
        ]
        self.vars: dict[str, tk.StringVar] = {}
        scroller = ScrollableFrame(self, bg=WHITE, height=640)
        scroller.pack(fill="both", expand=True)
        body = tk.Frame(scroller.body, bg=WHITE)
        body.pack(fill="both", expand=True, padx=24, pady=16)
        for key, label in fields:
            var = tk.StringVar(value="" if not student else str(student.get(key, "")))
            self.vars[key] = var
            tk.Label(body, text=label, bg=WHITE, fg=NAVY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            state = "readonly" if student and key == "student_id" else "normal"
            ttk.Entry(body, textvariable=var, state=state).pack(fill="x", pady=(2, 8))

        self.dept = tk.StringVar(value=student["department"] if student else DEPARTMENTS[0])
        self.sem = tk.StringVar(value=str(student["semester"] if student else 3))
        self.sec = tk.StringVar(value=student["section"] if student else "A")
        row = tk.Frame(body, bg=WHITE)
        row.pack(fill="x", pady=4)
        tk.Label(row, text="Dept / Sem / Section", bg=WHITE, fg=NAVY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        combo_row = tk.Frame(row, bg=WHITE)
        combo_row.pack(fill="x")
        ttk.Combobox(combo_row, textvariable=self.dept, values=DEPARTMENTS, state="readonly", width=12).pack(side="left")
        ttk.Combobox(combo_row, textvariable=self.sem, values=[str(s) for s in SEMESTERS], state="readonly", width=8).pack(
            side="left", padx=8
        )
        ttk.Combobox(combo_row, textvariable=self.sec, values=SECTIONS, state="readonly", width=8).pack(side="left")

        HoverButton(body, ACCENT, ACCENT_HOVER, text="Save record", command=self._save).pack(fill="x", pady=(10, 4))
        self.geometry("440x680")

    def _save(self) -> None:
        try:
            payload = student_payload(
                {
                    "student_id": self.vars["student_id"].get(),
                    "full_name": self.vars["full_name"].get(),
                    "email": self.vars["email"].get(),
                    "phone": self.vars["phone"].get(),
                    "department": self.dept.get(),
                    "semester": self.sem.get(),
                    "section": self.sec.get(),
                    "attendance_percentage": self.vars["attendance_percentage"].get() or 0,
                    "internal_examination_marks": self.vars["internal_examination_marks"].get() or 0,
                    "assignment_score": self.vars["assignment_score"].get() or 0,
                    "previous_semester_performance": self.vars["previous_semester_performance"].get() or 0,
                    "study_hours": self.vars["study_hours"].get() or 0,
                }
            )
            if self.existing is None:
                if self.db.student_exists(payload["student_id"]):
                    raise ValidationError("A student with this ID already exists.")
                if self.db.email_taken(payload["email"]):
                    raise ValidationError("This email is already registered.")
                self.db.add_student(payload)
                info(self, "Student added", f"{payload['student_id']} can sign in with password Student@123.")
            else:
                if self.db.email_taken(payload["email"], exclude_id=payload["student_id"]):
                    raise ValidationError("This email is already registered.")
                update = dict(payload)
                update.pop("student_id")
                self.db.update_student(payload["student_id"], update)
                info(self, "Updated", "The student record was saved.")
            self.on_saved()
            self.destroy()
        except ValidationError as exc:
            error(self, "Validation error", str(exc))
        except Exception as exc:
            error(self, "Save failed", str(exc))
