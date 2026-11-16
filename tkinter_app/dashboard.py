"""Admin dashboard with live database statistics and charts."""

from __future__ import annotations

import tkinter as tk

from database.db import Database
from tkinter_app.charting import bar_chart, embed_figure, new_figure, pie_chart
from tkinter_app.theme import ACCENT, CONTENT, DANGER, SUCCESS, WARNING
from tkinter_app.widgets import Card, DataTable, PageHeader, StatCard


class AdminDashboard(tk.Frame):
    def __init__(self, master, db: Database) -> None:
        super().__init__(master, bg=CONTENT)
        self.db = db
        PageHeader(
            self,
            "Operations overview",
            "Live figures calculated from SQLite — not placeholder values.",
        ).pack(fill="x", padx=24, pady=(20, 8))
        banner = tk.Frame(self, bg="#DBEAFE", highlightbackground="#93C5FD", highlightthickness=1)
        banner.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(
            banner,
            text="Seeded names are synthetic demonstration records. Cards, charts and tables below query the live database.",
            bg="#DBEAFE",
            fg="#1E3A5F",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12, pady=8)

        self.cards_row = tk.Frame(self, bg=CONTENT)
        self.cards_row.pack(fill="x", padx=24, pady=8)
        self.cards_row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.card_total = StatCard(self.cards_row, "Students", "0", "Registered records", ACCENT)
        self.card_att = StatCard(self.cards_row, "Attendance", "0%", "Institution average", SUCCESS)
        self.card_marks = StatCard(self.cards_row, "Internal marks", "0", "Mean examination score", ACCENT)
        self.card_well = StatCard(self.cards_row, "Performing well", "0", "High marks and attendance", SUCCESS)
        self.card_risk = StatCard(self.cards_row, "Need attention", "0", "Low attendance or internals", DANGER)
        for i, card in enumerate((self.card_total, self.card_att, self.card_marks, self.card_well, self.card_risk)):
            card.grid(row=0, column=i, sticky="nsew", padx=6)

        charts = tk.Frame(self, bg=CONTENT)
        charts.pack(fill="both", expand=True, padx=24, pady=8)
        charts.grid_columnconfigure(0, weight=1)
        charts.grid_columnconfigure(1, weight=1)
        charts.grid_rowconfigure(0, weight=1)

        self.perf_card = Card(charts, "Performance distribution")
        self.perf_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.perf_fig = new_figure(5.4, 3.1)
        self.perf_canvas = embed_figure(self.perf_card.body, self.perf_fig)

        self.att_card = Card(charts, "Attendance analytics")
        self.att_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.att_fig = new_figure(5.4, 3.1)
        self.att_canvas = embed_figure(self.att_card.body, self.att_fig)

        table_card = Card(self, "Latest student records")
        table_card.pack(fill="both", expand=True, padx=24, pady=(4, 20))
        self.table = DataTable(
            table_card.body,
            [
                ("id", "Student ID", 110),
                ("name", "Name", 170),
                ("dept", "Department", 90),
                ("sem", "Sem", 50),
                ("att", "Attendance %", 110),
                ("marks", "Internals", 90),
                ("assign", "Assignments", 110),
            ],
            height=7,
        )
        self.table.pack(fill="both", expand=True)

    def refresh(self) -> None:
        stats = self.db.dashboard_stats()
        self.card_total.update_values(str(stats["total_students"]), "Registered records")
        self.card_att.update_values(f"{stats['avg_attendance']:.1f}%", "Institution average")
        self.card_marks.update_values(f"{stats['avg_marks']:.1f}", "Mean examination score")
        self.card_well.update_values(str(stats["performing_well"]), "High marks and attendance")
        self.card_risk.update_values(str(stats["requiring_attention"]), "Low attendance or internals")

        dist = self.db.performance_distribution()
        pie_chart(self.perf_fig, list(dist.keys()), list(dist.values()), "Internal marks bands")
        self.perf_canvas.draw()

        att = self.db.attendance_distribution()
        bar_chart(self.att_fig, list(att.keys()), list(att.values()), "Attendance bands", color=WARNING)
        self.att_canvas.draw()

        rows = [
            (
                s["student_id"],
                s["full_name"],
                s["department"],
                s["semester"],
                f"{s['attendance_percentage']:.1f}",
                f"{s['internal_examination_marks']:.1f}",
                f"{s['assignment_score']:.1f}",
            )
            for s in stats["latest"]
        ]
        self.table.fill(rows)
