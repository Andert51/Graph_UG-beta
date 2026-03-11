"""MathEvaluator — concrete IEvaluator backed by Lark + NumPy.

Architecture notes
------------------
* ``_MathTransformer`` runs inline during LALR parsing (Lark
  ``transformer=`` parameter) and converts every parse-tree node directly
  into a typed ``ASTNode`` subclass.  No second pass is needed.
* ``MathEvaluator._eval_node`` uses Python 3.10 structural pattern matching
  to dispatch on the concrete node type without isinstance chains.
* The evaluator is stateful: variable assignments persist across ``evaluate``
  calls for the lifetime of one session.  ``reset_state()`` restores defaults.
* ``evaluate()`` processes the input line by line, skipping blank lines and
  comments (``#``), and aggregates all results.  It never raises; errors are
  captured in the returned ``MathResult.error`` field.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedInput

from app.core.exceptions.parse_errors import (
    GraphUGError,
    ParseError,
    EvaluationError,
    UndefinedSymbolError,
)
from app.core.interfaces.i_evaluator import IEvaluator
from app.core.models.math_result import MathResult
from app.core.models.plot_command import PlotCommand, PlotKind
from app.parser.ast_nodes import (
    ASTNode,
    AssignmentNode,
    BinaryOpNode,
    FuncCallNode,
    NumberNode,
    SymbolNode,
    UnaryOpNode,
    VectorNode,
)

_GRAMMAR_PATH = Path(__file__).parent / "grammar" / "math_grammar.lark"


# ---------------------------------------------------------------------------
# Lark Transformer — parse tree → typed AST nodes
# ---------------------------------------------------------------------------


class _MathTransformer(Transformer):
    """Converts Lark ``Tree`` / ``Token`` objects into typed ``ASTNode``s.

    All methods are called inline by the LALR parser at reduction time.
    """

    @v_args(inline=True)
    def number(self, token: Any) -> NumberNode:
        return NumberNode(value=float(token))

    @v_args(inline=True)
    def symbol(self, token: Any) -> SymbolNode:
        return SymbolNode(name=str(token))

    @v_args(inline=True)
    def add(self, left: ASTNode, right: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="+", left=left, right=right)

    @v_args(inline=True)
    def sub(self, left: ASTNode, right: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="-", left=left, right=right)

    @v_args(inline=True)
    def mul(self, left: ASTNode, right: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="*", left=left, right=right)

    @v_args(inline=True)
    def div(self, left: ASTNode, right: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="/", left=left, right=right)

    @v_args(inline=True)
    def pow(self, base: ASTNode, exp: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="^", left=base, right=exp)

    @v_args(inline=True)
    def neg(self, operand: ASTNode) -> UnaryOpNode:
        return UnaryOpNode(op="-", operand=operand)

    def arglist(self, items: list[ASTNode]) -> list[ASTNode]:
        return list(items)

    @v_args(inline=True)
    def func_call(self, name: Any, args: list[ASTNode]) -> FuncCallNode:
        return FuncCallNode(name=str(name), args=list(args))

    def vector_literal(self, items: list[Any]) -> VectorNode:
        elements: list[ASTNode] = items[0] if items else []
        return VectorNode(elements=elements)

    @v_args(inline=True)
    def assignment(self, name: Any, value: ASTNode) -> AssignmentNode:
        return AssignmentNode(name=str(name), value=value)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class MathEvaluator(IEvaluator):
    """Concrete ``IEvaluator``: Lark LALR → typed AST → evaluated ``MathResult``.

    The evaluator maintains a ``_scope`` dictionary for the current session.
    Built-in functions (NumPy trigonometry, ``linspace``, etc.) are pre-seeded
    into the scope and cannot be overwritten by user assignments.
    """

    # Built-in names available in the language without imports
    _BUILTINS: dict[str, Any] = {
        # Trigonometry
        "sin": np.sin, "cos": np.cos, "tan": np.tan,
        "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
        "atan2": np.arctan2,
        # Transcendentals
        "sqrt": np.sqrt, "exp": np.exp,
        "log": np.log, "log2": np.log2, "log10": np.log10,
        "abs": np.abs,
        # Array constructors — linspace/zeros/ones require integer size args;
        # wrap to coerce float literals from the parser (e.g. linspace(0,1,50))
        "linspace": lambda a, b, n=50: np.linspace(float(a), float(b), int(n)),
        "arange": np.arange,
        "zeros": lambda n: np.zeros(int(n)),
        "ones": lambda n: np.ones(int(n)),
        # Constants
        "pi": math.pi,
        "e": math.e,
        "inf": math.inf,
    }

    def __init__(self) -> None:
        grammar = _GRAMMAR_PATH.read_text(encoding="utf-8")
        self._parser: Lark = Lark(
            grammar,
            parser="lalr",
            transformer=_MathTransformer(),
        )
        self._scope: dict[str, Any] = dict(self._BUILTINS)

    # ------------------------------------------------------------------
    # IEvaluator interface
    # ------------------------------------------------------------------

    def evaluate(self, source: str) -> MathResult:
        """Evaluate *source*, processing each non-blank, non-comment line."""
        lines = [
            line.strip()
            for line in source.strip().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not lines:
            return MathResult(output_text="")

        accumulated_plots: list[PlotCommand] = []
        output_parts: list[str] = []
        last_value: Any = None

        for line in lines:
            try:
                ast = self._parser.parse(line)
            except UnexpectedInput as exc:
                return MathResult(error=str(ParseError(str(exc))))

            try:
                result = self._eval_node(ast)
            except GraphUGError as exc:
                return MathResult(error=str(exc))
            except ZeroDivisionError:
                return MathResult(error="EvaluationError: Division by zero")
            except Exception as exc:  # noqa: BLE001
                return MathResult(error=f"RuntimeError: {exc}")

            accumulated_plots.extend(result.plot_commands)
            if result.output_text:
                output_parts.append(result.output_text)
            last_value = result.value

        return MathResult(
            value=last_value,
            plot_commands=accumulated_plots,
            output_text="\n".join(output_parts),
        )

    def reset_state(self) -> None:
        """Restore the scope to factory defaults (built-ins only)."""
        self._scope = dict(self._BUILTINS)

    # ------------------------------------------------------------------
    # Private dispatch
    # ------------------------------------------------------------------

    def _eval_node(self, node: ASTNode) -> MathResult:  # noqa: PLR0911
        """Dispatch evaluation to the appropriate handler via structural matching."""
        match node:
            case NumberNode():
                return MathResult(value=node.value, output_text=str(node.value))

            case SymbolNode():
                return self._eval_symbol(node)

            case BinaryOpNode():
                return self._eval_binary(node)

            case UnaryOpNode():
                val = self._eval_node(node.operand).value
                result = -val
                return MathResult(value=result, output_text=repr(result))

            case FuncCallNode():
                return self._eval_func(node)

            case VectorNode():
                return self._eval_vector(node)

            case AssignmentNode():
                return self._eval_assignment(node)

            case _:
                raise EvaluationError(f"Unknown AST node type: {type(node).__name__}")

    def _eval_symbol(self, node: SymbolNode) -> MathResult:
        if node.name not in self._scope:
            raise UndefinedSymbolError(node.name)
        val = self._scope[node.name]
        return MathResult(value=val, output_text=repr(val))

    def _eval_binary(self, node: BinaryOpNode) -> MathResult:
        lv = self._eval_node(node.left).value
        rv = self._eval_node(node.right).value
        match node.op:
            case "+": val = lv + rv
            case "-": val = lv - rv
            case "*": val = lv * rv
            case "/": val = lv / rv
            case "^": val = lv ** rv
            case _: raise EvaluationError(f"Unknown operator: {node.op!r}")
        return MathResult(value=val, output_text=repr(val))

    def _eval_func(self, node: FuncCallNode) -> MathResult:
        # Built-in plot command — handled separately to produce PlotCommand DTOs
        if node.name == "plot":
            return self._eval_plot_call(node)

        if node.name not in self._scope:
            raise UndefinedSymbolError(node.name)
        fn = self._scope[node.name]
        if not callable(fn):
            raise EvaluationError(f"'{node.name}' is not callable")
        args = [self._eval_node(a).value for a in node.args]
        val = fn(*args)
        return MathResult(value=val, output_text=repr(val))

    def _eval_vector(self, node: VectorNode) -> MathResult:
        elements = [self._eval_node(e).value for e in node.elements]
        val = np.array(elements, dtype=float)
        return MathResult(value=val, output_text=repr(val))

    def _eval_assignment(self, node: AssignmentNode) -> MathResult:
        result = self._eval_node(node.value)
        if node.name in self._BUILTINS:
            raise EvaluationError(
                f"Cannot reassign built-in '{node.name}'"
            )
        self._scope[node.name] = result.value
        return MathResult(
            value=result.value,
            output_text=f"{node.name} = {result.output_text}",
        )

    def _eval_plot_call(self, node: FuncCallNode) -> MathResult:
        """Handle ``plot(y)`` and ``plot(x, y)`` calls."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) == 1:
            y_data = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            x_data = np.arange(len(y_data), dtype=float)
        elif len(args) == 2:
            x_data = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            y_data = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        else:
            raise EvaluationError("plot() requires 1 or 2 arguments")

        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": x_data, "y": y_data},
        )
        return MathResult(plot_commands=[cmd], output_text="→ plot rendered")
