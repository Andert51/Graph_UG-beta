"""CanvasPanel — right-side PyQtGraph canvas container.

Owns the layout and cosmetic framing of the plot area.  The raw
``pg.PlotWidget`` is accessible via the ``plot_widget`` property and is
injected into ``PyQtGraphRenderer`` at startup — so the renderer never
imports or constructs any Qt widget directly.
"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.gui.styles.pyqtgraph_config import apply_dark_background


class CanvasPanel(QWidget):
    """Thin wrapper around ``pg.PlotWidget`` that handles layout and theming."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def plot_widget(self) -> pg.PlotWidget:
        """The underlying ``pg.PlotWidget`` — inject into the renderer."""
        return self._plot_widget

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QLabel("  Canvas")
        header.setFixedHeight(26)
        header.setStyleSheet(
            "background:#181825; color:#a6adc8; font-size:10px;"
            "border-bottom:1px solid #313244; letter-spacing:1.2px;"
            "text-transform:uppercase; padding-left:4px;"
        )
        root.addWidget(header)

        self._plot_widget = pg.PlotWidget()
        apply_dark_background(self._plot_widget)
        root.addWidget(self._plot_widget)
