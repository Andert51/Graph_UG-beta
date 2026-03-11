"""EditorPanel — left-side input and output panel.

Responsibilities
----------------
* Provide a ``QPlainTextEdit`` code editor with ``Shift+Enter`` shortcut.
* Provide a ``QTextEdit`` read-only output console with coloured HTML output.
* Emit ``input_submitted(str)`` whenever the user requests evaluation.
* Expose ``append_output`` / ``clear_output`` so the Controller can push
  results back without the panel knowing anything about math.

The panel is intentionally ignorant of how input is evaluated; it only
emits a raw text signal and waits for the controller to call back.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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

from app.gui.widgets.line_number_editor import LineNumberEditor
from app.gui.widgets.syntax_highlighter import GraphUGHighlighter


class EditorPanel(QWidget):
    """Composite widget: code editor (top) + toolbar + console output (bottom)."""

    input_submitted: Signal = Signal(str)
    """Emitted with the full editor text when the user triggers evaluation."""

    _MAX_HISTORY: int = 200

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._history: list[str] = []
        self._history_index: int = -1
        self._draft: str = ""
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API — consumed by the controller / main window
    # ------------------------------------------------------------------

    def append_output(self, text: str, *, is_error: bool = False) -> None:
        """Append a coloured line to the output console.

        Parameters
        ----------
        text:
            Plain-text result or error message.
        is_error:
            When ``True`` the text is rendered in red; otherwise in green.
        """
        color = "#f38ba8" if is_error else "#a6e3a1"
        # HTML-escape the content to prevent accidental tag injection
        safe = (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        self._output.append(
            f'<span style="color:{color};'
            f'font-family:\'Cascadia Code\',\'Fira Code\',monospace;">'
            f"{safe}</span>"
        )

    def clear_output(self) -> None:
        """Clear all content from the output console."""
        self._output.clear()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header("  Script Editor"))

        mono = self._mono_font()

        # ── Code editor ──────────────────────────────────────────────
        self._editor = LineNumberEditor()
        self._editor.setFont(mono)
        self._editor.setPlaceholderText(
            "# GraphUG mathematical environment\n"
            "# Shift+Enter or ▶ Run to evaluate\n\n"
            "x = linspace(0, 2*pi, 200)\n"
            "plot(x, sin(x))"
        )
        self._editor.installEventFilter(self)
        self._highlighter = GraphUGHighlighter(self._editor.document())
        root.addWidget(self._editor, stretch=6)

        # ── Run / Clear toolbar ───────────────────────────────────────
        root.addWidget(self._make_toolbar())

        # ── Console output ────────────────────────────────────────────
        root.addWidget(self._make_header("  Output"))
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(mono)
        self._output.document().setMaximumBlockCount(2000)
        root.addWidget(self._output, stretch=3)

    def _make_header(self, title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setFixedHeight(26)
        lbl.setStyleSheet(
            "background:#181825; color:#a6adc8; font-size:10px;"
            "border-bottom:1px solid #313244; letter-spacing:1.2px;"
            "text-transform:uppercase; padding-left:4px;"
        )
        return lbl

    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet("background:#181825; border-top:1px solid #313244;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        run_btn = QPushButton("▶  Run")
        run_btn.setToolTip("Evaluate (Shift+Enter)")
        run_btn.clicked.connect(self._submit)
        layout.addWidget(run_btn)

        clear_editor_btn = QPushButton("✕  Clear Editor")
        clear_editor_btn.clicked.connect(self._editor.clear)
        layout.addWidget(clear_editor_btn)

        clear_out_btn = QPushButton("✕  Clear Output")
        clear_out_btn.clicked.connect(self.clear_output)
        layout.addWidget(clear_out_btn)

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
        if watched is self._editor and isinstance(event, QKeyEvent):
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
