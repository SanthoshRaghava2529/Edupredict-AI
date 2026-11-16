"""Attendance entry, history, alerts and visualization."""

from __future__ import annotations

import csv
from datetime import date
import tkinter as tk
from tkinter import filedialog, ttk

from config import DEPARTMENTS, REPORTS_DIR, SEMESTERS
from database.db import Database
from tkinter_app.charting import bar_chart, embed_figure, new_figure
from tkinter_app.theme import ACCENT, ACCENT_HOVER, CONTENT, DANGER, NAVY, WARNING
from tkinter_app.widgets import Card, DataTable, HoverButton, PageHeader, error, info


class AttendancePage(tk.Frame):
    def __init__(self, master, db: Database) -> None:
        super().__init__(master, bg=CONTENT)
        self.db = db
        self._student_map: dict = {}
        self._subject_map: dict = {}
        PageHeader(
            self,
            "Attendance management",
            "Mark daily attendance, review history and raise alerts below the configured threshold.",
        ).pack(fill="x", padx=24, pady=(20, 8))

        top = tk.Frame(self, bg=CONTENT)
        top.pack(fill="x", padx=24, pady=6)

        entry_card = Card(top, "Attendance entry")
        entry_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        form = entry_card.body
        self.student_var = tk.StringVar()
        self.subject_var = tk.StringVar()
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.status_var = tk.StringVar(value="Present")
        self.dept_var = tk.StringVar(value="All")
        self.sem_var = tk.StringVar(value="All")

        tk.Label(form, text="Department", bg="white", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", padx=4)
        tk.Label(form, text="Semester", bg="white", font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Combobox(form, textvariable=self.dept_var, values=["All", *DEPARTMENTS], state="readonly", width=12).grid(
            row=1, column=0, padx=4, pady=4
        )
        ttk.Combobox(
            form, textvariable=self.sem_var, values=["All", *[str(s) for s in SEMESTERS]], state="readonly", width=8
        ).grid(row=1, column=1, padx=4, pady=4)
        HoverButton(form, NAVY, ACCENT, text="Load students", command=self._load_students).grid(row=1, column=2, padx=4)

        tk.Label(form, text="Student", bg="white", font=("Segoe UI", 8, "bold")).grid(row=2, column=0, sticky="w", padx=4)
        tk.Label(form, text="Subject", bg="white", font=("Segoe UI", 8, "bold")).grid(row=2, column=2, sticky="w", padx=4)
        self.student_combo = ttk.Combobox(form, textvariable=self.student_var, state="readonly", width=28)
        self.student_combo.grid(row=3, column=0, columnspan=2, padx=4, pady=4, sticky="ew")
        self.subject_combo = ttk.Combobox(form, textvariable=self.subject_var, state="readonly", width=28)
        self.subject_combo.grid(row=3, column=2, padx=4, pady=4, sticky="ew")
        tk.Label(form, text="Date (YYYY-MM-DD)", bg="white", font=("Segoe UI", 8, "bold")).grid(row=4, column=0, sticky="w", padx=4)
        tk.Label(form, text="Status", bg="white", font=("Segoe UI", 8, "bold")).grid(row=4, column=1, sticky="w", padx=4)
        ttk.Entry(form, textvariable=self.date_var, width=14).grid(row=5, column=0, padx=4, pady=4)
        ttk.Combobox(form, textvariable=self.status_var, values=["Present", "Absent"], state="readonly", width=12).grid(
            row=5, column=1, padx=4, pady=4
        )
        HoverButton(form, ACCENT, ACCENT_HOVER, text="Save attendance", command=self._save).grid(row=5, column=2, padx=4)
        HoverButton(form, NAVY, ACCENT, text="Show history", command=self._history_for_selected).grid(
            row=6, column=0, padx=4, pady=4, sticky="w"
        )

        thresh_card = Card(top, "Low attendance threshold")
        thresh_card.pack(side="left", fill="y")
        self.threshold_var = tk.StringVar(value=str(self.db.get_attendance_threshold()))
        ttk.Entry(thresh_card.body, textvariable=self.threshold_var, width=8).pack(side="left")
        tk.Label(thresh_card.body, text="%", bg="white").pack(side="left", padx=4)
        HoverButton(thresh_card.body, NAVY, ACCENT, text="Update", command=self._save_threshold).pack(side="left", padx=8)

        mid = tk.Frame(self, bg=CONTENT)
        mid.pack(fill="both", expand=True, padx=24, pady=8)
        mid.grid_columnconfigure(0, weight=2)
        mid.grid_columnconfigure(1, weight=1)
        mid.grid_rowconfigure(0, weight=1)

        alert_card = Card(mid, "Students below threshold")
        alert_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        btns = tk.Frame(alert_card.body, bg="white")
        btns.pack(fill="x", pady=(0, 8))
        HoverButton(btns, NAVY, ACCENT, text="Export CSV", command=self._export_alerts).pack(side="left")
        self.alert_table = DataTable(
            alert_card.body,
            [
                ("id", "Student ID", 110),
                ("name", "Name", 160),
                ("dept", "Dept", 70),
                ("att", "Attendance %", 110),
                ("marks", "Internals", 90),
            ],
            height=10,
        )
        self.alert_table.pack(fill="both", expand=True)
        self.alert_table.bind("<<TreeviewSelect>>", lambda _e: self._show_history())

        hist_card = Card(mid, "Attendance history")
        hist_card.grid(row=0, column=1, sticky="nsew")
        self.history_table = DataTable(
            hist_card.body,
            [
                ("date", "Date", 100),
                ("subject", "Subject", 140),
                ("status", "Status", 80),
            ],
            height=10,
        )
        self.history_table.pack(fill="both", expand=True)

        chart_card = Card(self, "Attendance visualization")
        chart_card.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.fig = new_figure(9.5, 2.6)
        self.canvas = embed_figure(chart_card.body, self.fig)

    def refresh(self) -> None:
        self._load_students()
        self._refresh_alerts()

    def _load_students(self) -> None:
        dept = "" if self.dept_var.get() == "All" else self.dept_var.get()
        sem = "" if self.sem_var.get() == "All" else self.sem_var.get()
        students = self.db.list_students(department=dept, semester=sem)
        self._student_map = {f"{s['student_id']} — {s['full_name']}": s for s in students}
        self.student_combo["values"] = list(self._student_map)
        subjects = self.db.list_subjects(department=dept, semester=sem or "")
        if not subjects:
            subjects = self.db.list_subjects()
        self._subject_map = {f"{s['code']} — {s['name']}": s for s in subjects}
        self.subject_combo["values"] = list(self._subject_map)

    def _save_threshold(self) -> None:
        try:
            value = float(self.threshold_var.get())
            self.db.set_attendance_threshold(value)
            self._refresh_alerts()
            info(self, "Threshold updated", f"Alerts now use {value:.1f}%.")
        except Exception as exc:
            error(self, "Invalid threshold", str(exc))

    def _save(self) -> None:
        student = self._student_map.get(self.student_var.get())
        subject = self._subject_map.get(self.subject_var.get())
        if not student or not subject:
            error(self, "Incomplete", "Select a student and a subject.")
            return
        try:
            date.fromisoformat(self.date_var.get().strip())
        except ValueError:
            error(self, "Invalid date", "Use YYYY-MM-DD.")
            return
        try:
            self.db.record_attendance(
                student["student_id"], subject["id"], self.date_var.get().strip(), self.status_var.get()
            )
            info(self, "Saved", "Attendance was recorded and the percentage was recalculated.")
            self.refresh()
        except Exception as exc:
            error(self, "Save failed", str(exc))

    def _refresh_alerts(self) -> None:
        rows = self.db.low_attendance_students()
        self.alert_table.fill(
            [
                (
                    r["student_id"],
                    r["full_name"],
                    r["department"],
                    f"{r['attendance_percentage']:.1f}",
                    f"{r['internal_examination_marks']:.1f}",
                )
                for r in rows
            ]
        )
        dist = self.db.attendance_distribution()
        bar_chart(self.fig, list(dist.keys()), list(dist.values()), "Attendance distribution", color=WARNING)
        self.canvas.draw()

    def _history_for_selected(self) -> None:
        student = self._student_map.get(self.student_var.get())
        if not student:
            error(self, "No student", "Select a student first.")
            return
        self._fill_history(student["student_id"])

    def _show_history(self) -> None:
        values = self.alert_table.selected_values()
        if not values:
            return
        self._fill_history(values[0])

    def _fill_history(self, student_id: str) -> None:
        history = self.db.attendance_history(student_id)
        self.history_table.fill([(h["attendance_date"], h["subject_code"], h["status"]) for h in history])

    def _export_alerts(self) -> None:
        rows = self.db.low_attendance_students()
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir=REPORTS_DIR,
            filetypes=[("CSV", "*.csv")],
            initialfile="low_attendance.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["student_id", "full_name", "department", "attendance_percentage", "internal_marks"])
            for row in rows:
                writer.writerow(
                    [
                        row["student_id"],
                        row["full_name"],
                        row["department"],
                        row["attendance_percentage"],
                        row["internal_examination_marks"],
                    ]
                )
        info(self, "Exported", f"Saved {len(rows)} records to {path}")
