"""OutputPanel — standalone output console panel for dockable layout.

A read-only ``QTextEdit`` that displays coloured results and errors,
designed to be used inside a ``QDockWidget``.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class OutputPanel(QWidget):
    """Read-only console for evaluation results and errors."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_output(self, text: str, *, is_error: bool = False) -> None:
        """Append a coloured line to the console."""
        color = "#f38ba8" if is_error else "#a6e3a1"
        safe = (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        self._output.append(
            f'<span style="color:{color};'
            f"white-space:pre;"
            f'font-family:\'Cascadia Code\',\'Fira Code\',monospace;">'
            f"{safe}</span>"
        )

    def clear_output(self) -> None:
        self._output.clear()

    def set_font_size(self, size: int) -> None:
        font = self._output.font()
        font.setPointSize(size)
        self._output.setFont(font)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        font = QFont("Cascadia Code", 13)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._output.setFont(font)
        self._output.document().setMaximumBlockCount(2000)
        layout.addWidget(self._output)
