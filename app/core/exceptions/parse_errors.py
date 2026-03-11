"""GraphUG exception hierarchy.

All exceptions inherit from ``GraphUGError`` so that callers can either catch
the base class to swallow all domain errors, or catch a specific subclass for
precise handling.
"""

from __future__ import annotations


class GraphUGError(Exception):
    """Base exception for all application-level errors."""


# ---------------------------------------------------------------------------
# Parser errors
# ---------------------------------------------------------------------------


class ParseError(GraphUGError):
    """Raised when the Lark parser fails to tokenise or build a parse tree.

    Carries optional source-location information so the View can highlight
    the offending region in the editor.
    """

    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        super().__init__(message)
        self.line = line
        self.column = column

    def __str__(self) -> str:
        loc = f" (line {self.line}, col {self.column})" if self.line else ""
        return f"SyntaxError{loc}: {super().__str__()}"


# ---------------------------------------------------------------------------
# Evaluation errors
# ---------------------------------------------------------------------------


class EvaluationError(GraphUGError):
    """Raised when a syntactically valid expression cannot be evaluated.

    Examples include type mismatches, shape errors, or unsupported operations.
    """


class UndefinedSymbolError(EvaluationError):
    """Raised when an undeclared variable or function is referenced."""

    def __init__(self, symbol: str) -> None:
        super().__init__(f"Undefined symbol: '{symbol}'")
        self.symbol = symbol


class DimensionError(EvaluationError):
    """Raised on shape/dimension mismatches in matrix or vector operations."""
