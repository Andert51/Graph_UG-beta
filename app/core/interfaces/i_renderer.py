"""IRenderer — contract for any component that draws onto a canvas."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.models.plot_command import PlotCommand


class IRenderer(ABC):
    """Contract that decouples the rendering engine from the rest of the app.

    The concrete implementation (e.g. ``PyQtGraphRenderer``) receives and
    owns the actual ``pg.PlotWidget``, but the controller and evaluator only
    ever see this interface.
    """

    @abstractmethod
    def render(self, command: PlotCommand) -> None:
        """Execute a single *command*, updating the visible canvas.

        Parameters
        ----------
        command:
            A fully structured ``PlotCommand`` DTO produced by the evaluator.

        Raises
        ------
        NotImplementedError
            If the renderer does not yet support the requested ``PlotKind``.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all drawn items from the canvas and reset the view state."""
        ...
