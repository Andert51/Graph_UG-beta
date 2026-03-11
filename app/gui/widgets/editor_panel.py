"""EditorPanel — script editor with embedded mini-output.

Responsibilities
----------------
* Provide a ``QPlainTextEdit`` code editor with ``Shift+Enter`` shortcut.
* Provide a small embedded ``QTextEdit`` output console (also shown in the
  separate Output dock, but kept here for quick inline feedback).
* Emit ``input_submitted(str)`` whenever the user requests evaluation.
* Expose ``append_output`` / ``clear_output`` so the Controller can push
  results back without the panel knowing anything about math.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.gui.widgets.completer import attach_completer
from app.gui.widgets.line_number_editor import LineNumberEditor
from app.gui.widgets.syntax_highlighter import GraphUGHighlighter


class EditorPanel(QWidget):
    """Composite widget: code editor (top) + toolbar + mini output (bottom)."""

    input_submitted: Signal = Signal(str)

    _MAX_HISTORY: int = 200

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._history: list[str] = []
        self._history_index: int = -1
        self._draft: str = ""
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_output(self, text: str, *, is_error: bool = False) -> None:
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

    def clear_editor(self) -> None:
        self._editor.clear()

    def set_font_size(self, size: int) -> None:
        font = self._editor.font()
        font.setPointSize(size)
        self._editor.setFont(font)
        font_out = self._output.font()
        font_out.setPointSize(size)
        self._output.setFont(font_out)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        mono = self._mono_font()

        # ── Code editor ──────────────────────────────────────────────
        self._editor = LineNumberEditor()
        self._editor.setFont(mono)
        self._editor.setPlaceholderText(
            "# GraphUG — Interactive Mathematical Environment\n"
            "# Shift+Enter or ▶ Run to evaluate\n\n"
            "# Quick start:\n"
            "x = linspace(0, 2*pi, 200)\n"
            'fplot("sin(x)")\n'
            'surface("sin(x)*cos(y)")\n'
            "help()"
        )
        self._editor.installEventFilter(self)
        self._highlighter = GraphUGHighlighter(self._editor.document())
        self._completer = attach_completer(self._editor)
        self._editor.set_completer(self._completer)
        root.addWidget(self._editor, stretch=7)

        # ── Run toolbar ───────────────────────────────────────────────
        root.addWidget(self._make_toolbar())

        # ── Inline mini output ────────────────────────────────────────
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(mono)
        self._output.setMaximumHeight(120)
        self._output.document().setMaximumBlockCount(500)
        self._output.setPlaceholderText("Output appears here…")
        root.addWidget(self._output, stretch=2)

    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(32)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)

        run_btn = QPushButton("▶  Run")
        run_btn.setToolTip("Evaluate (Shift+Enter)")
        run_btn.setFixedHeight(24)
        run_btn.clicked.connect(self._submit)
        layout.addWidget(run_btn)

        clear_btn = QPushButton("✕  Clear")
        clear_btn.setToolTip("Clear the editor")
        clear_btn.setFixedHeight(24)
        clear_btn.clicked.connect(self._editor.clear)
        layout.addWidget(clear_btn)

        layout.addStretch()
        return bar

    @staticmethod
    def _mono_font() -> QFont:
        font = QFont("Cascadia Code", 13)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    # ------------------------------------------------------------------
    # Event filter — Shift+Enter shortcut in the editor
    # ------------------------------------------------------------------

    def eventFilter(self, watched: object, event: object) -> bool:  # type: ignore[override]
        if (
            watched is self._editor
            and isinstance(event, QKeyEvent)
            and event.type() == QEvent.Type.KeyPress
        ):
            mods = event.modifiers()
            key = event.key()

            # Shift+Enter → evaluate
            if key == Qt.Key.Key_Return and (mods & Qt.KeyboardModifier.ShiftModifier):
                self._submit()
                return True

            # Ctrl+Up → navigate history backward
            if key == Qt.Key.Key_Up and (mods & Qt.KeyboardModifier.ControlModifier):
                self._history_back()
                return True

            # Ctrl+Down → navigate history forward
            if key == Qt.Key.Key_Down and (mods & Qt.KeyboardModifier.ControlModifier):
                self._history_forward()
                return True

        return super().eventFilter(watched, event)

    def _submit(self) -> None:
        text = self._editor.toPlainText().strip()
        if text:
            # Push to history (dedup consecutive duplicates)
            if not self._history or self._history[-1] != text:
                self._history.append(text)
                if len(self._history) > self._MAX_HISTORY:
                    self._history.pop(0)
            self._history_index = -1
            self._draft = ""
            self.input_submitted.emit(text)

    # ------------------------------------------------------------------
    # History navigation
    # ------------------------------------------------------------------

    def _history_back(self) -> None:
        """Replace editor content with the previous history entry (Ctrl+Up)."""
        if not self._history:
            return
        if self._history_index == -1:
            # Save current editor text as draft
            self._draft = self._editor.toPlainText()
            self._history_index = len(self._history) - 1
        elif self._history_index > 0:
            self._history_index -= 1
        else:
            return
        self._editor.setPlainText(self._history[self._history_index])

    def _history_forward(self) -> None:
        """Replace editor content with the next history entry (Ctrl+Down)."""
        if self._history_index == -1:
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self._editor.setPlainText(self._history[self._history_index])
        else:
            # Restore draft
            self._history_index = -1
            self._editor.setPlainText(self._draft)
