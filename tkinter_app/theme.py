"""Navy-and-white visual system for ttk and custom widgets."""

from __future__ import annotations

from tkinter import ttk

NAVY = "#0B1D36"
NAVY_MID = "#102A4A"
NAVY_LIGHT = "#163A63"
SIDEBAR = "#0E2744"
ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
ACCENT_SOFT = "#DBEAFE"
WHITE = "#FFFFFF"
CONTENT = "#F3F6FB"
CARD = "#FFFFFF"
TEXT = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"
SUCCESS = "#059669"
SUCCESS_BG = "#ECFDF5"
WARNING = "#D97706"
WARNING_BG = "#FFFBEB"
DANGER = "#DC2626"
DANGER_BG = "#FEF2F2"
PURPLE = "#7C3AED"
TITLE_FONT = ("Segoe UI", 22, "bold")
HEADING_FONT = ("Segoe UI", 16, "bold")
SUBHEAD_FONT = ("Segoe UI", 12, "bold")
BODY_FONT = ("Segoe UI", 10)
SMALL_FONT = ("Segoe UI", 9)


def apply_theme(root) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", font=BODY_FONT, background=CONTENT, foreground=TEXT)
    style.configure("TFrame", background=CONTENT)
    style.configure("Card.TFrame", background=CARD)
    style.configure("Navy.TFrame", background=NAVY)
    style.configure("Sidebar.TFrame", background=SIDEBAR)
    style.configure("White.TFrame", background=WHITE)
    style.configure("TLabel", background=CONTENT, foreground=TEXT, font=BODY_FONT)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=BODY_FONT)
    style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=BODY_FONT)
    style.configure("Title.TLabel", background=CONTENT, foreground=TEXT, font=TITLE_FONT)
    style.configure("Heading.TLabel", background=CONTENT, foreground=TEXT, font=HEADING_FONT)
    style.configure("CardHeading.TLabel", background=CARD, foreground=TEXT, font=SUBHEAD_FONT)
    style.configure("WhiteTitle.TLabel", background=NAVY, foreground=WHITE, font=TITLE_FONT)
    style.configure("White.TLabel", background=NAVY, foreground=WHITE, font=BODY_FONT)
    style.configure("SidebarTitle.TLabel", background=SIDEBAR, foreground=WHITE, font=("Segoe UI", 14, "bold"))
    style.configure("SidebarSub.TLabel", background=SIDEBAR, foreground="#93C5FD", font=SMALL_FONT)
    style.configure("SidebarUser.TLabel", background=SIDEBAR, foreground="#CBD5E1", font=SMALL_FONT)

    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground=WHITE,
        font=("Segoe UI", 10, "bold"),
        padding=(14, 8),
        borderwidth=0,
        focusthickness=0,
    )
    style.map("Accent.TButton", background=[("active", ACCENT_HOVER), ("pressed", "#1D4ED8")])

    style.configure(
        "Secondary.TButton",
        background=WHITE,
        foreground=NAVY,
        font=("Segoe UI", 10, "bold"),
        padding=(12, 7),
        borderwidth=1,
        relief="solid",
    )
    style.map("Secondary.TButton", background=[("active", ACCENT_SOFT)])

    style.configure(
        "Danger.TButton",
        background=DANGER,
        foreground=WHITE,
        font=("Segoe UI", 10, "bold"),
        padding=(12, 7),
        borderwidth=0,
    )
    style.map("Danger.TButton", background=[("active", "#B91C1C")])

    style.configure(
        "Ghost.TButton",
        background=SIDEBAR,
        foreground="#E2E8F0",
        font=("Segoe UI", 10),
        padding=(16, 11),
        anchor="w",
        borderwidth=0,
    )
    style.map("Ghost.TButton", background=[("active", NAVY_LIGHT)], foreground=[("active", WHITE)])

    style.configure(
        "NavActive.TButton",
        background=ACCENT,
        foreground=WHITE,
        font=("Segoe UI", 10, "bold"),
        padding=(16, 11),
        anchor="w",
        borderwidth=0,
    )

    style.configure("TEntry", fieldbackground=WHITE, padding=7)
    style.configure("TCombobox", padding=6, fieldbackground=WHITE)
    style.configure("TNotebook", background=CONTENT, borderwidth=0)
    style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10, "bold"))
    style.map("TNotebook.Tab", background=[("selected", WHITE)], foreground=[("selected", NAVY)])

    style.configure(
        "Treeview",
        background=WHITE,
        fieldbackground=WHITE,
        foreground=TEXT,
        rowheight=30,
        font=BODY_FONT,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=NAVY,
        foreground=WHITE,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        padding=8,
    )
    style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", WHITE)])
    style.map("Treeview.Heading", background=[("active", NAVY_LIGHT)])
    return style
