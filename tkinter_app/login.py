
"""Professional login window with admin and student roles."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from config import APP_NAME, APP_SHORT_NAME, APP_VERSION
from database.db import Database
from tkinter_app.account import PasswordChangeDialog
from tkinter_app.session import Session
from tkinter_app.theme import ACCENT, ACCENT_HOVER, MUTED, NAVY, WHITE
from tkinter_app.widgets import LOGO_PATH, HoverButton, error, set_app_icon
from tkinter_app.theme import apply_theme


class LoginApp(tk.Tk):

    def __init__(self, db: Database, on_success: Callable[[Session], None]) -> None:
        super().__init__()

        self.db = db
        self.on_success = on_success

        self.title(APP_NAME)
        self.geometry("1040x620")
        self.minsize(960, 580)
        self.configure(bg=NAVY)

        apply_theme(self)
        set_app_icon(self)

        self._build()
        self.bind("<Return>", lambda _e: self._login())

    def _build(self) -> None:

        left = tk.Frame(self, bg=NAVY)
        left.pack(side="left", fill="both", expand=True)

        if LOGO_PATH.exists():
            try:
                from PIL import Image, ImageTk

                logo = Image.open(LOGO_PATH).resize((72, 72))
                self._logo_image = ImageTk.PhotoImage(logo)

                tk.Label(
                    left,
                    image=self._logo_image,
                    bg=NAVY
                ).pack(anchor="w", padx=48, pady=(48, 8))

            except Exception:
                pass

        tk.Label(
            left,
            text=APP_SHORT_NAME,
            bg=NAVY,
            fg="#93C5FD",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=48, pady=(12, 8))

        tk.Label(
            left,
            text="Predict academic risk\nbefore it becomes a crisis.",
            bg=NAVY,
            fg=WHITE,
            font=("Segoe UI", 28, "bold"),
            justify="left"
        ).pack(anchor="w", padx=48)

        tk.Label(
            left,
            text=(
                "A college-ready desktop system for student records, attendance,\n"
                "examination analytics and Random Forest performance prediction."
            ),
            bg=NAVY,
            fg="#CBD5E1",
            font=("Segoe UI", 11),
            justify="left"
        ).pack(anchor="w", padx=48, pady=(18, 0))

        bullets = [
            "Role-based admin and student access",
            "SQLite academic records with live statistics",
            "Scikit-learn Random Forest classifier",
            "PDF reports for counselling and evaluation",
        ]

        for item in bullets:
            row = tk.Frame(left, bg=NAVY)
            row.pack(anchor="w", padx=48, pady=6)

            tk.Label(
                row,
                text="●",
                bg=NAVY,
                fg=ACCENT,
                font=("Segoe UI", 10)
            ).pack(side="left")

            tk.Label(
                row,
                text=item,
                bg=NAVY,
                fg="#E2E8F0",
                font=("Segoe UI", 10)
            ).pack(side="left", padx=8)

        tk.Label(
            left,
            text=f"Version {APP_VERSION}  ·  Demonstration data is clearly labeled",
            bg=NAVY,
            fg=MUTED,
            font=("Segoe UI", 8)
        ).pack(side="bottom", anchor="w", padx=48, pady=24)

        # RIGHT LOGIN PANEL

        right = tk.Frame(self, bg=WHITE, width=430)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(
            right,
            text="Sign in",
            bg=WHITE,
            fg=NAVY,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w", padx=40, pady=(70, 4))

        tk.Label(
            right,
            text="Use your assigned role to open the workspace.",
            bg=WHITE,
            fg=MUTED
        ).pack(anchor="w", padx=40, pady=(0, 18))

        self.role_var = tk.StringVar(value="admin")

        role_row = tk.Frame(right, bg=WHITE)
        role_row.pack(fill="x", padx=40, pady=(0, 12))

        self._role_buttons: dict[str, tk.Button] = {}

        for role, label in (
            ("admin", "Administrator"),
            ("student", "Student")
        ):

            button = tk.Button(
                role_row,
                text=label,
                bd=0,
                relief="flat",
                cursor="hand2",
                font=("Segoe UI", 9, "bold"),
                padx=14,
                pady=8,
                command=lambda r=role: self._select_role(r)
            )

            button.pack(side="left", padx=(0, 8))
            self._role_buttons[role] = button

        self.username_var = tk.StringVar(value="admin")
        self.password_var = tk.StringVar()

        self._entry(right, "Username", self.username_var)
        self._entry(right, "Password", self.password_var, show="*")

        self._select_role("admin")

        HoverButton(
            right,
            ACCENT,
            ACCENT_HOVER,
            text="Continue",
            command=self._login
        ).pack(fill="x", padx=40, pady=(18, 8))

        tk.Label(
            right,
            text=(
                "Default admin: admin / Admin@123  ·  "
                "Demo student: CSE23001 / Student@123\n"
                "The admin account must change the default password after first login."
            ),
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI", 8),
            justify="left"
        ).pack(anchor="w", padx=40, pady=(10, 0))

    def _select_role(self, role: str) -> None:

        self.role_var.set(role)

        for key, button in self._role_buttons.items():

            if key == role:
                button.configure(
                    bg=ACCENT,
                    fg=WHITE,
                    activebackground=ACCENT_HOVER,
                    activeforeground=WHITE
                )
            else:
                button.configure(
                    bg="#E2E8F0",
                    fg=NAVY,
                    activebackground="#CBD5E1",
                    activeforeground=NAVY
                )

        current = self.username_var.get().strip()

        if role == "student" and current in {"", "admin"}:
            self.username_var.set("CSE23001")

        elif role == "admin" and current in {"", "CSE23001"}:
            self.username_var.set("admin")

    # ENTRY FIELD WITH SHOW/HIDE PASSWORD

    def _entry(
        self,
        parent,
        label: str,
        var: tk.StringVar,
        show: str = ""
    ) -> None:

        wrap = tk.Frame(parent, bg=WHITE)
        wrap.pack(fill="x", padx=40, pady=6)

        tk.Label(
            wrap,
            text=label,
            bg=WHITE,
            fg=NAVY,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        field_row = tk.Frame(wrap, bg=WHITE)
        field_row.pack(fill="x", pady=(4, 0))

        entry = ttk.Entry(
            field_row,
            textvariable=var,
            show=show
        )

        entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=4
        )

        # Show/Hide button only for password field

        if show == "*":

            visible = tk.BooleanVar(value=False)

            def toggle_password():

                visible.set(not visible.get())

                if visible.get():

                    entry.configure(show="")
                    toggle_button.configure(text="Hide")

                else:

                    entry.configure(show="*")
                    toggle_button.configure(text="Show")

            toggle_button = tk.Button(
                field_row,
                text="Show",
                command=toggle_password,
                bg=WHITE,
                fg=ACCENT,
                activebackground=WHITE,
                activeforeground=ACCENT_HOVER,
                relief="flat",
                bd=0,
                cursor="hand2",
                font=("Segoe UI", 9, "bold")
            )

            toggle_button.pack(side="right", padx=(8, 0))

    # LOGIN FUNCTION

    def _login(self) -> None:

        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            error(
                self,
                "Missing details",
                "Enter both username and password."
            )
            return

        user = self.db.authenticate(username, password)

        if user is None:
            error(
                self,
                "Sign in failed",
                "Invalid username or password."
            )
            return

        selected_role = self.role_var.get()

        if user["role"] != selected_role:
            error(
                self,
                "Role mismatch",
                f"This account is registered as {user['role']}, not {selected_role}."
            )
            return

        session = Session.from_user_row(user)

        if session.must_change_password:

            dialog = PasswordChangeDialog(
                self,
                self.db,
                session.username,
                require_different_from_default=True,
                title="Change default password",
                message="You must change the default admin password before continuing."
            )

            self.wait_window(dialog)

            if not dialog.changed:
                return

            session.must_change_password = False

        self.on_success(session)


def run_login(db: Database) -> Optional[Session]:

    result: dict[str, Optional[Session]] = {"session": None}

    def capture(session: Session) -> None:
        result["session"] = session
        app.destroy()

    app = LoginApp(db, capture)
    app.mainloop()

    return result["session"]
