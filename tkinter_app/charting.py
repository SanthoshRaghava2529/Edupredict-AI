"""Matplotlib helpers styled for the navy dashboard."""

from __future__ import annotations

from typing import Sequence

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from tkinter_app.theme import ACCENT, NAVY, MUTED

PALETTE = ["#3B82F6", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6"]


def embed_figure(parent, figure: Figure) -> FigureCanvasTkAgg:
    canvas = FigureCanvasTkAgg(figure, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    return canvas


def new_figure(width: float = 5.2, height: float = 3.2) -> Figure:
    figure = Figure(figsize=(width, height), dpi=100)
    figure.patch.set_facecolor("white")
    return figure


def bar_chart(figure: Figure, labels: Sequence[str], values: Sequence[float], title: str, color: str = ACCENT) -> None:
    figure.clear()
    axes = figure.add_subplot(111)
    axes.set_facecolor("white")
    if not labels:
        axes.text(0.5, 0.5, "No data yet", ha="center", va="center", color=MUTED)
        axes.set_axis_off()
        axes.set_title(title, color=NAVY, fontsize=11, fontweight="bold")
        return
    axes.bar(list(labels), list(values), color=color, width=0.62, zorder=3)
    axes.set_title(title, color=NAVY, fontsize=11, fontweight="bold", pad=10)
    axes.tick_params(colors=MUTED, labelsize=8)
    axes.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    for spine in ("top", "right"):
        axes.spines[spine].set_visible(False)
    figure.tight_layout()


def pie_chart(figure: Figure, labels: Sequence[str], values: Sequence[float], title: str) -> None:
    figure.clear()
    axes = figure.add_subplot(111)
    if sum(values) <= 0:
        axes.text(0.5, 0.5, "No data yet", ha="center", va="center", color=MUTED)
        axes.set_axis_off()
        axes.set_title(title, color=NAVY, fontsize=11, fontweight="bold")
        return
    axes.pie(
        list(values),
        labels=list(labels),
        colors=PALETTE[: len(labels)],
        autopct=lambda p: f"{p:.0f}%" if p >= 5 else "",
        startangle=90,
        textprops={"fontsize": 8, "color": NAVY},
        wedgeprops={"linewidth": 1, "edgecolor": "white"},
    )
    axes.set_title(title, color=NAVY, fontsize=11, fontweight="bold", pad=8)
    figure.tight_layout()


def confusion_heatmap(figure: Figure, matrix, labels: Sequence[str], title: str) -> None:
    figure.clear()
    axes = figure.add_subplot(111)
    if matrix is None or len(matrix) == 0:
        axes.text(0.5, 0.5, "Train the model to see the confusion matrix", ha="center", va="center", color=MUTED)
        axes.set_axis_off()
        axes.set_title(title, color=NAVY, fontsize=11, fontweight="bold")
        return
    image = axes.imshow(matrix, cmap="Blues")
    axes.set_xticks(range(len(labels)))
    axes.set_yticks(range(len(labels)))
    axes.set_xticklabels(list(labels), fontsize=8, rotation=20, ha="right")
    axes.set_yticklabels(list(labels), fontsize=8)
    axes.set_xlabel("Predicted", color=MUTED, fontsize=8)
    axes.set_ylabel("Actual", color=MUTED, fontsize=8)
    axes.set_title(title, color=NAVY, fontsize=11, fontweight="bold", pad=8)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            axes.text(j, i, str(value), ha="center", va="center", color=NAVY, fontsize=8)
    figure.colorbar(image, ax=axes, fraction=0.046, pad=0.04)
    figure.tight_layout()


def horizontal_bar(figure: Figure, labels: Sequence[str], values: Sequence[float], title: str) -> None:
    figure.clear()
    axes = figure.add_subplot(111)
    if not labels:
        axes.text(0.5, 0.5, "No data yet", ha="center", va="center", color=MUTED)
        axes.set_axis_off()
        axes.set_title(title, color=NAVY, fontsize=11, fontweight="bold")
        return
    colors = PALETTE[: max(1, len(labels))]
    axes.barh(list(labels), list(values), color=colors, zorder=3)
    axes.set_title(title, color=NAVY, fontsize=11, fontweight="bold", pad=10)
    axes.tick_params(colors=MUTED, labelsize=8)
    axes.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
    for spine in ("top", "right"):
        axes.spines[spine].set_visible(False)
    figure.tight_layout()
