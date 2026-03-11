"""IEvaluator — contract for any component that can parse and evaluate input."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.models.math_result import MathResult


class IEvaluator(ABC):
    """Contract that decouples the parser/evaluator from every other layer.

    Any concrete implementation (e.g. ``MathEvaluator`` using Lark, or a
    future ``SymPyEvaluator``) must fulfil this interface so that the
    controller never depends on implementation details.
    """

    @abstractmethod
    def evaluate(self, source: str) -> MathResult:
        """Parse and evaluate *source*, returning a structured result.

        The method must never raise; errors must be captured inside the
        returned ``MathResult.error`` field so the controller can forward
        them safely to the View.

        Parameters
        ----------
        source:
            Raw text submitted by the user (one or more lines).

        Returns
        -------
        MathResult
            Encapsulates the outcome: numeric value, plot commands, or an
            error message.
        """
        ...

    @abstractmethod
    def reset_state(self) -> None:
        """Clear all persistent state (variables, previous results) from the
        evaluator's session scope, restoring factory defaults."""
        ...
