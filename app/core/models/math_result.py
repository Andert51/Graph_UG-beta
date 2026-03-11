"""MathResult — the single return type of IEvaluator.evaluate()."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.models.plot_command import PlotCommand


@dataclass(slots=True)
class MathResult:
    """Encapsulates all possible outcomes of a single evaluated expression.

    Invariant: if ``error`` is not ``None`` the other fields carry no
    meaningful data and the controller should forward the error to the View
    without attempting to render.
    """

    value: Any = None
    """Numeric or symbolic result (``float``, ``np.ndarray``, ``sympy.Expr``, …)."""

    plot_commands: list[PlotCommand] = field(default_factory=list)
    """Ordered list of plot primitives to be forwarded to the renderer."""

    output_text: str = ""
    """Human-readable representation that the console panel will display."""

    error: str | None = None
    """Non-``None`` signals that evaluation failed; contains the detail message."""

    @property
    def is_error(self) -> bool:
        """Return ``True`` when the result represents a failure."""
        return self.error is not None

    @property
    def has_plot(self) -> bool:
        """Return ``True`` when there is at least one plot command to render."""
        return bool(self.plot_commands)
