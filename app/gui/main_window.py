"""MainWindow — the application shell (pure View layer).

Architectural contract
----------------------
* ``MainWindow`` never performs calculations.
* It never imports from ``parser``, ``math_engine``, or ``renderer``.
* It exposes a minimal public surface (properties + ``@Slot`` methods) that
  the controller uses to push results into the view.
* All inter-widget wiring happens here; individual widgets emit their own
  signals and are unaware of each other.

Layout (dockable panels)
------------------------
  ┌──────────────────────────────────────────────────────────┐
  │  QMenuBar   (File · Edit · View · Insert · Help)         │
  ├──────────────────────────────────────────────────────────┤
  │  QToolBar   (Run · Clear · Export · Snippets · Theme)    │
  ├──────────────────┬───────────────────────────────────────┤
  │  [Editor Dock]   │  Canvas (central widget)              │
  │  Script Editor   │  2-D / 3-D graph area                 │
  ├──────────────────┤                                       │
  │  [Output Dock]   │                                       │
  │  Console output  │                                       │
  ├──────────────────┴───────────────────────────────────────┤
  │  QStatusBar                                              │
  └──────────────────────────────────────────────────────────┘
  All side panels are QDockWidgets and can be dragged, floated, or hidden.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QStatusBar,
    QToolBar,
    QToolButton,
    QWidget,
)

from app.gui.dialogs.about_dialog import AboutDialog
from app.gui.dialogs.insert_calculus_dialog import InsertCalculusDialog
from app.gui.dialogs.insert_matrix_dialog import InsertMatrixDialog
from app.gui.dialogs.insert_plot_dialog import InsertPlotDialog
from app.gui.dialogs.insert_snippet_dialog import InsertSnippetDialog
from app.gui.dialogs.insert_vector_dialog import InsertVectorDialog
from app.gui.dialogs.settings_dialog import SettingsDialog
from app.gui.styles.theme_manager import ThemeManager, generate_stylesheet, CATPPUCCIN_MOCHA
from app.gui.widgets.canvas_panel import CanvasPanel
from app.gui.widgets.editor_panel import EditorPanel
from app.gui.widgets.output_panel import OutputPanel

# Application icon path
_ICON_PATH = Path(__file__).resolve().parents[2] / "assets" / "App_ico.ico"


class MainWindow(QMainWindow):
    """Top-level application window — pure View with dockable panels."""

    session_reset_requested: Signal = Signal()
    canvas_clear_requested: Signal = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GraphUG — Interactive Mathematical Environment")
        self.setMinimumSize(1100, 650)
        self.resize(1440, 840)

        # Theme manager
        self._theme = ThemeManager()
        self._font_size: int = 13

        # Set application icon
        if _ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(_ICON_PATH)))

        # Build UI components
        self._build_central_widget()
        self._build_dock_panels()
        self._build_toolbar()
        self._build_menus()
        self._build_status_bar()

        # Apply default theme
        self._theme.apply_theme("catppuccin_mocha", QApplication.instance())
        self._theme.add_listener(self._on_theme_palette_changed)

        # Enable dock nesting for flexible layouts
        self.setDockNestingEnabled(True)

    # ------------------------------------------------------------------
    # Public surface for the Controller
    # ------------------------------------------------------------------

    @property
    def editor_panel(self) -> EditorPanel:
        return self._editor

    @property
    def canvas_panel(self) -> CanvasPanel:
        return self._canvas

    @property
    def theme_manager(self) -> ThemeManager:
        return self._theme

    @Slot(str)
    def show_result(self, text: str) -> None:
        self._output.append_output(text, is_error=False)
        self._editor.append_output(text, is_error=False)
        self._status.showMessage(text[:120], 4_000)

    @Slot(str)
    def show_error(self, text: str) -> None:
        self._output.append_output(text, is_error=True)
        self._editor.append_output(text, is_error=True)
        self._status.showMessage(f"⚠  {text[:100]}", 6_000)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_central_widget(self) -> None:
        """The canvas is the permanent central widget."""
        self._canvas = CanvasPanel()
        self.setCentralWidget(self._canvas)

    def _build_dock_panels(self) -> None:
        """Create dockable editor and output panels."""
        # ── Editor dock ───────────────────────────────────────────────
        self._editor_dock = QDockWidget("Script Editor", self)
        self._editor_dock.setObjectName("editor_dock")
        self._editor_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self._editor = EditorPanel()
        self._editor_dock.setWidget(self._editor)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._editor_dock)

        # ── Output dock ───────────────────────────────────────────────
        self._output_dock = QDockWidget("Output Console", self)
        self._output_dock.setObjectName("output_dock")
        self._output_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self._output = OutputPanel()
        self._output_dock.setWidget(self._output)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._output_dock)

        # Stack output below editor in the left dock area
        self.splitDockWidget(self._editor_dock, self._output_dock, Qt.Orientation.Vertical)

        # Set initial sizes (editor larger than output)
        self.resizeDocks(
            [self._editor_dock, self._output_dock],
            [480, 200],
            Qt.Orientation.Vertical,
        )
        # Set left dock width
        self.resizeDocks(
            [self._editor_dock],
            [460],
            Qt.Orientation.Horizontal,
        )

    def _build_toolbar(self) -> None:
        """Create the main toolbar with common actions."""
        tb = QToolBar("Main Toolbar", self)
        tb.setObjectName("main_toolbar")
        tb.setMovable(False)
        tb.setIconSize(tb.iconSize())
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        # Run
        run_act = QAction("▶ Run", self)
        run_act.setShortcut(QKeySequence("Shift+Return"))
        run_act.setStatusTip("Evaluate the script (Shift+Enter)")
        run_act.triggered.connect(self._editor._submit)
        tb.addAction(run_act)

        tb.addSeparator()

        # Clear output
        clear_out_act = QAction("Clear Output", self)
        clear_out_act.setStatusTip("Clear the output console")
        clear_out_act.triggered.connect(self._clear_all_output)
        tb.addAction(clear_out_act)

        # Clear canvas
        clear_canvas_act = QAction("Clear Canvas", self)
        clear_canvas_act.setStatusTip("Clear the graph canvas")
        clear_canvas_act.triggered.connect(self._on_clear_canvas)
        tb.addAction(clear_canvas_act)

        tb.addSeparator()

        # Insert snippet
        snippet_act = QAction("Snippets", self)
        snippet_act.setStatusTip("Browse and insert code snippets")
        snippet_act.triggered.connect(self._on_insert_snippet)
        tb.addAction(snippet_act)

        # Insert plot
        plot_act = QAction("Plots", self)
        plot_act.setStatusTip("Insert a plot command")
        plot_act.triggered.connect(self._on_insert_plot)
        tb.addAction(plot_act)

        # Insert calculus
        calc_act = QAction("Calculus", self)
        calc_act.setStatusTip("Insert a calculus/algebra command")
        calc_act.triggered.connect(self._on_insert_calculus)
        tb.addAction(calc_act)

        tb.addSeparator()

        # Export
        export_act = QAction("Export PNG", self)
        export_act.setShortcut(QKeySequence("Ctrl+E"))
        export_act.setStatusTip("Export canvas as PNG")
        export_act.triggered.connect(self._on_export_canvas)
        tb.addAction(export_act)

        tb.addSeparator()

        # Settings
        settings_act = QAction("⚙ Settings", self)
        settings_act.setStatusTip("Theme and editor preferences")
        settings_act.triggered.connect(self._on_settings)
        tb.addAction(settings_act)

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

        export_act = QAction("&Export Canvas…", self)
        export_act.setShortcut(QKeySequence("Ctrl+E"))
        export_act.setStatusTip("Save the current canvas as a PNG image")
        export_act.triggered.connect(self._on_export_canvas)
        file_menu.addAction(export_act)

        file_menu.addSeparator()

        settings_act = QAction("&Settings…", self)
        settings_act.setShortcut(QKeySequence("Ctrl+,"))
        settings_act.triggered.connect(self._on_settings)
        file_menu.addAction(settings_act)

        file_menu.addSeparator()

        quit_act = QAction("&Quit", self)
        quit_act.setShortcut(QKeySequence.StandardKey.Quit)
        quit_act.triggered.connect(QApplication.quit)
        file_menu.addAction(quit_act)

        # ── Edit ──────────────────────────────────────────────────────
        edit_menu = mb.addMenu("&Edit")

        clear_out_act = QAction("Clear &Output", self)
        clear_out_act.setShortcut(QKeySequence("Ctrl+L"))
        clear_out_act.triggered.connect(self._clear_all_output)
        edit_menu.addAction(clear_out_act)

        clear_canvas_act = QAction("Clear &Canvas", self)
        clear_canvas_act.setShortcut(QKeySequence("Ctrl+Shift+L"))
        clear_canvas_act.triggered.connect(self._on_clear_canvas)
        edit_menu.addAction(clear_canvas_act)

        clear_editor_act = QAction("Clear &Editor", self)
        clear_editor_act.triggered.connect(self._editor.clear_editor)
        edit_menu.addAction(clear_editor_act)

        # ── View ──────────────────────────────────────────────────────
        view_menu = mb.addMenu("&View")

        view_menu.addAction(self._editor_dock.toggleViewAction())
        view_menu.addAction(self._output_dock.toggleViewAction())

        view_menu.addSeparator()

        reset_layout_act = QAction("Reset &Layout", self)
        reset_layout_act.setStatusTip("Restore the default panel layout")
        reset_layout_act.triggered.connect(self._reset_layout)
        view_menu.addAction(reset_layout_act)

        # ── Insert ────────────────────────────────────────────────────
        insert_menu = mb.addMenu("&Insert")

        plot_act = QAction("&Plot Command…", self)
        plot_act.setShortcut(QKeySequence("Ctrl+Shift+P"))
        plot_act.triggered.connect(self._on_insert_plot)
        insert_menu.addAction(plot_act)

        insert_menu.addSeparator()

        vector_act = QAction("&Vector…", self)
        vector_act.setShortcut(QKeySequence("Ctrl+Shift+V"))
        vector_act.triggered.connect(self._on_insert_vector)
        insert_menu.addAction(vector_act)

        matrix_act = QAction("&Matrix…", self)
        matrix_act.setShortcut(QKeySequence("Ctrl+Shift+M"))
        matrix_act.triggered.connect(self._on_insert_matrix)
        insert_menu.addAction(matrix_act)

        insert_menu.addSeparator()

        calculus_act = QAction("&Calculus / Algebra…", self)
        calculus_act.setShortcut(QKeySequence("Ctrl+Shift+C"))
        calculus_act.triggered.connect(self._on_insert_calculus)
        insert_menu.addAction(calculus_act)

        insert_menu.addSeparator()

        snippet_act = QAction("&Snippet…", self)
        snippet_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        snippet_act.triggered.connect(self._on_insert_snippet)
        insert_menu.addAction(snippet_act)

        # ── Help ──────────────────────────────────────────────────────
        help_menu = mb.addMenu("&Help")

        about_act = QAction("&About GraphUG", self)
        about_act.triggered.connect(self._on_about)
        help_menu.addAction(about_act)

    def _build_status_bar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage(
            "Ready  ·  GraphUG v0.7  ·  Shift+Enter to run  "
            "·  Drag panels to rearrange  ·  Ctrl+, for settings"
        )

    # ------------------------------------------------------------------
    # Theme handling
    # ------------------------------------------------------------------

    def _on_theme_palette_changed(self, palette: object) -> None:
        """Called by ThemeManager when the palette changes.

        Update non-QSS components (PyQtGraph canvas, syntax highlighter).
        """
        from app.gui.styles.theme_manager import Palette

        if not isinstance(palette, Palette):
            return
        # Update PyQtGraph canvas background and grid
        self._canvas.apply_palette(palette)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_new_session(self) -> None:
        self._clear_all_output()
        self._status.showMessage("Session cleared.", 3_000)
        self.session_reset_requested.emit()

    def _on_clear_canvas(self) -> None:
        self.canvas_clear_requested.emit()
        self._status.showMessage("Canvas cleared.", 3_000)

    def _clear_all_output(self) -> None:
        self._editor.clear_output()
        self._output.clear_output()

    def _on_insert_vector(self) -> None:
        dialog = InsertVectorDialog(self)
        if dialog.exec() == InsertVectorDialog.DialogCode.Accepted:
            self._editor.input_submitted.emit(dialog.command)

    def _on_insert_matrix(self) -> None:
        dialog = InsertMatrixDialog(self)
        if dialog.exec() == InsertMatrixDialog.DialogCode.Accepted:
            self._editor.input_submitted.emit(dialog.command)

    def _on_insert_plot(self) -> None:
        dialog = InsertPlotDialog(self)
        if dialog.exec() == InsertPlotDialog.DialogCode.Accepted and dialog.command:
            self._editor.input_submitted.emit(dialog.command)

    def _on_insert_calculus(self) -> None:
        dialog = InsertCalculusDialog(self)
        if dialog.exec() == InsertCalculusDialog.DialogCode.Accepted and dialog.command:
            self._editor.input_submitted.emit(dialog.command)

    def _on_insert_snippet(self) -> None:
        dialog = InsertSnippetDialog(self)
        if dialog.exec() == InsertSnippetDialog.DialogCode.Accepted and dialog.command:
            self._editor.input_submitted.emit(dialog.command)

    def _on_export_canvas(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Canvas",
            "graphug_plot.png",
            "PNG Images (*.png);;All Files (*)",
        )
        if path:
            import pyqtgraph.exporters as exporters

            exporter = exporters.ImageExporter(self._canvas.plot_widget.plotItem)
            exporter.export(path)
            self._status.showMessage(f"Canvas exported to {path}", 5_000)

    def _on_settings(self) -> None:
        dialog = SettingsDialog(self._theme, self._font_size, self)
        dialog.theme_changed.connect(
            lambda name: self._theme.apply_theme(name, QApplication.instance())
        )
        dialog.font_size_changed.connect(self._apply_font_size)
        dialog.exec()

    def _apply_font_size(self, size: int) -> None:
        self._font_size = size
        self._editor.set_font_size(size)
        self._output.set_font_size(size)

    def _on_about(self) -> None:
        AboutDialog(self).exec()

    def _reset_layout(self) -> None:
        """Restore the default panel arrangement."""
        self._editor_dock.setVisible(True)
        self._output_dock.setVisible(True)
        self._editor_dock.setFloating(False)
        self._output_dock.setFloating(False)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._editor_dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._output_dock)
        self.splitDockWidget(self._editor_dock, self._output_dock, Qt.Orientation.Vertical)
        self.resizeDocks(
            [self._editor_dock, self._output_dock],
            [480, 200],
            Qt.Orientation.Vertical,
        )
        self.resizeDocks([self._editor_dock], [460], Qt.Orientation.Horizontal)
        self._status.showMessage("Layout reset.", 3_000)

