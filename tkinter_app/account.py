"""Password-change dialog used at first admin login and later from the workspace."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from config import DEFAULT_ADMIN_PASSWORD
from database.db import Database
from tkinter_app.theme import ACCENT, NAVY, WHITE
from tkinter_app.validators import ValidationError, validate_password
from tkinter_app.widgets import HoverButton, error, info


class PasswordChangeDialog(tk.Toplevel):
    def __init__(
        self,
        master,
        db: Database,
        username: str,
        *,
        require_different_from_default: bool = False,
        title: str = "Change password",
        message: str = "Choose a new password for this account.",
    ) -> None:
        super().__init__(master)
        self.db = db
        self.username = username
        self.require_different_from_default = require_different_from_default
        self.changed = False
        self.title(title)
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        tk.Label(
            self,
            text=message,
            bg=WHITE,
            fg=NAVY,
            font=("Segoe UI", 11, "bold"),
            wraplength=420,
            justify="left",
        ).pack(padx=24, pady=(20, 8), anchor="w")

        self.current_var = tk.StringVar()
        self.new_var = tk.StringVar()
        self.confirm_var = tk.StringVar()
        if not require_different_from_default:
            self._field("Current password", self.current_var, show="*")
        self._field("New password", self.new_var, show="*")
        self._field("Confirm password", self.confirm_var, show="*")
        HoverButton(self, NAVY, ACCENT, text="Update password", command=self._submit).pack(pady=(8, 20))
        self.geometry("480x340" if not require_different_from_default else "480x280")
        self.update_idletasks()
        self._center()

    def _field(self, label: str, var: tk.StringVar, show: str = "") -> None:
        wrap = tk.Frame(self, bg=WHITE)
        wrap.pack(fill="x", padx=24, pady=6)
        tk.Label(wrap, text=label, bg=WHITE, fg=NAVY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(wrap, textvariable=var, show=show).pack(fill="x", pady=(4, 0))

    def _center(self) -> None:
        self.update_idletasks()
        x = self.winfo_screenwidth() // 2 - self.winfo_width() // 2
        y = self.winfo_screenheight() // 2 - self.winfo_height() // 2
        self.geometry(f"+{x}+{y}")

    def _submit(self) -> None:
        try:
            password = validate_password(self.new_var.get(), self.confirm_var.get())
        except ValidationError as exc:
            error(self, "Invalid password", str(exc))
            return
        if self.require_different_from_default and password == DEFAULT_ADMIN_PASSWORD:
            error(self, "Invalid password", "Choose a password different from the default.")
            return
        current = None if self.require_different_from_default else self.current_var.get()
        if current == password:
            error(self, "Invalid password", "The new password must be different from the current password.")
            return
        try:
            self.db.change_password(
                self.username,
                password,
                clear_flag=True,
                current_password=current,
            )
        except ValueError as exc:
            error(self, "Update failed", str(exc))
            return
        self.changed = True
        info(self, "Password updated", "Your password was changed. Use the new password next time.")
        self.destroy()
