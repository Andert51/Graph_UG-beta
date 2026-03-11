"""Expression — immutable value-object that represents a parsed statement."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class ExpressionKind(Enum):
    """Coarse classification of a parsed expression."""

    ASSIGNMENT = auto()
    ARITHMETIC = auto()
    FUNCTION_CALL = auto()
    PLOT_COMMAND = auto()
    COMMAND = auto()  # e.g. "clear", "reset"


@dataclass(frozen=True, slots=True)
class Expression:
    """Immutable value-object produced by the parser.

    Carries the original text, the coarse kind classification, and an
    opaque AST reference.  Downstream consumers (evaluator, renderer) work
    with ``MathResult`` and ``PlotCommand``; this type is produced by the
    lexing stage only.
    """

    kind: ExpressionKind
    raw: str
    ast: Any = field(default=None, compare=False)
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)
