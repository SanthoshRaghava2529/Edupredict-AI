"""Reusable dashboard widgets."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Iterable, Sequence

from config import PROJECT_ROOT
from tkinter_app.theme import (
    BORDER,
    CARD,
    CONTENT,
    MUTED,
    NAVY,
    TEXT,
    WHITE,
)

LOGO_PATH = PROJECT_ROOT / "assets" / "images" / "logo.png"
ICON_PATH = PROJECT_ROOT / "assets" / "icons" / "app_icon.png"


def set_app_icon(window: tk.Tk | tk.Toplevel) -> None:
    """Attach the generated PNG icon when Pillow assets are present."""
    path = ICON_PATH if ICON_PATH.exists() else LOGO_PATH
    if not path.exists():
        return
    try:
        from PIL import Image, ImageTk

        image = Image.open(path).resize((32, 32))
        photo = ImageTk.PhotoImage(image)
        window.iconphoto(True, photo)
        window._app_icon_image = photo  # prevent garbage collection
    except Exception:
        try:
            window.iconphoto(True, tk.PhotoImage(file=str(path)))
        except Exception:
            pass


class ScrollableFrame(tk.Frame):
    """Vertical scroll container for tall forms."""

    def __init__(self, master, bg: str = WHITE, height: int = 640) -> None:
        super().__init__(master, bg=bg)
        canvas = tk.Canvas(self, bg=bg, highlightthickness=0, height=height)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.body = tk.Frame(canvas, bg=bg)
        self.body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        bind_mousewheel(self.body, canvas)
        self.canvas = canvas


class HoverButton(tk.Button):
    def __init__(self, master, bg, hover_bg, **kwargs) -> None:
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("cursor", "hand2")
        kwargs.setdefault("fg", WHITE)
        kwargs.setdefault("activeforeground", WHITE)
        kwargs.setdefault("font", ("Segoe UI", 10, "bold"))
        kwargs.setdefault("padx", 16)
        kwargs.setdefault("pady", 8)
        super().__init__(master, bg=bg, activebackground=hover_bg, **kwargs)
        self._bg = bg
        self._hover = hover_bg
        self.bind("<Enter>", lambda _e: self.configure(bg=self._hover))
        self.bind("<Leave>", lambda _e: self.configure(bg=self._bg))


class StatCard(tk.Frame):
    def __init__(self, master, title: str, value: str, subtitle: str, accent: str) -> None:
        super().__init__(master, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        bar = tk.Frame(self, bg=accent, width=6)
        bar.pack(side="left", fill="y")
        inner = tk.Frame(self, bg=CARD)
        inner.pack(side="left", fill="both", expand=True, padx=16, pady=14)
        tk.Label(inner, text=title.upper(), bg=CARD, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(inner, text=value, bg=CARD, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Label(inner, text=subtitle, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

    def update_values(self, value: str, subtitle: str | None = None) -> None:
        labels = [w for w in self.winfo_children()[1].winfo_children() if isinstance(w, tk.Label)]
        if len(labels) >= 2:
            labels[1].configure(text=value)
        if subtitle is not None and len(labels) >= 3:
            labels[2].configure(text=subtitle)


class PageHeader(tk.Frame):
    def __init__(self, master, title: str, subtitle: str) -> None:
        super().__init__(master, bg=CONTENT)
        tk.Label(self, text=title, bg=CONTENT, fg=NAVY, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(self, text=subtitle, bg=CONTENT, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))


class Card(tk.Frame):
    def __init__(self, master, title: str | None = None, padding: int = 16) -> None:
        super().__init__(master, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        if title:
            tk.Label(self, text=title, bg=CARD, fg=NAVY, font=("Segoe UI", 12, "bold")).pack(
                anchor="w", padx=padding, pady=(padding, 8)
            )
            self.body = tk.Frame(self, bg=CARD)
            self.body.pack(fill="both", expand=True, padx=padding, pady=(0, padding))
        else:
            self.body = tk.Frame(self, bg=CARD)
            self.body.pack(fill="both", expand=True, padx=padding, pady=padding)


class DataTable(tk.Frame):
    def __init__(self, master, columns: Sequence[tuple[str, str, int]], height: int = 12) -> None:
        super().__init__(master, bg=WHITE)
        ids = [c[0] for c in columns]
        self.tree = ttk.Treeview(self, columns=ids, show="headings", height=height)
        for key, heading, width in columns:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, anchor="w", stretch=True)
        self.tree.tag_configure("odd", background="#F8FAFC")
        self.tree.tag_configure("even", background=WHITE)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def fill(self, rows: Iterable[Sequence]) -> None:
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(rows):
            tag = "odd" if index % 2 else "even"
            self.tree.insert("", "end", values=row, tags=(tag,))

    def selected_values(self) -> tuple | None:
        selected = self.tree.selection()
        if not selected:
            return None
        return self.tree.item(selected[0], "values")

    def bind(self, sequence=None, func=None, add=None):
        return self.tree.bind(sequence, func, add)


def labeled_entry(parent, label: str, var: tk.Variable, show: str | None = None) -> ttk.Entry:
    wrap = tk.Frame(parent, bg=parent.cget("bg"))
    wrap.pack(fill="x", pady=6)
    tk.Label(wrap, text=label, bg=parent.cget("bg"), fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
    entry = ttk.Entry(wrap, textvariable=var, show=show or "")
    entry.pack(fill="x", pady=(4, 0))
    return entry


def labeled_combo(parent, label: str, var: tk.Variable, values: Sequence[str], width: int = 20) -> ttk.Combobox:
    wrap = tk.Frame(parent, bg=parent.cget("bg"))
    wrap.pack(fill="x", pady=6)
    tk.Label(wrap, text=label, bg=parent.cget("bg"), fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
    combo = ttk.Combobox(wrap, textvariable=var, values=list(values), state="readonly", width=width)
    combo.pack(fill="x", pady=(4, 0))
    return combo


def form_grid(parent, fields: Sequence[tuple[str, tk.Widget]]) -> None:
    for row, (label, widget) in enumerate(fields):
        tk.Label(parent, text=label, bg=parent.cget("bg"), fg=TEXT, font=("Segoe UI", 9, "bold")).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=6
        )
        widget.grid(row=row, column=1, sticky="ew", pady=6)
    parent.grid_columnconfigure(1, weight=1)


def confirm(parent, title: str, message: str) -> bool:
    from tkinter import messagebox

    return messagebox.askyesno(title, message, parent=parent)


def info(parent, title: str, message: str) -> None:
    from tkinter import messagebox

    messagebox.showinfo(title, message, parent=parent)


def error(parent, title: str, message: str) -> None:
    from tkinter import messagebox

    messagebox.showerror(title, message, parent=parent)


def warn(parent, title: str, message: str) -> None:
    from tkinter import messagebox

    messagebox.showwarning(title, message, parent=parent)


def bind_mousewheel(widget: tk.Widget, target: tk.Canvas) -> None:
    widget.bind("<Enter>", lambda _e: target.bind_all("<MouseWheel>", lambda e: target.yview_scroll(int(-1 * (e.delta / 120)), "units")))
    widget.bind("<Leave>", lambda _e: target.unbind_all("<MouseWheel>"))
