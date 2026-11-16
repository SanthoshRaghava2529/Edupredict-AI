"""PDF report generation with ReportLab."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
import tkinter as tk
from tkinter import ttk

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import APP_NAME, DEPARTMENTS, REPORTS_DIR, SEMESTERS
from database.db import Database
from tkinter_app.theme import ACCENT, ACCENT_HOVER, CONTENT, NAVY
from tkinter_app.widgets import Card, HoverButton, PageHeader, error, info

NAVY_HEX = colors.HexColor("#0B1D36")
ACCENT_HEX = colors.HexColor("#3B82F6")
ROW_HEX = colors.HexColor("#F8FAFC")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="AppTitle", fontName="Helvetica-Bold", fontSize=16, textColor=NAVY_HEX, spaceAfter=6))
    styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=12, textColor=NAVY_HEX, spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="BodyText2", fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#334155")))
    styles.add(ParagraphStyle(name="Small", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#64748B")))
    return styles


def _cell(text, styles) -> Paragraph:
    return Paragraph(escape(str(text)), styles["Small"])


def _table(data, col_widths=None):
    table = Table(data, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_HEX),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), ROW_HEX),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def generate_student_report(db: Database, student_id: str, output_path: Path | None = None) -> Path:
    student = db.get_student(student_id)
    if not student:
        raise ValueError(f"Student {student_id} was not found.")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = REPORTS_DIR / f"{student_id}_{stamp}.pdf"

    styles = _styles()
    story = [
        Paragraph(APP_NAME, styles["AppTitle"]),
        Paragraph("Individual Academic Performance Report", styles["Section"]),
        Paragraph(f"Generated on {datetime.now().strftime('%d %B %Y, %H:%M')}", styles["Small"]),
        Spacer(1, 8),
        Paragraph("Student details", styles["Section"]),
        _table(
            [
                ["Field", "Value"],
                ["Student ID", student["student_id"]],
                ["Name", student["full_name"]],
                ["Email", student["email"]],
                ["Department / Semester / Section", f"{student['department']} / {student['semester']} / {student['section']}"],
                ["Phone", student["phone"]],
            ],
            [180, 320],
        ),
        Paragraph("Attendance summary", styles["Section"]),
        Paragraph(
            f"Overall attendance: <b>{student['attendance_percentage']:.1f}%</b>. "
            f"Institution alert threshold: {db.get_attendance_threshold():.0f}%.",
            styles["BodyText2"],
        ),
    ]
    history = db.attendance_history(student_id)[:12]
    if history:
        rows = [["Date", "Subject", "Status"]]
        rows.extend(
            [[h["attendance_date"], _cell(h["subject_code"], styles), h["status"]] for h in history]
        )
        story.append(_table(rows, [120, 180, 100]))

    story.append(Paragraph("Examination performance", styles["Section"]))
    marks = db.student_marks(student_id)
    if marks:
        rows = [["Subject", "Marks", "Maximum", "Percentage"]]
        for m in marks:
            pct = 100.0 * m["marks"] / m["max_marks"]
            rows.append(
                [
                    _cell(f"{m['subject_code']} {m['subject_name']}", styles),
                    f"{m['marks']:.1f}",
                    f"{m['max_marks']:.0f}",
                    f"{pct:.1f}%",
                ]
            )
        story.append(_table(rows, [220, 80, 80, 90]))
    else:
        story.append(Paragraph(f"Recorded internal average: {student['internal_examination_marks']:.1f}/100", styles["BodyText2"]))

    story.append(Paragraph("Assignment performance", styles["Section"]))
    assignments = db.student_assignments(student_id)
    if assignments:
        rows = [["Title", "Subject", "Score", "Maximum"]]
        for a in assignments:
            rows.append(
                [_cell(a["title"], styles), a["subject_code"], f"{a['score']:.1f}", f"{a['max_score']:.0f}"]
            )
        story.append(_table(rows, [180, 100, 80, 80]))
    else:
        story.append(Paragraph(f"Assignment average: {student['assignment_score']:.1f}/100", styles["BodyText2"]))

    story.append(Paragraph("Previous academic performance", styles["Section"]))
    story.append(Paragraph(f"{student['previous_semester_performance']:.1f} / 100", styles["BodyText2"]))

    prediction = db.latest_prediction(student_id)
    story.append(Paragraph("Machine learning prediction", styles["Section"]))
    if prediction:
        story.append(
            Paragraph(
                f"Predicted category: <b>{prediction['predicted_category']}</b><br/>"
                f"Reason: {prediction.get('reason') or 'n/a'}<br/>"
                f"Recommendations: {prediction['recommendations']}",
                styles["BodyText2"],
            )
        )
    else:
        story.append(
            Paragraph(
                "No stored prediction yet. An administrator can generate one from the Prediction workspace.",
                styles["BodyText2"],
            )
        )

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "This report is produced by a college project application. Demonstration records are synthetic and "
            "must not be treated as official institutional transcripts.",
            styles["Small"],
        )
    )

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"{student_id} academic report",
        author=APP_NAME,
    )
    document.build(story)
    return output_path


def generate_class_report(db: Database, department: str = "", semester: str | int = "", output_path: Path | None = None) -> Path:
    students = db.list_students(department=department, semester=semester)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = f"{department or 'ALL'}_SEM{semester or 'ALL'}"
    if output_path is None:
        output_path = REPORTS_DIR / f"class_report_{label}_{stamp}.pdf"

    styles = _styles()
    stats = db.class_stats(department=department, semester=semester)
    institution = db.dashboard_stats()
    story = [
        Paragraph(APP_NAME, styles["AppTitle"]),
        Paragraph("Class-level academic report", styles["Section"]),
        Paragraph(
            f"Filter: department={department or 'All'}, semester={semester or 'All'} · "
            f"Generated {datetime.now().strftime('%d %B %Y, %H:%M')}",
            styles["Small"],
        ),
        Paragraph("Summary", styles["Section"]),
        _table(
            [
                ["Metric", "Value"],
                ["Students in this filter", str(stats["student_count"])],
                ["Average attendance (filter)", f"{stats['avg_attendance']:.1f}%"],
                ["Average internals (filter)", f"{stats['avg_marks']:.1f}"],
                ["Average assignments (filter)", f"{stats['avg_assignment']:.1f}"],
                ["Institution registered total", str(institution["total_students"])],
            ],
            [260, 220],
        ),
        Paragraph("Student roster", styles["Section"]),
    ]
    if not students:
        story.append(Paragraph("No students match this department and semester filter.", styles["BodyText2"]))
    else:
        rows = [["ID", "Name", "Dept", "Att %", "Internals", "Assign", "Latest ML"]]
        for student in students:
            pred = db.latest_prediction(student["student_id"])
            rows.append(
                [
                    student["student_id"],
                    _cell(student["full_name"], styles),
                    student["department"],
                    f"{student['attendance_percentage']:.1f}",
                    f"{student['internal_examination_marks']:.1f}",
                    f"{student['assignment_score']:.1f}",
                    pred["predicted_category"] if pred else "—",
                ]
            )
        story.append(_table(rows, [80, 120, 50, 50, 60, 55, 70]))
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "ML categories come from a Random Forest trained on synthetic demonstration data. "
            "Do not present these scores as official board or university results.",
            styles["Small"],
        )
    )
    document = SimpleDocTemplate(str(output_path), pagesize=A4, title="Class report", author=APP_NAME)
    document.build(story)
    return output_path


class ReportsPage(tk.Frame):
    def __init__(self, master, db: Database) -> None:
        super().__init__(master, bg=CONTENT)
        self.db = db
        self._map: dict = {}
        PageHeader(self, "PDF reports", "Generate individual counselling reports or a class roster PDF.").pack(
            fill="x", padx=24, pady=(20, 8)
        )
        card = Card(self, "Report builder")
        card.pack(fill="x", padx=24, pady=8)
        form = card.body
        self.student_var = tk.StringVar()
        self.dept_var = tk.StringVar(value="All")
        self.sem_var = tk.StringVar(value="All")
        tk.Label(form, text="Individual student", bg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.student_combo = ttk.Combobox(form, textvariable=self.student_var, state="readonly", width=40)
        self.student_combo.pack(anchor="w", pady=6)
        HoverButton(form, ACCENT, ACCENT_HOVER, text="Generate individual PDF", command=self._individual).pack(anchor="w", pady=4)

        tk.Label(form, text="Class filter (department and semester)", bg="white", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(12, 0)
        )
        row = tk.Frame(form, bg="white")
        row.pack(anchor="w", pady=(8, 6))
        ttk.Combobox(row, textvariable=self.dept_var, values=["All", *DEPARTMENTS], state="readonly", width=12).pack(side="left")
        ttk.Combobox(row, textvariable=self.sem_var, values=["All", *[str(s) for s in SEMESTERS]], state="readonly", width=8).pack(
            side="left", padx=8
        )
        HoverButton(row, NAVY, ACCENT, text="Generate class PDF", command=self._class).pack(side="left", padx=8)
        self.note = tk.Label(form, text=f"Files are stored in {REPORTS_DIR}", bg="white", fg="#64748B")
        self.note.pack(anchor="w", pady=10)

    def refresh(self) -> None:
        students = self.db.list_students()
        self._map = {f"{s['student_id']} — {s['full_name']}": s for s in students}
        self.student_combo["values"] = list(self._map)

    def _individual(self) -> None:
        student = self._map.get(self.student_var.get())
        if not student:
            error(self, "Select a student", "Choose a student for the individual report.")
            return
        try:
            path = generate_student_report(self.db, student["student_id"])
            info(self, "Report created", str(path))
        except Exception as exc:
            error(self, "Report failed", str(exc))

    def _class(self) -> None:
        dept = "" if self.dept_var.get() == "All" else self.dept_var.get()
        sem = "" if self.sem_var.get() == "All" else self.sem_var.get()
        try:
            path = generate_class_report(self.db, dept, sem)
            info(self, "Report created", str(path))
        except Exception as exc:
            error(self, "Report failed", str(exc))
