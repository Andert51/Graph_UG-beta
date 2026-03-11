"""PyQtGraphRenderer — concrete IRenderer backed by pyqtgraph.

Design decisions
----------------
* The renderer receives the ``pg.PlotWidget`` instance via constructor
  injection.  It never imports or instantiates Qt widgets itself; that
  responsibility belongs to ``CanvasPanel``.
* Each ``PlotKind`` is handled by a dedicated ``_render_*`` method, making it
  trivial to add new primitives without touching the dispatch logic.
* Rendered items are tracked in ``_items`` so the ``clear()`` operation can
  remove them individually (``PlotWidget.clear()`` also clears axes labels /
  legend, which is usually undesirable).
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from app.core.interfaces.i_renderer import IRenderer
from app.core.models.plot_command import PlotCommand, PlotKind


class PyQtGraphRenderer(IRenderer):
    """Renders ``PlotCommand`` DTOs onto an existing ``pg.PlotWidget``."""

    def __init__(self, plot_widget: pg.PlotWidget) -> None:
        """
        Parameters
        ----------
        plot_widget:
            The ``pg.PlotWidget`` owned by ``CanvasPanel``.  Injected at
            construction time — never created internally.
        """
        self._widget: pg.PlotWidget = plot_widget
        self._items: list[pg.GraphicsObject] = []

    # ------------------------------------------------------------------
    # IRenderer interface
    # ------------------------------------------------------------------

    def render(self, command: PlotCommand) -> None:
        """Dispatch *command* to the appropriate private handler."""
        match command.kind:
            case PlotKind.LINE_2D:
                self._render_line_2d(command)
            case PlotKind.SCATTER:
                self._render_scatter(command)
            case PlotKind.VECTOR_2D:
                self._render_vector_2d(command)
            case PlotKind.BAR:
                self._render_bar(command)
            case PlotKind.HISTOGRAM:
                self._render_histogram(command)
            case _:
                raise NotImplementedError(
                    f"PyQtGraphRenderer does not yet support: {command.kind}"
                )

    def clear(self) -> None:
        """Remove all tracked items from the canvas."""
        for item in self._items:
            self._widget.removeItem(item)
        self._items.clear()
        # Also clear any auto-added legend entries
        legend = self._widget.getPlotItem().legend
        if legend is not None:
            legend.clear()

    # ------------------------------------------------------------------
    # Private render strategies
    # ------------------------------------------------------------------

    def _render_line_2d(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (ndarray), ``y`` (ndarray)."""
        x: np.ndarray = cmd.data["x"]
        y: np.ndarray = cmd.data["y"]
        pen = pg.mkPen(color=cmd.color, width=cmd.line_width)
        item = self._widget.plot(
            x, y,
            pen=pen,
            name=cmd.label or None,
        )
        self._items.append(item)

    def _render_scatter(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (ndarray), ``y`` (ndarray)."""
        x: np.ndarray = cmd.data["x"]
        y: np.ndarray = cmd.data["y"]
        scatter = pg.ScatterPlotItem(
            x=x, y=y,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(cmd.color),
            size=8,
            name=cmd.label or None,
        )
        self._widget.addItem(scatter)
        self._items.append(scatter)

    def _render_vector_2d(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x0``, ``y0`` (origin), ``dx``, ``dy`` (components)."""
        x0: float = cmd.data.get("x0", 0.0)
        y0: float = cmd.data.get("y0", 0.0)
        dx: float = cmd.data["dx"]
        dy: float = cmd.data["dy"]

        # Shaft
        shaft = self._widget.plot(
            [x0, x0 + dx], [y0, y0 + dy],
            pen=pg.mkPen(cmd.color, width=cmd.line_width),
        )

        # Arrowhead
        arrow = pg.ArrowItem(
            pos=(x0 + dx, y0 + dy),
            angle=float(np.degrees(np.arctan2(-dy, -dx))),  # points toward origin
            tipAngle=30,
            headLen=15,
            tailLen=0,
            pen=pg.mkPen(cmd.color, width=cmd.line_width),
            brush=pg.mkBrush(cmd.color),
        )
        self._widget.addItem(arrow)
        self._items.extend([shaft, arrow])

    def _render_bar(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (ndarray), ``height`` (ndarray), ``width`` (float)."""
        x: np.ndarray = cmd.data["x"]
        height: np.ndarray = cmd.data["height"]
        width: float = float(cmd.data.get("width", 0.8))
        bar = pg.BarGraphItem(
            x=x, height=height, width=width,
            brush=pg.mkBrush(cmd.color),
        )
        self._widget.addItem(bar)
        self._items.append(bar)

    def _render_histogram(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``values`` (ndarray), ``bins`` (int or ndarray)."""
        values: np.ndarray = cmd.data["values"]
        bins = cmd.data.get("bins", 20)
        counts, edges = np.histogram(values, bins=bins)
        # Represent as bar chart with bin centres as x-positions
        centres = (edges[:-1] + edges[1:]) / 2.0
        width = float(edges[1] - edges[0]) * 0.9
        bar = pg.BarGraphItem(
            x=centres, height=counts.astype(float), width=width,
            brush=pg.mkBrush(cmd.color),
        )
        self._widget.addItem(bar)
        self._items.append(bar)
