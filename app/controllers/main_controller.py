"""MainController — application mediator between View, Evaluator, and Renderer.

Signal topology
---------------
  View (EditorPanel.input_submitted: str)
      │
      ▼  @Slot
  MainController.handle_input(source: str)
      │
      ├─► IEvaluator.evaluate(source) ──► MathResult
      │       │
      │       ├─ MathResult.plot_commands ──► IRenderer.render(cmd) × N
      │       │
      │       └─ MathResult.output_text / .error
      │
      ├─► Signal result_ready(str)  ──► MainWindow.show_result(str)
      └─► Signal error_occurred(str) ──► MainWindow.show_error(str)

``MainController`` inherits both ``QObject`` (for PySide6 signals/slots) and
``IController`` (for the abstract contract).  ``QObject`` must come first in
the MRO.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.core.interfaces.i_controller import IController
from app.core.interfaces.i_evaluator import IEvaluator
from app.core.interfaces.i_renderer import IRenderer
from app.core.models.math_result import MathResult
from app.core.models.plot_command import PlotKind
from app.utils.logger import get_logger

_log = get_logger(__name__)


class MainController(QObject, IController):
    """Mediates the full evaluation pipeline via PySide6 signals."""

    result_ready: Signal = Signal(str)
    """Emitted with a human-readable result string on successful evaluation."""

    error_occurred: Signal = Signal(str)
    """Emitted with an error detail string when evaluation or rendering fails."""

    def __init__(
        self,
        evaluator: IEvaluator,
        renderer: IRenderer,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._evaluator: IEvaluator = evaluator
        self._renderer: IRenderer = renderer

    # ------------------------------------------------------------------
    # IController interface
    # ------------------------------------------------------------------

    @Slot(str)
    def handle_input(self, source: str) -> None:
        """Entry point wired to ``EditorPanel.input_submitted``.

        Performs: parse → evaluate → render (if applicable) → emit result.
        On any failure the error is forwarded to the View without crashing.
        """
        _log.debug("handle_input: %d chars", len(source))
        result: MathResult = self._evaluator.evaluate(source)

        if result.is_error:
            _log.warning("Evaluation error: %s", result.error)
            self.error_occurred.emit(result.error)  # type: ignore[arg-type]
            return

        # Auto-clear canvas before rendering new plots (unless hold mode)
        has_visual_plots = any(
            cmd.kind not in (PlotKind.CANVAS_CMD,)
            for cmd in result.plot_commands
        )
        if has_visual_plots and not self._evaluator.hold_mode:
            self._renderer.clear()

        for cmd in result.plot_commands:
            try:
                self._renderer.render(cmd)
            except NotImplementedError as exc:
                self.error_occurred.emit(f"RenderError: {exc}")
                return
            except Exception as exc:  # noqa: BLE001
                self.error_occurred.emit(f"RenderError (unexpected): {exc}")
                return

        self.result_ready.emit(result.output_text or "✓")

    def reset_session(self) -> None:
        """Reset evaluator scope and clear the canvas."""
        self._evaluator.reset_state()
        self._renderer.clear()
        self.result_ready.emit("Session reset.")

    def clear_canvas(self) -> None:
        """Clear only the canvas (renderer items), not the evaluator scope."""
        self._renderer.clear()
