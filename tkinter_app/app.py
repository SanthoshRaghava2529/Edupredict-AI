"""Main application shell with sidebar navigation and role-based pages."""

from __future__ import annotations

import tkinter as tk

from config import APP_NAME, APP_SHORT_NAME
from database.db import Database
from tkinter_app.analytics import AnalyticsPage
from tkinter_app.attendance import AttendancePage
from tkinter_app.dashboard import AdminDashboard
from tkinter_app.marks import MarksPage
from tkinter_app.prediction import AtRiskPage, PredictionPage
from tkinter_app.reports import ReportsPage
from tkinter_app.session import Session
from tkinter_app.student_portal import StudentPortal
from tkinter_app.students import StudentsPage
from tkinter_app.account import PasswordChangeDialog
from tkinter_app.theme import ACCENT, CONTENT, NAVY, SIDEBAR, WHITE, apply_theme
from tkinter_app.widgets import HoverButton, confirm, set_app_icon


class MainApp(tk.Tk):
    def __init__(self, db: Database, session: Session) -> None:
        super().__init__()
        self.db = db
        self.session = session
        self.logout_requested = False
        self.title(APP_NAME)
        self.geometry("1360x820")
        self.minsize(1180, 720)
        self.configure(bg=CONTENT)
        apply_theme(self)
        set_app_icon(self)
        self._nav_buttons: dict[str, tk.Button] = {}
        self._pages: dict[str, tk.Frame] = {}
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.show("dashboard" if session.is_admin else "my_dashboard")

    def _build(self) -> None:
        sidebar = tk.Frame(self, bg=SIDEBAR, width=232)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text=APP_SHORT_NAME, bg=SIDEBAR, fg=WHITE, font=("Segoe UI", 16, "bold")).pack(
            anchor="w", padx=22, pady=(22, 2)
        )
        tk.Label(sidebar, text="Student Performance Suite", bg=SIDEBAR, fg="#93C5FD", font=("Segoe UI", 9)).pack(
            anchor="w", padx=22, pady=(0, 18)
        )
        tk.Label(
            sidebar,
            text=f"{self.session.username}\n{self.session.role.title()} access",
            bg=SIDEBAR,
            fg="#CBD5E1",
            font=("Segoe UI", 9),
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 16))

        if self.session.is_admin:
            items = [
                ("dashboard", "  Dashboard"),
                ("students", "  Students"),
                ("attendance", "  Attendance"),
                ("marks", "  Marks & assignments"),
                ("prediction", "  ML predictions"),
                ("atrisk", "  At-risk students"),
                ("analytics", "  Analytics"),
                ("reports", "  Reports"),
            ]
        else:
            items = [
                ("my_dashboard", "  My dashboard"),
            ]

        nav = tk.Frame(sidebar, bg=SIDEBAR)
        nav.pack(fill="x", pady=4)
        for key, label in items:
            button = tk.Button(
                nav,
                text=label,
                anchor="w",
                bd=0,
                relief="flat",
                cursor="hand2",
                font=("Segoe UI", 10),
                fg=WHITE,
                bg=SIDEBAR,
                activebackground=NAVY,
                activeforeground=WHITE,
                padx=18,
                pady=10,
                command=lambda k=key: self.show(k),
            )
            button.pack(fill="x")
            self._nav_buttons[key] = button

        HoverButton(sidebar, "#1E3A5F", ACCENT, text="Sign out", command=self._logout).pack(
            side="bottom", fill="x", padx=18, pady=18
        )
        HoverButton(sidebar, "#1E3A5F", ACCENT, text="Change password", command=self._change_password).pack(
            side="bottom", fill="x", padx=18, pady=(0, 8)
        )

        self.content = tk.Frame(self, bg=CONTENT)
        self.content.pack(side="left", fill="both", expand=True)

        if self.session.is_admin:
            self._pages["dashboard"] = AdminDashboard(self.content, self.db)
            self._pages["students"] = StudentsPage(self.content, self.db)
            self._pages["attendance"] = AttendancePage(self.content, self.db)
            self._pages["marks"] = MarksPage(self.content, self.db)
            self._pages["prediction"] = PredictionPage(self.content, self.db)
            self._pages["atrisk"] = AtRiskPage(self.content, self.db)
            self._pages["analytics"] = AnalyticsPage(self.content, self.db)
            self._pages["reports"] = ReportsPage(self.content, self.db)
        else:
            self._pages["my_dashboard"] = StudentPortal(self.content, self.db, self.session)
            self._pages["dashboard"] = self._pages["my_dashboard"]

        for page in self._pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

    def show(self, key: str) -> None:
        if key not in self._pages:
            return
        for name, button in self._nav_buttons.items():
            if name == key:
                button.configure(bg=ACCENT, fg=WHITE, font=("Segoe UI", 10, "bold"))
            else:
                button.configure(bg=SIDEBAR, fg=WHITE, font=("Segoe UI", 10))
        page = self._pages[key]
        page.lift()
        if hasattr(page, "refresh"):
            page.refresh()

    def _change_password(self) -> None:
        PasswordChangeDialog(
            self,
            self.db,
            self.session.username,
            title="Change password",
            message="Update the password for the signed-in account.",
        )

    def _logout(self) -> None:
        if confirm(self, "Logout", "Return to the sign-in screen?"):
            self.logout_requested = True
            self.destroy()

    def _close(self) -> None:
        self.logout_requested = False
        self.destroy()
