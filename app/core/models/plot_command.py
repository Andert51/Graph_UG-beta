"""PlotCommand — data-transfer object carrying everything the renderer needs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class PlotKind(Enum):
    """Supported plot primitives."""

    # ── 2D primitives ─────────────────────────────────────────────────
    LINE_2D = auto()
    SCATTER = auto()
    VECTOR_2D = auto()
    BAR = auto()
    HISTOGRAM = auto()
    FILL_BETWEEN = auto()    # shaded region (integral visualisation)
    CONTOUR = auto()         # level curves of f(x, y)
    IMPLICIT_2D = auto()     # implicit curve f(x, y) = 0
    SLOPE_FIELD = auto()     # direction / slope field
    HEATMAP = auto()         # colour-mapped image of f(x, y)
    VECTOR_FIELD_2D = auto() # 2-D vector field with arrows
    STEM = auto()            # stem (lollipop) plot
    STEP = auto()            # staircase / step plot
    PIE = auto()             # pie chart
    ERRORBAR = auto()        # error bar plot

    # ── 3D primitives ─────────────────────────────────────────────────
    SURFACE_3D = auto()      # z = f(x, y) surface
    WIREFRAME_3D = auto()    # wireframe surface
    PARAMETRIC_3D = auto()   # 3-D parametric curve
    SCATTER_3D = auto()      # 3-D scatter points
    SURFACE_PARAM_3D = auto() # parametric surface (u, v) → (x, y, z)
    BAR_3D = auto()          # 3-D bar chart

    # ── Meta ──────────────────────────────────────────────────────────
    CANVAS_CMD = auto()      # axis labels, title, grid toggle


@dataclass(slots=True)
class PlotCommand:
    """Flexible DTO that carries all data required to draw one plot primitive.

    ``data`` is intentionally untyped to keep the contract minimal; each
    ``PlotKind`` documents its expected keys in the renderer implementation.

    Examples
    --------
    LINE_2D / SCATTER: ``{"x": ndarray, "y": ndarray}``
    VECTOR_2D:         ``{"x0": float, "y0": float, "dx": float, "dy": float}``
    BAR:               ``{"x": ndarray, "height": ndarray, "width": float}``
    """

    kind: PlotKind
    data: dict[str, Any]
    label: str = ""
    color: str = "#00bfff"
    line_width: float = 1.5
    extra_opts: dict[str, Any] = field(default_factory=dict)
