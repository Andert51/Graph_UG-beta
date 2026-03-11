"""Line-number gutter for the GraphUG code editor.

Displays line numbers in a thin gutter on the left side of a
``QPlainTextEdit``.  Follows the official Qt example, adapted for
Catppuccin Mocha palette.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPaintEvent, QTextBlock
from PySide6.QtWidgets import QCompleter, QPlainTextEdit, QWidget

from app.gui.widgets.completer import update_completions


class LineNumberArea(QWidget):
    """Thin gutter widget — paints line numbers for its parent editor."""

    def __init__(self, editor: QPlainTextEdit) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._editor.lineNumberAreaWidth(), 0)  # type: ignore[attr-defined]

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        self._editor.lineNumberAreaPaintEvent(event)  # type: ignore[attr-defined]


class LineNumberEditor(QPlainTextEdit):
    """QPlainTextEdit subclass with an integrated line-number gutter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self._completer: QCompleter | None = None
        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self._update_line_area_width()

    # -- Autocomplete integration --

    def set_completer(self, completer: QCompleter) -> None:
        """Attach an autocomplete completer to this editor."""
        self._completer = completer

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Process key events and update autocomplete popup."""
        if self._completer and self._completer.popup().isVisible():
            if event.key() in (
                Qt.Key.Key_Enter, Qt.Key.Key_Return,
                Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab,
            ):
                event.ignore()
                return

        super().keyPressEvent(event)

        if self._completer is not None:
            update_completions(self, self._completer)

    # -- Gutter width calculation --

    def lineNumberAreaWidth(self) -> int:  # noqa: N802
        digits = max(1, len(str(self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    # -- Respond to viewport changes --

    def _update_line_area_width(self) -> None:
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def _update_line_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width()

    def resizeEvent(self, event: object) -> None:  # noqa: N802
        super().resizeEvent(event)  # type: ignore[arg-type]
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    # -- Paint the gutter --

    def lineNumberAreaPaintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#181825"))

        block: QTextBlock = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        font = QFont(self.font())
        font.setPointSize(max(font.pointSize() - 1, 8))
        painter.setFont(font)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#585b70"))
                painter.drawText(
                    0, top,
                    self._line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

        painter.end()
