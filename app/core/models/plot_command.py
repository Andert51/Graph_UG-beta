"""PlotCommand — data-transfer object carrying everything the renderer needs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class PlotKind(Enum):
    """Supported plot primitives in phase 1."""

    LINE_2D = auto()
    SCATTER = auto()
    VECTOR_2D = auto()
    BAR = auto()
    HISTOGRAM = auto()
    SURFACE_3D = auto()  # reserved — phase 2


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
