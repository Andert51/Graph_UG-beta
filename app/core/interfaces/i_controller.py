"""IController — top-level contract for the application mediator."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IController(ABC):
    """Contract for the main application controller.

    The controller sits at the intersection of all layers:
    - It receives raw text input from the View.
    - It delegates computation to ``IEvaluator``.
    - It delegates rendering to ``IRenderer``.
    - It pushes textual results back to the View through PySide6 signals.

    The View and the math/render engines never call each other directly;
    all information flows through this mediator.
    """

    @abstractmethod
    def handle_input(self, source: str) -> None:
        """Process user-submitted *source* text end-to-end.

        Pipeline: text → evaluate → render plots (if any) → emit result/error.

        Parameters
        ----------
        source:
            Raw string received from the editor or terminal widget.
        """
        ...

    @abstractmethod
    def reset_session(self) -> None:
        """Reset all stateful components: evaluator scope, canvas, console."""
        ...
