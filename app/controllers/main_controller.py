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
      │       │   (2-D commands → _renderer, 3-D commands → _renderer_3d)
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

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from app.core.interfaces.i_controller import IController
from app.core.interfaces.i_evaluator import IEvaluator
from app.core.interfaces.i_renderer import IRenderer
from app.core.models.math_result import MathResult
from app.core.models.plot_command import PlotKind
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.gui.widgets.canvas_panel import CanvasPanel

_log = get_logger(__name__)

# PlotKinds that require the 3-D renderer
_3D_KINDS: frozenset[PlotKind] = frozenset({
    PlotKind.SURFACE_3D,
    PlotKind.WIREFRAME_3D,
    PlotKind.PARAMETRIC_3D,
    PlotKind.SCATTER_3D,
    PlotKind.SURFACE_PARAM_3D,
    PlotKind.BAR_3D,
})


class MainController(QObject, IController):
    """Mediates the full evaluation pipeline via PySide6 signals."""

    result_ready: Signal = Signal(str)
    error_occurred: Signal = Signal(str)

    canvas_mode_requested: Signal = Signal(str)
    """Emitted with ``"2d"`` or ``"3d"`` to auto-switch the canvas view."""

    def __init__(
        self,
        evaluator: IEvaluator,
        renderer: IRenderer,
        renderer_3d: IRenderer | None = None,
        canvas_panel: "CanvasPanel | None" = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._evaluator: IEvaluator = evaluator
        self._renderer: IRenderer = renderer
        self._renderer_3d: IRenderer | None = renderer_3d
        self._canvas_panel: "CanvasPanel | None" = canvas_panel

    # ------------------------------------------------------------------
    # IController interface
    # ------------------------------------------------------------------

    @Slot(str)
    def handle_input(self, source: str) -> None:
        _log.debug("handle_input: %d chars", len(source))
        result: MathResult = self._evaluator.evaluate(source)

        if result.is_error:
            _log.warning("Evaluation error: %s", result.error)
            self.error_occurred.emit(result.error)  # type: ignore[arg-type]
            return

        has_visual_2d = any(
            cmd.kind not in (PlotKind.CANVAS_CMD,) and cmd.kind not in _3D_KINDS
            for cmd in result.plot_commands
        )
        has_3d = any(cmd.kind in _3D_KINDS for cmd in result.plot_commands)

        # Auto-clear before new plots (unless hold mode)
        if (has_visual_2d or has_3d) and not self._evaluator.hold_mode:
            if has_visual_2d:
                self._renderer.clear()
            if has_3d and self._renderer_3d:
                self._renderer_3d.clear()

        # Auto-switch canvas mode
        if has_3d and self._canvas_panel:
            self._canvas_panel.set_mode("3d")
        elif has_visual_2d and self._canvas_panel:
            self._canvas_panel.set_mode("2d")

        for cmd in result.plot_commands:
            try:
                if cmd.kind in _3D_KINDS:
                    if self._renderer_3d is None:
                        self.error_occurred.emit("RenderError: 3-D renderer not available")
                        return
                    self._renderer_3d.render(cmd)
                else:
                    self._renderer.render(cmd)
            except NotImplementedError as exc:
                self.error_occurred.emit(f"RenderError: {exc}")
                return
            except Exception as exc:  # noqa: BLE001
                self.error_occurred.emit(f"RenderError (unexpected): {exc}")
                return

        self.result_ready.emit(result.output_text or "✓")

    def reset_session(self) -> None:
        self._evaluator.reset_state()
        self._renderer.clear()
        if self._renderer_3d:
            self._renderer_3d.clear()
        self.result_ready.emit("Session reset.")

    def clear_canvas(self) -> None:
        """Clear only the canvas (renderer items), not the evaluator scope."""
        self._renderer.clear()
        if self._renderer_3d:
            self._renderer_3d.clear()
