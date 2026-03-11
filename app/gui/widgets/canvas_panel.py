"""CanvasPanel — right-side canvas container with 2-D and 3-D views.

Owns both a ``pg.PlotWidget`` (2-D) and a ``gl.GLViewWidget`` (3-D),
stacked inside a ``QStackedWidget`` so only one is visible at a time.
Provides a toolbar with a 2-D / 3-D toggle button plus 3-D navigation
presets and a camera-info overlay.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.gui.styles.pyqtgraph_config import apply_dark_background


class CanvasPanel(QWidget):
    """Dual-mode canvas panel: 2-D (PyQtGraph) and 3-D (OpenGL)."""

    mode_changed: Signal = Signal(str)
    """Emitted with ``"2d"`` or ``"3d"`` when the active view switches."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode: str = "2d"
        self._build_ui()
        # Timer for camera info updates (only active in 3D mode)
        self._cam_timer = QTimer(self)
        self._cam_timer.setInterval(250)
        self._cam_timer.timeout.connect(self._update_camera_info)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_palette(self, palette) -> None:
        """Update canvas colours from a theme *palette*."""
        # 2-D canvas
        self._plot_widget.setBackground(palette.canvas_bg)
        axis_pen = pg.mkPen(palette.axis_colour, width=1)
        for side in ("bottom", "left"):
            ax = self._plot_widget.getAxis(side)
            ax.setPen(axis_pen)
            ax.setTextPen(pg.mkPen(palette.fg_secondary))
        # 3-D canvas
        self._gl_widget.setBackgroundColor(palette.canvas_bg)

    @property
    def plot_widget(self) -> pg.PlotWidget:
        """The 2-D ``pg.PlotWidget`` — inject into the 2-D renderer."""
        return self._plot_widget

    @property
    def gl_widget(self) -> gl.GLViewWidget:
        """The 3-D ``gl.GLViewWidget`` — inject into the 3-D renderer."""
        return self._gl_widget

    @property
    def mode(self) -> str:
        """Current canvas mode: ``"2d"`` or ``"3d"``."""
        return self._mode

    def set_mode(self, mode: str) -> None:
        """Switch visible canvas to *mode* (``"2d"`` or ``"3d"``)."""
        if mode not in ("2d", "3d"):
            return
        self._mode = mode
        self._stack.setCurrentIndex(0 if mode == "2d" else 1)
        self._btn_2d.setEnabled(mode != "2d")
        self._btn_3d.setEnabled(mode != "3d")
        # Show/hide 3D-specific controls
        self._nav_bar.setVisible(mode == "3d")
        self._cam_label.setVisible(mode == "3d")
        if mode == "3d":
            self._cam_timer.start()
            self._update_camera_info()
        else:
            self._cam_timer.stop()
        self.mode_changed.emit(mode)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header toolbar ────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(26)
        header.setStyleSheet(
            "background:#181825; color:#a6adc8; font-size:10px;"
            "border-bottom:1px solid #313244;"
        )
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(6, 0, 6, 0)
        hlay.setSpacing(4)

        lbl = QLabel("Canvas")
        lbl.setStyleSheet(
            "letter-spacing:1.2px; text-transform:uppercase;"
            "background:transparent; border:none;"
        )
        hlay.addWidget(lbl)
        hlay.addStretch()

        btn_style = (
            "QPushButton { background:#1e1e2e; color:#cdd6f4; border:1px solid #313244;"
            "  border-radius:3px; padding:1px 8px; font-size:10px; }"
            "QPushButton:disabled { background:#313244; color:#6c7086; }"
            "QPushButton:hover:!disabled { background:#45475a; }"
        )

        self._btn_2d = QPushButton("2D")
        self._btn_2d.setFixedHeight(20)
        self._btn_2d.setStyleSheet(btn_style)
        self._btn_2d.setEnabled(False)  # 2D is active by default
        self._btn_2d.clicked.connect(lambda: self.set_mode("2d"))
        hlay.addWidget(self._btn_2d)

        self._btn_3d = QPushButton("3D")
        self._btn_3d.setFixedHeight(20)
        self._btn_3d.setStyleSheet(btn_style)
        self._btn_3d.clicked.connect(lambda: self.set_mode("3d"))
        hlay.addWidget(self._btn_3d)

        root.addWidget(header)

        # ── Stacked views ─────────────────────────────────────────────
        self._stack = QStackedWidget()

        # 2-D canvas (index 0)
        self._plot_widget = pg.PlotWidget()
        apply_dark_background(self._plot_widget)
        self._stack.addWidget(self._plot_widget)

        # 3-D canvas (index 1)
        self._gl_widget = gl.GLViewWidget()
        self._gl_widget.setBackgroundColor("#11111b")
        self._gl_widget.setCameraPosition(distance=25, elevation=30, azimuth=45)
        # Add a grid plane
        grid = gl.GLGridItem()
        grid.setSize(20, 20)
        grid.setSpacing(2, 2)
        grid.setColor((0.31, 0.31, 0.42, 0.3))
        self._gl_widget.addItem(grid)

        # ── XYZ axis guides ───────────────────────────────────────────
        axis_len = 12.0
        # X axis — red
        x_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [axis_len, 0, 0]]),
            color=(0.95, 0.34, 0.42, 0.9), width=2.0, antialias=True,
        )
        self._gl_widget.addItem(x_axis)
        # Y axis — green
        y_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, axis_len, 0]]),
            color=(0.65, 0.89, 0.63, 0.9), width=2.0, antialias=True,
        )
        self._gl_widget.addItem(y_axis)
        # Z axis — blue
        z_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, 0, axis_len]]),
            color=(0.54, 0.71, 0.98, 0.9), width=2.0, antialias=True,
        )
        self._gl_widget.addItem(z_axis)

        # Axis tick marks (small cross-hairs every 2 units)
        for i in range(2, int(axis_len) + 1, 2):
            sz = 0.15
            for ax_vals, color in [
                (np.array([[i, -sz, 0], [i, sz, 0]]), (0.95, 0.34, 0.42, 0.6)),
                (np.array([[-sz, i, 0], [sz, i, 0]]), (0.65, 0.89, 0.63, 0.6)),
                (np.array([[-sz, 0, i], [sz, 0, i]]), (0.54, 0.71, 0.98, 0.6)),
            ]:
                tick = gl.GLLinePlotItem(pos=ax_vals, color=color, width=1.0, antialias=True)
                self._gl_widget.addItem(tick)

        self._stack.addWidget(self._gl_widget)

        self._stack.setCurrentIndex(0)
        root.addWidget(self._stack)

        # ── 3D Navigation preset bar ─────────────────────────────────
        self._nav_bar = QWidget()
        self._nav_bar.setFixedHeight(30)
        self._nav_bar.setStyleSheet(
            "background:#181825; border-top:1px solid #313244;"
        )
        nav_lay = QHBoxLayout(self._nav_bar)
        nav_lay.setContentsMargins(6, 2, 6, 2)
        nav_lay.setSpacing(4)

        nav_style = (
            "QPushButton { background:#1e1e2e; color:#cdd6f4; border:1px solid #313244;"
            "  border-radius:3px; padding:1px 10px; font-size:10px; }"
            "QPushButton:hover { background:#45475a; }"
        )
        for label, elev, azim in [
            ("Front", 0, 0), ("Top", 90, 0), ("Side", 0, 90),
            ("Iso", 30, 45), ("Reset", 30, 45),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            btn.setStyleSheet(nav_style)
            if label == "Reset":
                btn.clicked.connect(
                    lambda _=False, d=25, e=30, a=45: self._gl_widget.setCameraPosition(
                        distance=d, elevation=e, azimuth=a
                    )
                )
            else:
                btn.clicked.connect(
                    lambda _=False, e=elev, a=azim: self._gl_widget.setCameraPosition(
                        elevation=e, azimuth=a
                    )
                )
            nav_lay.addWidget(btn)

        nav_lay.addStretch()
        self._nav_bar.setVisible(False)
        root.addWidget(self._nav_bar)

        # ── Camera info label ─────────────────────────────────────────
        self._cam_label = QLabel()
        self._cam_label.setFixedHeight(18)
        self._cam_label.setStyleSheet(
            "background:#181825; color:#6c7086; font-size:9px;"
            "padding-left:8px; border-top:1px solid #313244;"
            "font-family:monospace;"
        )
        self._cam_label.setVisible(False)
        root.addWidget(self._cam_label)

    def _update_camera_info(self) -> None:
        """Refresh the camera overlay with current distance/elevation/azimuth."""
        params = self._gl_widget.cameraParams()
        d = params.get("distance", 0)
        e = params.get("elevation", 0)
        a = params.get("azimuth", 0)
        self._cam_label.setText(
            f"  Camera  dist={d:.1f}  elev={e:.0f}°  azim={a:.0f}°"
            f"  │  Scroll=zoom  Drag=rotate  Shift+Drag=pan"
        )
