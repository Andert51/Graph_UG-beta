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
from app.utils.logger import get_logger

_log = get_logger(__name__)


class PyQtGraphRenderer(IRenderer):
    """Renders ``PlotCommand`` DTOs onto an existing ``pg.PlotWidget``."""

    # Colour cycle for automatic plot colouring (Catppuccin-inspired)
    _COLOR_CYCLE: list[str] = [
        "#89b4fa",  # blue
        "#f38ba8",  # red
        "#a6e3a1",  # green
        "#fab387",  # peach
        "#cba6f7",  # mauve
        "#f9e2af",  # yellow
        "#94e2d5",  # teal
        "#f5c2e7",  # pink
        "#74c7ec",  # sapphire
        "#eba0ac",  # maroon
    ]

    def __init__(self, plot_widget: pg.PlotWidget) -> None:
        self._widget: pg.PlotWidget = plot_widget
        self._items: list[pg.GraphicsObject] = []
        self._color_index: int = 0
        self._grid_visible: bool = False

    # ------------------------------------------------------------------
    # IRenderer interface
    # ------------------------------------------------------------------

    def render(self, command: PlotCommand) -> None:
        """Dispatch *command* to the appropriate private handler."""
        _log.debug("render: kind=%s label=%r", command.kind.name, command.label)
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
            case PlotKind.FILL_BETWEEN:
                self._render_fill_between(command)
            case PlotKind.CONTOUR:
                self._render_contour(command)
            case PlotKind.IMPLICIT_2D:
                self._render_implicit_2d(command)
            case PlotKind.SLOPE_FIELD:
                self._render_slope_field(command)
            case PlotKind.HEATMAP:
                self._render_heatmap(command)
            case PlotKind.VECTOR_FIELD_2D:
                self._render_vector_field_2d(command)
            case PlotKind.STEM:
                self._render_stem(command)
            case PlotKind.STEP:
                self._render_step(command)
            case PlotKind.PIE:
                self._render_pie(command)
            case PlotKind.ERRORBAR:
                self._render_errorbar(command)
            case PlotKind.CANVAS_CMD:
                self._apply_canvas_cmd(command)
            case _:
                raise NotImplementedError(
                    f"PyQtGraphRenderer does not yet support: {command.kind}"
                )

    def clear(self) -> None:
        """Remove all tracked items from the canvas."""
        for item in self._items:
            self._widget.removeItem(item)
        self._items.clear()
        self._color_index = 0
        # Also clear any auto-added legend entries
        legend = self._widget.getPlotItem().legend
        if legend is not None:
            legend.clear()

    # ------------------------------------------------------------------
    # Colour cycling
    # ------------------------------------------------------------------

    def _next_color(self) -> str:
        """Return the next colour in the cycle."""
        color = self._COLOR_CYCLE[self._color_index % len(self._COLOR_CYCLE)]
        self._color_index += 1
        return color

    def _resolve_color(self, cmd: PlotCommand) -> str:
        """Use the command's color if explicitly set, otherwise auto-cycle."""
        if cmd.color != "#00bfff":
            return cmd.color
        return self._next_color()

    # ------------------------------------------------------------------
    # Private render strategies
    # ------------------------------------------------------------------

    def _render_line_2d(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (ndarray), ``y`` (ndarray)."""
        x: np.ndarray = cmd.data["x"]
        y: np.ndarray = cmd.data["y"]
        color = self._resolve_color(cmd)
        pen = pg.mkPen(color=color, width=cmd.line_width)
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
        color = self._resolve_color(cmd)
        scatter = pg.ScatterPlotItem(
            x=x, y=y,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(color),
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
        color = self._resolve_color(cmd)

        # Shaft
        shaft = self._widget.plot(
            [x0, x0 + dx], [y0, y0 + dy],
            pen=pg.mkPen(color, width=cmd.line_width),
        )

        # Arrowhead
        arrow = pg.ArrowItem(
            pos=(x0 + dx, y0 + dy),
            angle=float(np.degrees(np.arctan2(-dy, -dx))),
            tipAngle=30,
            headLen=15,
            tailLen=0,
            pen=pg.mkPen(color, width=cmd.line_width),
            brush=pg.mkBrush(color),
        )
        self._widget.addItem(arrow)
        self._items.extend([shaft, arrow])

    def _render_bar(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (ndarray), ``height`` (ndarray), ``width`` (float)."""
        x: np.ndarray = cmd.data["x"]
        height: np.ndarray = cmd.data["height"]
        width: float = float(cmd.data.get("width", 0.8))
        color = self._resolve_color(cmd)
        bar = pg.BarGraphItem(
            x=x, height=height, width=width,
            brush=pg.mkBrush(color),
        )
        self._widget.addItem(bar)
        self._items.append(bar)

    def _render_histogram(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``values`` (ndarray), ``bins`` (int or ndarray)."""
        values: np.ndarray = cmd.data["values"]
        bins = cmd.data.get("bins", 20)
        counts, edges = np.histogram(values, bins=bins)
        centres = (edges[:-1] + edges[1:]) / 2.0
        width = float(edges[1] - edges[0]) * 0.9
        color = self._resolve_color(cmd)
        bar = pg.BarGraphItem(
            x=centres, height=counts.astype(float), width=width,
            brush=pg.mkBrush(color),
        )
        self._widget.addItem(bar)
        self._items.append(bar)

    def _render_fill_between(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x``, ``y1``, ``y2`` (ndarrays).  Shades region between curves."""
        x = cmd.data["x"]
        y1 = cmd.data["y1"]
        y2 = cmd.data["y2"]
        color = self._resolve_color(cmd)

        # Draw the two boundary curves as PlotDataItems (needed by FillBetweenItem)
        pen1 = pg.mkPen(color=color, width=0)  # invisible pen
        curve1 = pg.PlotDataItem(x, y1, pen=pen1)
        curve2 = pg.PlotDataItem(x, y2, pen=pen1)
        self._widget.addItem(curve1)
        self._widget.addItem(curve2)

        fill = pg.FillBetweenItem(curve1, curve2, brush=pg.mkBrush(color + "40"))
        self._widget.addItem(fill)
        self._items.extend([curve1, curve2, fill])

    def _render_contour(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``z`` (2D), ``x_range``, ``y_range``, ``levels``."""
        z: np.ndarray = cmd.data["z"]
        x_range = cmd.data["x_range"]
        y_range = cmd.data["y_range"]
        levels = cmd.data["levels"]

        for level in levels:
            color = self._next_color()
            iso = pg.IsocurveItem(data=z, level=level, pen=pg.mkPen(color, width=1.5))
            # Map data coordinates to real-world coordinates
            iso.setPos(x_range[0], y_range[0])
            n_rows, n_cols = z.shape
            sx = (x_range[1] - x_range[0]) / n_cols
            sy = (y_range[1] - y_range[0]) / n_rows
            iso.setTransform(pg.QtGui.QTransform().scale(sx, sy))
            self._widget.addItem(iso)
            self._items.append(iso)

    def _render_implicit_2d(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``z`` (2D), ``x_range``, ``y_range``.  Draws the f(x,y)=0 contour."""
        z: np.ndarray = cmd.data["z"]
        x_range = cmd.data["x_range"]
        y_range = cmd.data["y_range"]
        color = self._resolve_color(cmd)

        iso = pg.IsocurveItem(data=z, level=0.0, pen=pg.mkPen(color, width=2.0))
        iso.setPos(x_range[0], y_range[0])
        n_rows, n_cols = z.shape
        sx = (x_range[1] - x_range[0]) / n_cols
        sy = (y_range[1] - y_range[0]) / n_rows
        iso.setTransform(pg.QtGui.QTransform().scale(sx, sy))
        self._widget.addItem(iso)
        self._items.append(iso)

    def _render_slope_field(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``X``, ``Y``, ``DX``, ``DY`` (2D grids)."""
        X: np.ndarray = cmd.data["X"]
        Y: np.ndarray = cmd.data["Y"]
        DX: np.ndarray = cmd.data["DX"]
        DY: np.ndarray = cmd.data["DY"]
        color = self._resolve_color(cmd)
        pen = pg.mkPen(color, width=1.0)

        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                cx, cy = float(X[i, j]), float(Y[i, j])
                dx, dy = float(DX[i, j]), float(DY[i, j])
                line = pg.PlotDataItem(
                    [cx - dx, cx + dx],
                    [cy - dy, cy + dy],
                    pen=pen,
                )
                self._widget.addItem(line)
                self._items.append(line)

    def _apply_canvas_cmd(self, cmd: PlotCommand) -> None:
        """Handle canvas meta-commands: xlabel, ylabel, title, grid, log scale."""
        action = cmd.data.get("cmd")
        plot_item = self._widget.getPlotItem()
        if action == "xlabel":
            plot_item.setLabel("bottom", cmd.data["text"])
        elif action == "ylabel":
            plot_item.setLabel("left", cmd.data["text"])
        elif action == "title":
            plot_item.setTitle(cmd.data["text"])
        elif action == "grid":
            visible = cmd.data.get("visible")
            if visible is None:
                self._grid_visible = not self._grid_visible
            else:
                self._grid_visible = visible
            plot_item.showGrid(x=self._grid_visible, y=self._grid_visible, alpha=0.3)
        elif action == "loglog":
            plot_item.setLogMode(x=True, y=True)
        elif action == "semilogx":
            plot_item.setLogMode(x=True, y=False)
        elif action == "semilogy":
            plot_item.setLogMode(x=False, y=True)

    # ------------------------------------------------------------------
    # Phase 7 — New 2-D render strategies
    # ------------------------------------------------------------------

    def _render_heatmap(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``z`` (2D), ``x_range``, ``y_range``."""
        z: np.ndarray = cmd.data["z"]
        x_range = cmd.data["x_range"]
        y_range = cmd.data["y_range"]
        img = pg.ImageItem(z.T)
        # Map data coords → pixel coords via transform
        n_rows, n_cols = z.shape
        sx = (x_range[1] - x_range[0]) / n_cols
        sy = (y_range[1] - y_range[0]) / n_rows
        img.setTransform(pg.QtGui.QTransform().translate(x_range[0], y_range[0]).scale(sx, sy))
        # Apply a colour map
        cmap = pg.colormap.get("viridis", source="matplotlib")
        img.setLookupTable(cmap.getLookupTable(nPts=256))
        self._widget.addItem(img)
        self._items.append(img)

    def _render_vector_field_2d(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``X``, ``Y``, ``U``, ``V``, ``mag`` (2D grids)."""
        X: np.ndarray = cmd.data["X"]
        Y: np.ndarray = cmd.data["Y"]
        U: np.ndarray = cmd.data["U"]
        V: np.ndarray = cmd.data["V"]
        color = self._resolve_color(cmd)
        pen = pg.mkPen(color, width=1.5)

        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                cx, cy = float(X[i, j]), float(Y[i, j])
                dx, dy = float(U[i, j]), float(V[i, j])
                # Shaft
                line = pg.PlotDataItem([cx, cx + dx], [cy, cy + dy], pen=pen)
                self._widget.addItem(line)
                self._items.append(line)
                # Small arrowhead
                if abs(dx) + abs(dy) > 1e-10:
                    arrow = pg.ArrowItem(
                        pos=(cx + dx, cy + dy),
                        angle=float(np.degrees(np.arctan2(-dy, -dx))),
                        tipAngle=25, headLen=8, tailLen=0,
                        pen=pg.mkPen(color, width=1),
                        brush=pg.mkBrush(color),
                    )
                    self._widget.addItem(arrow)
                    self._items.append(arrow)

    def _render_stem(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (ndarray), ``y`` (ndarray).  Stem/lollipop plot."""
        x: np.ndarray = cmd.data["x"]
        y: np.ndarray = cmd.data["y"]
        color = self._resolve_color(cmd)
        pen = pg.mkPen(color, width=1.5)

        # Vertical stems
        for xi, yi in zip(x, y):
            stem = pg.PlotDataItem([float(xi), float(xi)], [0.0, float(yi)], pen=pen)
            self._widget.addItem(stem)
            self._items.append(stem)

        # Marker dots at top
        scatter = pg.ScatterPlotItem(
            x=x, y=y,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(color),
            size=8,
        )
        self._widget.addItem(scatter)
        self._items.append(scatter)

        # Baseline
        baseline = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen("#585b70", width=0.5))
        self._widget.addItem(baseline)
        self._items.append(baseline)

    def _render_step(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (ndarray), ``y`` (ndarray).  Staircase plot."""
        x: np.ndarray = cmd.data["x"]
        y: np.ndarray = cmd.data["y"]
        color = self._resolve_color(cmd)
        # Build staircase arrays
        xs = np.repeat(x, 2)[1:]
        ys = np.repeat(y, 2)[:-1]
        pen = pg.mkPen(color=color, width=cmd.line_width)
        item = self._widget.plot(xs, ys, pen=pen, name=cmd.label or None)
        self._items.append(item)

    def _render_pie(self, cmd: PlotCommand) -> None:
        """Render a pie chart approximation as a stacked horizontal bar."""
        values: np.ndarray = cmd.data["values"]
        total = float(np.sum(values))
        if total == 0:
            return
        fractions = values / total
        # Draw as coloured bar segments
        start = 0.0
        for frac in fractions:
            color = self._next_color()
            bar = pg.BarGraphItem(
                x=[start + frac / 2], height=[1.0], width=frac,
                brush=pg.mkBrush(color),
            )
            self._widget.addItem(bar)
            self._items.append(bar)
            start += frac

    def _render_errorbar(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x``, ``y``, ``err`` (ndarrays).  Plot with error bars."""
        x: np.ndarray = cmd.data["x"]
        y: np.ndarray = cmd.data["y"]
        err: np.ndarray = cmd.data["err"]
        color = self._resolve_color(cmd)

        # Line through points
        pen = pg.mkPen(color=color, width=cmd.line_width)
        item = self._widget.plot(x, y, pen=pen)
        self._items.append(item)

        # Error bars
        err_item = pg.ErrorBarItem(
            x=x, y=y,
            top=err, bottom=err,
            beam=0.3,
            pen=pg.mkPen(color, width=1.0),
        )
        self._widget.addItem(err_item)
        self._items.append(err_item)

        # Scatter markers
        scatter = pg.ScatterPlotItem(
            x=x, y=y,
            pen=pg.mkPen(None), brush=pg.mkBrush(color), size=6,
        )
        self._widget.addItem(scatter)
        self._items.append(scatter)
