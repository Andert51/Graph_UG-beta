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
    DimensionError,
)
from app.core.interfaces.i_evaluator import IEvaluator
from app.core.models.math_result import MathResult
from app.core.models.plot_command import PlotCommand, PlotKind
from app.utils.logger import get_logger

_log = get_logger(__name__)
from app.math_engine.symbolic import (
    is_available as _sympy_available,
    simplify as _sym_simplify,
    factor as _sym_factor,
    expand as _sym_expand,
    diff as _sym_diff,
    integrate as _sym_integrate,
    solve as _sym_solve,
)
from app.parser.ast_nodes import (
    ASTNode,
    AssignmentNode,
    BinaryOpNode,
    FuncCallNode,
    MatrixNode,
    NumberNode,
    StringNode,
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
    def string(self, token: Any) -> StringNode:
        # Strip surrounding quotes (single or double)
        return StringNode(value=str(token)[1:-1])

    @v_args(inline=True)
    def symbol(self, token: Any) -> SymbolNode:
        return SymbolNode(name=str(token))

    # ── Arithmetic ────────────────────────────────────────────────────

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
    def mod(self, left: ASTNode, right: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="%", left=left, right=right)

    @v_args(inline=True)
    def pow(self, base: ASTNode, exp: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="^", left=base, right=exp)

    # ── Comparison ────────────────────────────────────────────────────

    @v_args(inline=True)
    def eq(self, l: ASTNode, r: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="==", left=l, right=r)

    @v_args(inline=True)
    def ne(self, l: ASTNode, r: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="!=", left=l, right=r)

    @v_args(inline=True)
    def lt(self, l: ASTNode, r: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="<", left=l, right=r)

    @v_args(inline=True)
    def gt(self, l: ASTNode, r: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op=">", left=l, right=r)

    @v_args(inline=True)
    def le(self, l: ASTNode, r: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="<=", left=l, right=r)

    @v_args(inline=True)
    def ge(self, l: ASTNode, r: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op=">=", left=l, right=r)

    # ── Unary ─────────────────────────────────────────────────────────

    @v_args(inline=True)
    def neg(self, operand: ASTNode) -> UnaryOpNode:
        return UnaryOpNode(op="-", operand=operand)

    @v_args(inline=True)
    def pos(self, operand: ASTNode) -> ASTNode:
        # Unary + is a no-op for numeric values
        return operand

    # ── Collections ───────────────────────────────────────────────────

    def arglist(self, items: list[ASTNode]) -> list[ASTNode]:
        return list(items)

    @v_args(inline=True)
    def func_call(self, name: Any, args: list[ASTNode]) -> FuncCallNode:
        return FuncCallNode(name=str(name), args=list(args))

    @v_args(inline=True)
    def func_call_expr(self, callee: ASTNode, args: list[ASTNode]) -> FuncCallNode:
        # handles chained calls like expr(args)
        if isinstance(callee, SymbolNode):
            return FuncCallNode(name=callee.name, args=list(args))
        return FuncCallNode(name="__call__", args=[callee, *args])

    def vector_literal(self, items: list[Any]) -> VectorNode:
        elements: list[ASTNode] = items[0] if items else []
        return VectorNode(elements=elements)

    def row(self, items: list[ASTNode]) -> list[ASTNode]:
        return list(items)

    def matrix_literal(self, rows: list[list[ASTNode]]) -> MatrixNode:
        return MatrixNode(rows=rows)

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
        "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
        # Transcendentals
        "sqrt": np.sqrt, "exp": np.exp,
        "log": np.log, "log2": np.log2, "log10": np.log10,
        "abs": np.abs,
        "ceil": np.ceil, "floor": np.floor, "round": np.round,
        # Array constructors — coerce float num to int for NumPy 2.x
        "linspace": lambda a, b, n=50: np.linspace(float(a), float(b), int(n)),
        "arange": np.arange,
        "zeros": lambda n: np.zeros(int(n)),
        "ones": lambda n: np.ones(int(n)),
        "eye": lambda n: np.eye(int(n)),
        # Linear algebra
        "dot": np.dot,
        "cross": np.cross,
        "norm": lambda v, o=None: float(np.linalg.norm(v, ord=o)),
        "det": np.linalg.det,
        "inv": np.linalg.inv,
        "transpose": lambda m: np.asarray(m).T,
        # Stats
        "sum": np.sum, "mean": np.mean,
        "min": np.min, "max": np.max,
        "std": np.std, "var": np.var,
        # Utility
        "len": lambda v: float(len(np.atleast_1d(v))),
        "reshape": lambda v, *s: np.asarray(v).reshape(tuple(int(x) for x in s)),
        # Constants
        "pi": math.pi,
        "e": math.e,
        "inf": math.inf,
        "nan": math.nan,
        "true": 1.0,
        "false": 0.0,
    }

    def __init__(self) -> None:
        grammar = _GRAMMAR_PATH.read_text(encoding="utf-8")
        self._parser: Lark = Lark(
            grammar,
            parser="lalr",
            transformer=_MathTransformer(),
        )
        self._scope: dict[str, Any] = dict(self._BUILTINS)
        _log.info("MathEvaluator initialised (grammar=%s)", _GRAMMAR_PATH.name)

    # ------------------------------------------------------------------
    # IEvaluator interface
    # ------------------------------------------------------------------

    @staticmethod
    def _split_statements(line: str) -> list[str]:
        """Split *line* on ``;`` while respecting ``[…]`` brackets.

        Semicolons inside brackets are part of matrix-literal syntax and
        must **not** be treated as statement separators.
        """
        parts: list[str] = []
        depth = 0
        start = 0
        for i, ch in enumerate(line):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            elif ch == ";" and depth == 0:
                parts.append(line[start:i])
                start = i + 1
        parts.append(line[start:])
        return parts

    def evaluate(self, source: str) -> MathResult:
        """Evaluate *source*, processing each non-blank, non-comment statement.

        Lines are split by newlines first, then by ``;`` (outside of
        brackets) to allow inline multi-statement input: ``a = 1; b = 2``.
        Semicolons inside ``[…]`` are left intact for matrix-literal syntax.
        """
        raw_lines = source.strip().splitlines()
        statements: list[str] = []
        for raw_line in raw_lines:
            for segment in self._split_statements(raw_line):
                stmt = segment.strip()
                if stmt and not stmt.startswith("#"):
                    statements.append(stmt)

        if not statements:
            return MathResult(output_text="")

        accumulated_plots: list[PlotCommand] = []
        output_parts: list[str] = []
        last_value: Any = None

        for line in statements:
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

            case StringNode():
                return MathResult(value=node.value, output_text=repr(node.value))

            case SymbolNode():
                return self._eval_symbol(node)

            case BinaryOpNode():
                return self._eval_binary(node)

            case UnaryOpNode():
                val = self._eval_node(node.operand).value
                result = -val if node.op == "-" else val
                return MathResult(value=result, output_text=repr(result))

            case FuncCallNode():
                return self._eval_func(node)

            case VectorNode():
                return self._eval_vector(node)

            case MatrixNode():
                return self._eval_matrix(node)

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
            case "%": val = lv % rv
            case "^": val = lv ** rv
            case "==": val = float(np.all(lv == rv))
            case "!=": val = float(np.all(lv != rv))
            case "<":  val = float(np.all(lv < rv))
            case ">":  val = float(np.all(lv > rv))
            case "<=": val = float(np.all(lv <= rv))
            case ">=": val = float(np.all(lv >= rv))
            case _: raise EvaluationError(f"Unknown operator: {node.op!r}")
        return MathResult(value=val, output_text=repr(val))

    def _eval_func(self, node: FuncCallNode) -> MathResult:
        # Built-in plot commands — handled separately to produce PlotCommand DTOs
        if node.name == "plot":
            return self._eval_plot_call(node)
        if node.name == "scatter":
            return self._eval_scatter_call(node)
        if node.name == "vector":
            return self._eval_vector_call(node)
        if node.name == "bar":
            return self._eval_bar_call(node)
        if node.name == "hist":
            return self._eval_hist_call(node)

        # Symbolic algebra commands — operate on string expressions
        if node.name in ("simplify", "factor", "expand", "diff", "integrate", "solve"):
            return self._eval_symbolic_call(node)

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

    def _eval_matrix(self, node: MatrixNode) -> MathResult:
        """Evaluate a matrix literal ``[1,2; 3,4]`` to a 2-D ``np.ndarray``."""
        rows: list[list[float]] = []
        col_count: int | None = None
        for row_nodes in node.rows:
            row_vals = [self._eval_node(e).value for e in row_nodes]
            if col_count is None:
                col_count = len(row_vals)
            elif len(row_vals) != col_count:
                raise DimensionError(
                    f"Matrix row length mismatch: expected {col_count}, got {len(row_vals)}"
                )
            rows.append(row_vals)
        val = np.array(rows, dtype=float)
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

    def _eval_scatter_call(self, node: FuncCallNode) -> MathResult:
        """Handle ``scatter(x, y)``."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 2:
            raise EvaluationError("scatter() requires 2 arguments: scatter(x, y)")
        x_data = np.atleast_1d(np.asarray(args[0].value, dtype=float))
        y_data = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        cmd = PlotCommand(
            kind=PlotKind.SCATTER,
            data={"x": x_data, "y": y_data},
        )
        return MathResult(plot_commands=[cmd], output_text="→ scatter rendered")

    def _eval_vector_call(self, node: FuncCallNode) -> MathResult:
        """Handle ``vector(dx, dy)`` and ``vector(x0, y0, dx, dy)``."""
        args = [self._eval_node(a).value for a in node.args]
        if len(args) == 2:
            x0, y0, dx, dy = 0.0, 0.0, float(args[0]), float(args[1])
        elif len(args) == 4:
            x0, y0, dx, dy = (float(a) for a in args)
        else:
            raise EvaluationError("vector() requires 2 or 4 arguments")
        cmd = PlotCommand(
            kind=PlotKind.VECTOR_2D,
            data={"x0": x0, "y0": y0, "dx": dx, "dy": dy},
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ vector ({dx}, {dy})")

    def _eval_bar_call(self, node: FuncCallNode) -> MathResult:
        """Handle ``bar(x, heights)`` and ``bar(heights)``."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) == 1:
            heights = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            x = np.arange(len(heights), dtype=float)
        elif len(args) == 2:
            x = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            heights = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        else:
            raise EvaluationError("bar() requires 1 or 2 arguments")
        cmd = PlotCommand(
            kind=PlotKind.BAR,
            data={"x": x, "height": heights, "width": 0.8},
        )
        return MathResult(plot_commands=[cmd], output_text="→ bar chart rendered")

    def _eval_hist_call(self, node: FuncCallNode) -> MathResult:
        """Handle ``hist(data)`` and ``hist(data, bins)``."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) == 1:
            values = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            bins = 20
        elif len(args) == 2:
            values = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            bins = int(args[1].value)
        else:
            raise EvaluationError("hist() requires 1 or 2 arguments")
        cmd = PlotCommand(
            kind=PlotKind.HISTOGRAM,
            data={"values": values, "bins": bins},
        )
        return MathResult(plot_commands=[cmd], output_text="→ histogram rendered")

    # ------------------------------------------------------------------
    # Symbolic algebra helpers
    # ------------------------------------------------------------------

    _SYMBOLIC_DISPATCH: dict[str, Any] = {
        "simplify": _sym_simplify,
        "factor": _sym_factor,
        "expand": _sym_expand,
        "diff": _sym_diff,
        "integrate": _sym_integrate,
        "solve": _sym_solve,
    }

    def _eval_symbolic_call(self, node: FuncCallNode) -> MathResult:
        """Handle ``simplify("expr")``, ``diff("expr", "var")``, ``integrate("expr", "var")``."""
        if not _sympy_available():
            raise EvaluationError(
                f"{node.name}() requires SymPy.  Run: pip install sympy"
            )
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                f'{node.name}() first argument must be a string, e.g. {node.name}("x^2")'
            )
        fn = self._SYMBOLIC_DISPATCH[node.name]
        result_str = fn(*args)
        return MathResult(value=result_str, output_text=result_str)
