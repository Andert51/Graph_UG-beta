"""Abstract contracts (interfaces) for all cross-layer communication."""

from app.core.interfaces.i_evaluator import IEvaluator
from app.core.interfaces.i_renderer import IRenderer
from app.core.interfaces.i_controller import IController

__all__ = ["IEvaluator", "IRenderer", "IController"]
