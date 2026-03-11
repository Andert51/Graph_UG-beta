"""GraphUG — Application Entry Point.

Wires all layers together using explicit dependency injection.
No singletons; no global service locators.  The object graph is:

    MathEvaluator (parser + numpy)
        │
        ▼
    MainController ◄──── IEvaluator
        │            ◄──── IRenderer ◄── PyQtGraphRenderer
        │                                       │
        │                               pg.PlotWidget (owned by CanvasPanel)
        │
        ├── Signal result_ready  ──► MainWindow.show_result
        └── Signal error_occurred ──► MainWindow.show_error

    MainWindow.editor_panel.input_submitted ──► MainController.handle_input
    MainWindow._on_new_session ──────────────► MainController.reset_session
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable when run as ``python main.py``
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.utils.logger import get_logger

_log = get_logger(__name__)

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.controllers.main_controller import MainController
from app.gui.main_window import MainWindow
from app.gui.styles.pyqtgraph_config import configure_pyqtgraph
from app.parser.evaluator import MathEvaluator
from app.renderer.pyqtgraph_renderer import PyQtGraphRenderer


def _build_application() -> QApplication:
    """Initialise PyQtGraph options and construct the ``QApplication``."""
    configure_pyqtgraph()
    app = QApplication(sys.argv)
    app.setApplicationName("GraphUG")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("GraphUG Project")
    # Enable high-DPI scaling
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    return app


def _wire_dependencies(window: MainWindow) -> MainController:
    """Construct all service objects and connect signals/slots.

    Returns the controller so it stays alive for the application lifetime.
    """
    evaluator = MathEvaluator()
    renderer = PyQtGraphRenderer(window.canvas_panel.plot_widget)
    controller = MainController(evaluator, renderer)

    # View → Controller
    window.editor_panel.input_submitted.connect(controller.handle_input)

    # Controller → View
    controller.result_ready.connect(window.show_result)
    controller.error_occurred.connect(window.show_error)

    # "New Session" UI cleanup (canvas + output) → controller state reset
    window.session_reset_requested.connect(controller.reset_session)

    return controller


def main() -> None:
    """Application entry point."""
    _log.info("GraphUG starting…")
    app = _build_application()
    window = MainWindow()

    # Keep a reference so the controller (and its children) are not GC'd
    _controller = _wire_dependencies(window)  # noqa: F841

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
