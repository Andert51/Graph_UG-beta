"""Typed AST node definitions for the GraphUG mathematical language.

All nodes are plain ``@dataclass`` classes.  The ``line``/``column`` fields
carry source-location metadata injected by the Transformer so future tooling
(e.g. error highlighting) can pinpoint the offending token.

Node types mirror the grammar rules one-to-one — do not add business logic
here.  Evaluation logic lives exclusively in ``MathEvaluator``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


@dataclass
class ASTNode:
    """Structural base for all AST nodes."""

    line: int = field(default=0, compare=False, repr=False)
    column: int = field(default=0, compare=False, repr=False)


# ---------------------------------------------------------------------------
# Literal / leaf nodes
# ---------------------------------------------------------------------------


@dataclass
class NumberNode(ASTNode):
    """A numeric literal, always stored as ``float``."""

    value: float = 0.0


@dataclass
class SymbolNode(ASTNode):
    """A variable or built-in name reference."""

    name: str = ""


@dataclass
class StringNode(ASTNode):
    """A string literal, e.g. ``"x^2 + 1"``."""

    value: str = ""


# ---------------------------------------------------------------------------
# Operator nodes
# ---------------------------------------------------------------------------


@dataclass
class BinaryOpNode(ASTNode):
    """A binary infix operation: ``+``, ``-``, ``*``, ``/``, ``^``."""

    op: str = ""
    left: ASTNode = field(default_factory=ASTNode)
    right: ASTNode = field(default_factory=ASTNode)


@dataclass
class UnaryOpNode(ASTNode):
    """A unary prefix operation — currently only negation (``-``)."""

    op: str = "-"
    operand: ASTNode = field(default_factory=ASTNode)


# ---------------------------------------------------------------------------
# Compound nodes
# ---------------------------------------------------------------------------


@dataclass
class FuncCallNode(ASTNode):
    """A function call: ``name(arg1, arg2, …)``."""

    name: str = ""
    args: list[ASTNode] = field(default_factory=list)


@dataclass
class VectorNode(ASTNode):
    """A row-vector literal: ``[e1, e2, …]``."""

    elements: list[ASTNode] = field(default_factory=list)


@dataclass
class MatrixNode(ASTNode):
    """A matrix literal: ``[r1c1, r1c2; r2c1, r2c2]``."""

    rows: list[list[ASTNode]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Statement nodes
# ---------------------------------------------------------------------------


@dataclass
class AssignmentNode(ASTNode):
    """A variable assignment: ``name = expr``."""

    name: str = ""
    value: ASTNode = field(default_factory=ASTNode)
