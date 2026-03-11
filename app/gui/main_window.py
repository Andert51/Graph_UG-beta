"""MainWindow — the application shell (pure View layer).

Architectural contract
----------------------
* ``MainWindow`` never performs calculations.
* It never imports from ``parser``, ``math_engine``, or ``renderer``.
* It exposes a minimal public surface (properties + ``@Slot`` methods) that
  the controller uses to push results into the view.
* All inter-widget wiring happens here; individual widgets emit their own
  signals and are unaware of each other.

Layout
------
  ┌─────────────────────────────────────────────────────┐
  │  QMenuBar  (File · Edit · Insert)                   │
  ├────────────────────────┬────────────────────────────┤
  │  EditorPanel           │  CanvasPanel               │
  │  (editor + console)    │  (pg.PlotWidget)            │
  ├────────────────────────┴────────────────────────────┤
  │  QStatusBar                                         │
  └─────────────────────────────────────────────────────┘
  The central splitter is horizontal; the editor takes 2/5, canvas 3/5.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QStatusBar,
)

from app.gui.dialogs.insert_vector_dialog import InsertVectorDialog
from app.gui.styles.dark_theme import DARK_STYLESHEET
from app.gui.widgets.canvas_panel import CanvasPanel
from app.gui.widgets.editor_panel import EditorPanel


class MainWindow(QMainWindow):
    """Top-level application window — pure View."""

    session_reset_requested: Signal = Signal()
    """Emitted when the user triggers File → New Session.
    The controller connects to this to reset the evaluator scope.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GraphUG — Interactive Mathematical Environment")
        self.setMinimumSize(1100, 650)
        self.resize(1440, 840)

        self._build_central_widget()
        self._build_menus()
        self._build_status_bar()
        self.setStyleSheet(DARK_STYLESHEET)

    # ------------------------------------------------------------------
    # Public surface for the Controller
    # ------------------------------------------------------------------

    @property
    def editor_panel(self) -> EditorPanel:
        """The editor / console panel — connect its ``input_submitted`` signal."""
        return self._editor

    @property
    def canvas_panel(self) -> CanvasPanel:
        """The canvas panel — pass ``canvas_panel.plot_widget`` to the renderer."""
        return self._canvas

    @Slot(str)
    def show_result(self, text: str) -> None:
        """Push a successful result to the output console and status bar."""
        self._editor.append_output(text, is_error=False)
        self._status.showMessage(text[:120], 4_000)

    @Slot(str)
    def show_error(self, text: str) -> None:
        """Push an error message to the output console and status bar."""
        self._editor.append_output(text, is_error=True)
        self._status.showMessage(f"⚠  {text[:100]}", 6_000)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_central_widget(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)

        self._editor = EditorPanel()
        self._canvas = CanvasPanel()

        splitter.addWidget(self._editor)
        splitter.addWidget(self._canvas)
        splitter.setStretchFactor(0, 2)   # editor: 2 parts
        splitter.setStretchFactor(1, 3)   # canvas: 3 parts
        splitter.setSizes([440, 1000])

        self.setCentralWidget(splitter)

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # ── File ──────────────────────────────────────────────────────
        file_menu = mb.addMenu("&File")

        new_act = QAction("&New Session", self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.setStatusTip("Clear editor, output, and canvas")
        new_act.triggered.connect(self._on_new_session)
        file_menu.addAction(new_act)

        file_menu.addSeparator()

        quit_act = QAction("&Quit", self)
        quit_act.setShortcut(QKeySequence.StandardKey.Quit)
        quit_act.triggered.connect(QApplication.quit)
        file_menu.addAction(quit_act)

        # ── Edit ──────────────────────────────────────────────────────
        edit_menu = mb.addMenu("&Edit")

        clear_out_act = QAction("Clear &Output", self)
        clear_out_act.setShortcut(QKeySequence("Ctrl+L"))
        clear_out_act.triggered.connect(self._editor.clear_output)
        edit_menu.addAction(clear_out_act)

        clear_canvas_act = QAction("Clear &Canvas", self)
        clear_canvas_act.setShortcut(QKeySequence("Ctrl+Shift+L"))
        clear_canvas_act.triggered.connect(self._canvas.plot_widget.clear)
        edit_menu.addAction(clear_canvas_act)

        # ── Insert ────────────────────────────────────────────────────
        insert_menu = mb.addMenu("&Insert")

        vector_act = QAction("&Vector…", self)
        vector_act.setShortcut(QKeySequence("Ctrl+Shift+V"))
        vector_act.setStatusTip("Open the Insert Vector dialog")
        vector_act.triggered.connect(self._on_insert_vector)
        insert_menu.addAction(vector_act)

    def _build_status_bar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready  ·  GraphUG v0.1")

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_new_session(self) -> None:
        """Reset editor output and canvas, then signal the controller."""
        self._editor.clear_output()
        self._canvas.plot_widget.clear()
        self._status.showMessage("Session cleared.", 3_000)
        self.session_reset_requested.emit()

    def _on_insert_vector(self) -> None:
        """Open the vector dialog; on accept, submit the generated command."""
        dialog = InsertVectorDialog(self)
        if dialog.exec() == InsertVectorDialog.DialogCode.Accepted:
            self._editor.input_submitted.emit(dialog.command)
