"""Embedded analytics charts from live SQLite data."""

from __future__ import annotations

import tkinter as tk

from database.db import Database
from tkinter_app.charting import bar_chart, embed_figure, horizontal_bar, new_figure, pie_chart
from tkinter_app.theme import ACCENT, CONTENT
from tkinter_app.widgets import Card, DataTable, PageHeader


class AnalyticsPage(tk.Frame):
    def __init__(self, master, db: Database) -> None:
        super().__init__(master, bg=CONTENT)
        self.db = db
        PageHeader(self, "Analytics", "All charts are generated from the current database, not static images.").pack(
            fill="x", padx=24, pady=(20, 8)
        )

        grid = tk.Frame(self, bg=CONTENT)
        grid.pack(fill="both", expand=True, padx=24, pady=8)
        for i in range(2):
            grid.grid_columnconfigure(i, weight=1)
            grid.grid_rowconfigure(i, weight=1)

        self.cards = []
        self.figures = []
        self.canvases = []
        titles = [
            "Student performance distribution",
            "Attendance distribution",
            "Subject-wise average marks",
            "ML category mix (latest predictions)",
        ]
        for index, title in enumerate(titles):
            card = Card(grid, title)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)
            fig = new_figure(5.2, 2.8)
            canvas = embed_figure(card.body, fig)
            self.cards.append(card)
            self.figures.append(fig)
            self.canvases.append(canvas)

        tables = tk.Frame(self, bg=CONTENT)
        tables.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        tables.grid_columnconfigure(0, weight=1)
        tables.grid_columnconfigure(1, weight=1)
        tables.grid_columnconfigure(2, weight=1)

        top_card = Card(tables, "Top-performing students")
        top_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.top_table = DataTable(
            top_card.body,
            [("id", "ID", 90), ("name", "Name", 150), ("marks", "Internals", 80), ("att", "Attendance", 90)],
            height=6,
        )
        self.top_table.pack(fill="both", expand=True)

        dept_card = Card(tables, "Department comparison")
        dept_card.grid(row=0, column=1, sticky="nsew")
        self.dept_table = DataTable(
            dept_card.body,
            [("dept", "Department", 90), ("marks", "Avg internals", 100), ("att", "Avg attendance", 110), ("n", "Students", 80)],
            height=6,
        )
        self.dept_table.pack(fill="both", expand=True)

        risk_card = Card(tables, "At-risk snapshot")
        risk_card.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        self.risk_table = DataTable(
            risk_card.body,
            [("id", "ID", 90), ("name", "Name", 150), ("marks", "Internals", 80), ("att", "Attendance", 90)],
            height=6,
        )
        self.risk_table.pack(fill="both", expand=True)

    def refresh(self) -> None:
        perf = self.db.performance_distribution()
        pie_chart(self.figures[0], list(perf.keys()), list(perf.values()), "Internal marks")
        self.canvases[0].draw()

        att = self.db.attendance_distribution()
        bar_chart(self.figures[1], list(att.keys()), list(att.values()), "Attendance bands", color=ACCENT)
        self.canvases[1].draw()

        subjects = self.db.subject_average_marks()
        labels = [r["code"] for r in subjects] or ["None"]
        values = [float(r["avg_percentage"] or 0) for r in subjects] or [0]
        horizontal_bar(self.figures[2], labels, values, "Subject averages")
        self.canvases[2].draw()

        mix = self.db.prediction_category_counts()
        pie_chart(self.figures[3], list(mix.keys()), list(mix.values()), "Latest ML categories")
        self.canvases[3].draw()

        self.top_table.fill(
            [
                (s["student_id"], s["full_name"], f"{s['internal_examination_marks']:.1f}", f"{s['attendance_percentage']:.1f}")
                for s in self.db.top_students(8)
            ]
        )
        self.dept_table.fill(
            [
                (
                    r["department"],
                    f"{float(r['avg_marks']):.1f}",
                    f"{float(r['avg_attendance']):.1f}",
                    r["student_count"],
                )
                for r in self.db.department_averages()
            ]
        )
        self.risk_table.fill(
            [
                (s["student_id"], s["full_name"], f"{s['internal_examination_marks']:.1f}", f"{s['attendance_percentage']:.1f}")
                for s in self.db.low_attendance_students()[:8]
            ]
        )
