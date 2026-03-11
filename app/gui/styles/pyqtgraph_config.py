"""PyQtGraph global configuration and per-widget theming helpers.

Call ``configure_pyqtgraph()`` once at application startup (before creating
any ``QApplication``) and ``apply_dark_background()`` on each new
``pg.PlotWidget`` instance.
"""

from __future__ import annotations

import pyqtgraph as pg


def configure_pyqtgraph() -> None:
    """Set process-wide PyQtGraph defaults that must be applied before
    the ``QApplication`` is created."""
    pg.setConfigOptions(
        antialias=True,
        useOpenGL=False,   # safer default; enable per-widget if needed
        background="#11111b",
        foreground="#cdd6f4",
    )


def apply_dark_background(widget: pg.PlotWidget) -> None:
    """Apply a consistent dark theme to *widget*.

    Parameters
    ----------
    widget:
        An already-constructed ``pg.PlotWidget`` owned by a ``CanvasPanel``.
    """
    widget.setBackground("#11111b")
    widget.showGrid(x=True, y=True, alpha=0.15)

    axis_pen = pg.mkPen(color="#45475a", width=1)
    tick_pen = pg.mkPen(color="#a6adc8")
    for axis_name in ("left", "bottom", "right", "top"):
        ax = widget.getAxis(axis_name)
        ax.setPen(axis_pen)
        ax.setTextPen(tick_pen)

    plot_item: pg.PlotItem = widget.getPlotItem()
    plot_item.addLegend(
        offset=(10, 10),
        labelTextSize="10pt",
        labelTextColor="#cdd6f4",
    )
