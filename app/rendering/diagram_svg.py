import math
from io import BytesIO

import matplotlib

matplotlib.use("Agg")  # no display; background-safe
import matplotlib.patches as patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from app.llm.schemas.diagram import DiagramOutput


_BRANCH_COLOURS = [
    "#2563eb",  # blue
    "#16a34a",  # green
    "#ea580c",  # orange
    "#9333ea",  # purple
    "#dc2626",  # red
    "#0891b2",  # cyan
]


def render_concept_map_svg(diagram: DiagramOutput) -> bytes:
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(-8, 8)
    ax.set_ylim(-6, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.suptitle(diagram.title, fontsize=16, fontweight="bold", y=0.97)

    _draw_node(
        ax,
        x=0,
        y=0,
        text=diagram.central_term,
        colour="#111827",
        fontcolour="white",
        width=3.2,
        height=1.1,
        fontsize=14,
        bold=True,
    )

    n = len(diagram.branches)
    angle_step = 2 * math.pi / n
    for index, branch in enumerate(diagram.branches):
        colour = _BRANCH_COLOURS[index % len(_BRANCH_COLOURS)]
        angle = -math.pi / 2 + index * angle_step
        branch_radius = 4.2
        bx, by = branch_radius * math.cos(angle), branch_radius * math.sin(angle)

        _draw_edge(ax, x1=0, y1=0, x2=bx, y2=by, colour=colour)
        _draw_node(
            ax, x=bx, y=by, text=branch.label, colour=colour, fontcolour="white",
            width=2.6, height=0.8, fontsize=11, bold=True,
        )

        details = branch.details[:5]
        for leaf_index, leaf in enumerate(details):
            leaf_angle = angle + (leaf_index - (len(details) - 1) / 2) * 0.28
            leaf_radius = branch_radius + 2.5
            lx, ly = leaf_radius * math.cos(leaf_angle), leaf_radius * math.sin(leaf_angle)
            _draw_edge(ax, x1=bx, y1=by, x2=lx, y2=ly, colour=colour, lw=0.9)
            _draw_leaf(ax, x=lx, y=ly, text=leaf, colour=colour)

    buffer = BytesIO()
    fig.savefig(buffer, format="svg", bbox_inches="tight", pad_inches=0.4)
    plt.close(fig)
    return buffer.getvalue()


def _draw_node(
    ax,
    *,
    x: float,
    y: float,
    text: str,
    colour: str,
    fontcolour: str = "black",
    width: float = 2.6,
    height: float = 0.8,
    fontsize: int = 11,
    bold: bool = False,
) -> None:
    box = patches.FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle="round,pad=0.12,rounding_size=0.2",
        facecolor=colour,
        edgecolor=colour,
    )
    ax.add_patch(box)
    ax.text(
        x, y, text,
        ha="center", va="center",
        fontsize=fontsize,
        color=fontcolour,
        fontweight="bold" if bold else "normal",
        wrap=True,
    )


def _draw_leaf(ax, *, x: float, y: float, text: str, colour: str) -> None:
    ax.text(
        x, y, text,
        ha="center", va="center",
        fontsize=10,
        color=colour,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": colour, "linewidth": 1},
    )


def _draw_edge(ax, *, x1: float, y1: float, x2: float, y2: float, colour: str, lw: float = 1.5) -> None:
    ax.plot([x1, x2], [y1, y2], color=colour, linewidth=lw, alpha=0.7, zorder=0)
