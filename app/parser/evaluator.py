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
from app.math_engine.gpu_backend import (
    gpu_available as _gpu_available,
    gpu_fft, gpu_matmul, gpu_det, gpu_inv,
    gpu_eig, gpu_svd, gpu_solve, gpu_info,
)
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
    limit as _sym_limit,
    series as _sym_series,
    partial as _sym_partial,
    gradient_sym as _sym_gradient,
    divergence as _sym_divergence,
    curl as _sym_curl,
    laplacian as _sym_laplacian,
    laplace_transform as _sym_laplace,
    inv_laplace as _sym_inv_laplace,
    taylor as _sym_taylor,
    summation as _sym_summation,
    product_sym as _sym_product,
    definite_integral as _sym_defintegral,
    nsolve_eq as _sym_nsolve,
    rref as _sym_rref,
    nullspace as _sym_nullspace,
    colspace as _sym_colspace,
    lambdify_expr as _sym_lambdify,
    lambdify_expr_2d as _sym_lambdify_2d,
    diff_expr as _sym_diff_expr,
    tangent_at as _sym_tangent_at,
)
from app.parser.ast_nodes import (
    ASTNode,
    AssignmentNode,
    BinaryOpNode,
    FuncCallNode,
    IndexAccessNode,
    MatrixNode,
    NumberNode,
    PipeNode,
    StringNode,
    SymbolNode,
    TernaryNode,
    UnaryOpNode,
    VectorNode,
)

_GRAMMAR_PATH = Path(__file__).parent / "grammar" / "math_grammar.lark"


# ---------------------------------------------------------------------------
# Helper functions for special matrices
# ---------------------------------------------------------------------------

def _toeplitz(c: np.ndarray) -> np.ndarray:
    """Build a symmetric Toeplitz matrix from first column *c*."""
    c = np.asarray(c).ravel()
    n = len(c)
    result = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            result[i, j] = c[abs(i - j)]
    return result


def _companion(p: np.ndarray) -> np.ndarray:
    """Build companion matrix from polynomial coefficients *p*."""
    p = np.asarray(p).ravel()
    n = len(p) - 1
    if n < 1:
        return np.array([[]])
    c = np.zeros((n, n))
    c[0, :] = -p[1:] / p[0]
    c[np.arange(1, n), np.arange(0, n - 1)] = 1.0
    return c


def _block_diag(*blocks: np.ndarray) -> np.ndarray:
    """Build a block-diagonal matrix from *blocks*."""
    blocks = [np.atleast_2d(np.asarray(b)) for b in blocks]
    total_r = sum(b.shape[0] for b in blocks)
    total_c = sum(b.shape[1] for b in blocks)
    result = np.zeros((total_r, total_c))
    r, c = 0, 0
    for b in blocks:
        result[r:r + b.shape[0], c:c + b.shape[1]] = b
        r += b.shape[0]
        c += b.shape[1]
    return result


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

    # ── Logical ───────────────────────────────────────────────────────

    @v_args(inline=True)
    def logic_or(self, left: ASTNode, right: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="or", left=left, right=right)

    @v_args(inline=True)
    def logic_and(self, left: ASTNode, right: ASTNode) -> BinaryOpNode:
        return BinaryOpNode(op="and", left=left, right=right)

    @v_args(inline=True)
    def logic_not(self, operand: ASTNode) -> UnaryOpNode:
        return UnaryOpNode(op="not", operand=operand)

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

    @v_args(inline=True)
    def index_access(self, obj: ASTNode, index: ASTNode) -> IndexAccessNode:
        return IndexAccessNode(obj=obj, index=index)

    @v_args(inline=True)
    def ternary(self, cond: ASTNode, if_true: ASTNode, if_false: ASTNode) -> TernaryNode:
        return TernaryNode(condition=cond, if_true=if_true, if_false=if_false)

    @v_args(inline=True)
    def pipe(self, value: ASTNode, _pipe_op: Any, func_name: Any) -> PipeNode:
        return PipeNode(value=value, func_name=str(func_name))

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
        # ── Trigonometry ──────────────────────────────────────────────
        "sin": np.sin, "cos": np.cos, "tan": np.tan,
        "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
        "atan2": np.arctan2,
        "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
        "asinh": np.arcsinh, "acosh": np.arccosh, "atanh": np.arctanh,
        "sec": lambda x: 1.0 / np.cos(x),
        "csc": lambda x: 1.0 / np.sin(x),
        "cot": lambda x: np.cos(x) / np.sin(x),
        "sinc": np.sinc,
        "deg2rad": np.deg2rad, "rad2deg": np.rad2deg,

        # ── Transcendentals / elementary ──────────────────────────────
        "sqrt": np.sqrt, "cbrt": np.cbrt,
        "exp": np.exp, "exp2": np.exp2, "expm1": np.expm1,
        "log": np.log, "log2": np.log2, "log10": np.log10, "log1p": np.log1p,
        "abs": np.abs, "sign": np.sign,
        "ceil": np.ceil, "floor": np.floor, "round": np.round,
        "clip": lambda v, lo, hi: np.clip(v, float(lo), float(hi)),
        "mod": np.mod,
        "gcd": lambda a, b: float(math.gcd(int(a), int(b))),
        "lcm": lambda a, b: float(math.lcm(int(a), int(b))),
        "factorial": lambda n: float(math.factorial(int(n))),
        "comb": lambda n, k: float(math.comb(int(n), int(k))),
        "perm": lambda n, k=None: float(math.perm(int(n), int(k) if k is not None else None)),
        "hypot": np.hypot,

        # ── Array constructors ────────────────────────────────────────
        "linspace": lambda a, b, n=50: np.linspace(float(a), float(b), int(n)),
        "arange": np.arange,
        "zeros": lambda *s: np.zeros(tuple(int(x) for x in s)) if len(s) > 1 else np.zeros(int(s[0])),
        "ones": lambda *s: np.ones(tuple(int(x) for x in s)) if len(s) > 1 else np.ones(int(s[0])),
        "eye": lambda n: np.eye(int(n)),
        "diag": lambda v, k=0: np.diag(np.asarray(v), int(k)),
        "full": lambda n, val: np.full(int(n), float(val)),
        "rand": lambda *s: np.random.rand(*(int(x) for x in s)) if s else np.random.rand(),
        "randn": lambda *s: np.random.randn(*(int(x) for x in s)) if s else np.random.randn(),
        "randint": lambda lo, hi, n=1: np.random.randint(int(lo), int(hi), int(n)).astype(float),
        "logspace": lambda a, b, n=50: np.logspace(float(a), float(b), int(n)),
        "meshgrid": lambda x, y: np.meshgrid(np.asarray(x), np.asarray(y)),
        "flatten": lambda v: np.asarray(v).flatten(),
        "sort": lambda v: np.sort(np.asarray(v)),
        "unique": lambda v: np.unique(np.asarray(v)),
        "reverse": lambda v: np.asarray(v)[::-1].copy(),
        "concat": lambda a, b: np.concatenate([np.atleast_1d(a), np.atleast_1d(b)]),
        "stack": lambda a, b: np.stack([np.asarray(a), np.asarray(b)]),
        "tile": lambda v, n: np.tile(np.asarray(v), int(n)),
        "repeat": lambda v, n: np.repeat(np.asarray(v), int(n)),

        # ── Linear algebra ────────────────────────────────────────────
        "dot": np.dot,
        "cross": np.cross,
        "norm": lambda v, o=None: float(np.linalg.norm(v, ord=o)),
        "det": lambda m: gpu_det(np.asarray(m)),
        "inv": lambda m: gpu_inv(np.asarray(m)),
        "transpose": lambda m: np.asarray(m).T,
        "trace": lambda m: float(np.trace(np.asarray(m))),
        "rank": lambda m: float(np.linalg.matrix_rank(np.asarray(m))),
        "eig": lambda m: gpu_eig(np.asarray(m)),
        "eigvals": lambda m: gpu_eig(np.asarray(m)),
        "svd": lambda m: gpu_svd(np.asarray(m)),
        "pinv": lambda m: np.linalg.pinv(np.asarray(m)),
        "solve_linear": lambda A, b: gpu_solve(np.asarray(A), np.asarray(b)),
        "lu": lambda m: np.linalg.qr(np.asarray(m))[0],
        "qr": lambda m: np.linalg.qr(np.asarray(m)),
        "cholesky": lambda m: np.linalg.cholesky(np.asarray(m)),
        "cond": lambda m: float(np.linalg.cond(np.asarray(m))),
        "outer": lambda a, b: np.outer(np.asarray(a), np.asarray(b)),
        "inner": lambda a, b: float(np.inner(np.asarray(a), np.asarray(b))),
        "kron": lambda a, b: np.kron(np.asarray(a), np.asarray(b)),
        "matmul": lambda a, b: gpu_matmul(np.asarray(a), np.asarray(b)),

        # ── Statistics & reduction ────────────────────────────────────
        "sum": np.sum, "mean": np.mean,
        "min": np.min, "max": np.max,
        "std": np.std, "var": np.var,
        "median": lambda v: float(np.median(np.asarray(v))),
        "percentile": lambda v, p: float(np.percentile(np.asarray(v), float(p))),
        "cumsum": lambda v: np.cumsum(np.asarray(v)),
        "cumprod": lambda v: np.cumprod(np.asarray(v)),
        "prod": lambda v: float(np.prod(np.asarray(v))),
        "argmin": lambda v: float(np.argmin(np.asarray(v))),
        "argmax": lambda v: float(np.argmax(np.asarray(v))),
        "histogram": lambda v, bins=20: np.histogram(np.asarray(v), int(bins))[0].astype(float),
        "corrcoef": lambda x, y: np.corrcoef(np.asarray(x), np.asarray(y)),
        "cov": lambda x, y: np.cov(np.asarray(x), np.asarray(y)),

        # ── Utility ───────────────────────────────────────────────────
        "len": lambda v: float(len(np.atleast_1d(v))),
        "reshape": lambda v, *s: np.asarray(v).reshape(tuple(int(x) for x in s)),
        "where": lambda cond, x, y: np.where(np.asarray(cond, dtype=bool), x, y),
        "interp": lambda xp, x, y: np.interp(np.asarray(xp), np.asarray(x), np.asarray(y)),
        "gradient": lambda v: np.gradient(np.asarray(v, dtype=float)),
        "diff_array": lambda v: np.diff(np.asarray(v, dtype=float)),
        "trapz": lambda y, x=None: float(np.trapezoid(np.asarray(y, dtype=float), np.asarray(x, dtype=float) if x is not None else None)),
        "polyfit": lambda x, y, deg: np.polyfit(np.asarray(x), np.asarray(y), int(deg)),
        "polyval": lambda p, x: np.polyval(np.asarray(p), np.asarray(x)),
        "roots": lambda p: np.roots(np.asarray(p)),
        "convolve": lambda a, b: np.convolve(np.asarray(a), np.asarray(b)),
        "fft": lambda v: gpu_fft(np.asarray(v, dtype=float)),
        "ifft": lambda v: np.real(np.fft.ifft(np.asarray(v, dtype=complex))),
        "fftfreq": lambda n, d=1.0: np.fft.fftfreq(int(n), float(d)),

        # ── Vector calculus helpers (numeric) ─────────────────────────
        "magnitude": lambda v: float(np.linalg.norm(np.asarray(v))),
        "normalize": lambda v: np.asarray(v, dtype=float) / np.linalg.norm(np.asarray(v)),
        "angle": lambda v: float(np.arctan2(np.asarray(v)[1], np.asarray(v)[0])) if np.asarray(v).ndim == 1 else np.arctan2(np.asarray(v), 1.0),
        "proj": lambda u, v: (np.dot(u, v) / np.dot(v, v)) * np.asarray(v, dtype=float),
        "reject": lambda u, v: np.asarray(u, dtype=float) - (np.dot(u, v) / np.dot(v, v)) * np.asarray(v, dtype=float),

        # ── Constants ─────────────────────────────────────────────────
        "pi": math.pi,
        "e": math.e,
        "inf": math.inf,
        "nan": math.nan,
        "true": 1.0,
        "false": 0.0,
        "phi": (1 + math.sqrt(5)) / 2,              # golden ratio
        "tau": 2 * math.pi,
        "euler_gamma": 0.5772156649015329,           # Euler–Mascheroni

        # ── Type / introspection ──────────────────────────────────────
        "typeof": lambda v: type(v).__name__,
        "size": lambda v: np.asarray(v).shape,
        "ndim": lambda v: float(np.asarray(v).ndim),
        "isnan": lambda v: float(np.any(np.isnan(np.asarray(v, dtype=float)))),
        "isinf": lambda v: float(np.any(np.isinf(np.asarray(v, dtype=float)))),

        # ── Complex number support ────────────────────────────────────
        "complex": lambda r, i=0: complex(float(r), float(i)),
        "real": lambda z: np.real(np.asarray(z)),
        "imag": lambda z: np.imag(np.asarray(z)),
        "conj": lambda z: np.conj(np.asarray(z)),
        "phase": lambda z: np.angle(np.asarray(z)),
        "abs_complex": lambda z: np.abs(np.asarray(z)),

        # ── Special matrices ──────────────────────────────────────────
        "vander": lambda v, n=None: np.vander(np.asarray(v), N=int(n) if n else None),
        "toeplitz": lambda c: _toeplitz(np.asarray(c)),
        "hilbert": lambda n: np.array([[1.0 / (i + j + 1) for j in range(int(n))] for i in range(int(n))]),
        "companion": lambda p: np.array(_companion(np.asarray(p))),
        "triu": lambda m, k=0: np.triu(np.asarray(m), int(k)),
        "tril": lambda m, k=0: np.tril(np.asarray(m), int(k)),
        "block_diag": lambda *blocks: _block_diag(*blocks),

        # ── Extended signal processing ────────────────────────────────
        "fftshift": lambda v: np.fft.fftshift(np.asarray(v)),
        "rfft": lambda v: np.abs(np.fft.rfft(np.asarray(v, dtype=float))),
        "fft2": lambda m: np.abs(np.fft.fft2(np.asarray(m, dtype=float))),
        "hamming": lambda n: np.hamming(int(n)),
        "hanning": lambda n: np.hanning(int(n)),
        "blackman": lambda n: np.blackman(int(n)),
        "kaiser": lambda n, beta=14: np.kaiser(int(n), float(beta)),

        # ── Set operations ────────────────────────────────────────────
        "union": lambda a, b: np.union1d(np.asarray(a), np.asarray(b)),
        "intersect": lambda a, b: np.intersect1d(np.asarray(a), np.asarray(b)),
        "setdiff": lambda a, b: np.setdiff1d(np.asarray(a), np.asarray(b)),
        "in1d": lambda a, b: np.in1d(np.asarray(a), np.asarray(b)).astype(float),

        # ── Cumulative / running ──────────────────────────────────────
        "cummax": lambda v: np.maximum.accumulate(np.asarray(v)),
        "cummin": lambda v: np.minimum.accumulate(np.asarray(v)),
        "movmean": lambda v, w: np.convolve(np.asarray(v, dtype=float), np.ones(int(w)) / int(w), mode="valid"),

        # ── Bitwise / integer ─────────────────────────────────────────
        "bitand": lambda a, b: float(int(a) & int(b)),
        "bitor": lambda a, b: float(int(a) | int(b)),
        "bitxor": lambda a, b: float(int(a) ^ int(b)),
        "bitnot": lambda a: float(~int(a)),
        "shl": lambda a, n: float(int(a) << int(n)),
        "shr": lambda a, n: float(int(a) >> int(n)),

        # ── Functional / mapping helpers ──────────────────────────────
        "map_arr": lambda fn_name, arr: np.vectorize(fn_name)(np.asarray(arr)),
        "linreg": lambda x, y: np.polyfit(np.asarray(x, dtype=float), np.asarray(y, dtype=float), 1),
        "spline_interp": lambda xp, x, y: np.interp(np.asarray(xp), np.asarray(x), np.asarray(y)),
    }

    def __init__(self) -> None:
        grammar = _GRAMMAR_PATH.read_text(encoding="utf-8")
        self._parser: Lark = Lark(
            grammar,
            parser="lalr",
            transformer=_MathTransformer(),
        )
        self._scope: dict[str, Any] = dict(self._BUILTINS)
        self._hold_mode: bool = False
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

        for idx, line in enumerate(statements, 1):
            try:
                ast = self._parser.parse(line)
            except UnexpectedInput as exc:
                msg = str(ParseError(str(exc)))
                return MathResult(error=f"[Statement {idx}] {msg}\n  → \"{line}\"")

            try:
                result = self._eval_node(ast)
            except GraphUGError as exc:
                return MathResult(error=f"[Statement {idx}] {exc}\n  → \"{line}\"")
            except ZeroDivisionError:
                return MathResult(
                    error=f"[Statement {idx}] EvaluationError: Division by zero\n"
                    f"  → \"{line}\"\n"
                    f"  Hint: The denominator evaluates to zero. Check your expression."
                )
            except Exception as exc:  # noqa: BLE001
                return MathResult(error=f"[Statement {idx}] RuntimeError: {exc}\n  → \"{line}\"")

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
        self._hold_mode = False

    @property
    def hold_mode(self) -> bool:
        """Whether the evaluator is in hold mode (overlay plots)."""
        return self._hold_mode

    # ------------------------------------------------------------------
    # Pretty-print helper
    # ------------------------------------------------------------------

    @staticmethod
    def _format_value(val: Any) -> str:
        """Return a human-friendly string for *val* with beautiful formatting."""
        if isinstance(val, np.ndarray):
            if val.ndim == 1:
                return MathEvaluator._fmt_vector(val)
            if val.ndim == 2:
                return MathEvaluator._fmt_matrix(val)
            return repr(val)
        if isinstance(val, (list, tuple)):
            # Tuple of arrays (e.g. from qr, eig)
            if all(isinstance(v, np.ndarray) for v in val):
                parts = []
                for i, v in enumerate(val):
                    label = f"  Component {i + 1}:"
                    if v.ndim == 1:
                        parts.append(f"{label}\n{MathEvaluator._fmt_vector(v)}")
                    elif v.ndim == 2:
                        parts.append(f"{label}\n{MathEvaluator._fmt_matrix(v)}")
                    else:
                        parts.append(f"{label} {repr(v)}")
                return "\n".join(parts)
            if isinstance(val, tuple):
                return " × ".join(str(int(d)) for d in val)
            return repr(val)
        if isinstance(val, complex):
            r, i = val.real, val.imag
            if r == 0:
                return f"{i:g}i"
            sign = "+" if i >= 0 else "-"
            return f"{r:g} {sign} {abs(i):g}i"
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return f"{val:g}"
            if val == int(val):
                return str(int(val))
            return f"{val:g}"
        if isinstance(val, str):
            return val
        return repr(val)

    @staticmethod
    def _fmt_vector(v: np.ndarray) -> str:
        """Format a 1-D array with clean presentation."""
        n = len(v)
        if n == 0:
            return "[ ]  (empty)"
        # Check for complex
        if np.iscomplexobj(v):
            def _fc(z):
                if z.imag == 0:
                    return f"{z.real:g}"
                sign = "+" if z.imag >= 0 else "-"
                return f"{z.real:g}{sign}{abs(z.imag):g}i"
            if n <= 10:
                elems = "  ".join(_fc(x) for x in v)
                return f"[ {elems} ]"
            first = "  ".join(_fc(x) for x in v[:5])
            last = "  ".join(_fc(x) for x in v[-3:])
            return f"[ {first}  …  {last} ]  ({n} elements)"
        if n <= 10:
            elems = "  ".join(f"{x:g}" for x in v)
            return f"[ {elems} ]"
        if n <= 20:
            elems = "  ".join(f"{x:g}" for x in v)
            return f"[ {elems} ]  ({n} elements)"
        first = "  ".join(f"{x:g}" for x in v[:8])
        last = "  ".join(f"{x:g}" for x in v[-3:])
        return f"[ {first}  …  {last} ]  ({n} elements)"

    @staticmethod
    def _fmt_matrix(m: np.ndarray) -> str:
        """Format a 2-D array with aligned columns and Unicode brackets."""
        rows, cols = m.shape
        max_show_r, max_show_c = 12, 10  # truncation limits
        show_r = min(rows, max_show_r)
        show_c = min(cols, max_show_c)
        trunc_r = rows > max_show_r
        trunc_c = cols > max_show_c

        # Format visible cells
        cells = []
        for i in range(show_r):
            row_cells = [f"{m[i, j]:g}" for j in range(show_c)]
            if trunc_c:
                row_cells.append("…")
            cells.append(row_cells)

        # Column widths
        n_disp_cols = show_c + (1 if trunc_c else 0)
        widths = [
            max(len(cells[i][j]) for i in range(show_r))
            for j in range(n_disp_cols)
        ]

        # Build formatted rows
        lines: list[str] = []
        header = f"  [{rows}×{cols}]"
        inner_w = sum(widths) + 2 * (n_disp_cols - 1) + 2
        lines.append(f"{'':4}┌{'':^{inner_w}}┐")
        for i in range(show_r):
            parts = "  ".join(f"{cells[i][j]:>{widths[j]}}" for j in range(n_disp_cols))
            lines.append(f"{'':4}│ {parts} │")
        if trunc_r:
            lines.append(f"{'':4}│ {'⋮':^{inner_w - 2}} │")
        lines.append(f"{'':4}└{'':^{inner_w}}┘")
        return header + "\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # Private dispatch
    # ------------------------------------------------------------------

    def _eval_node(self, node: ASTNode) -> MathResult:  # noqa: PLR0911
        """Dispatch evaluation to the appropriate handler via structural matching."""
        match node:
            case NumberNode():
                return MathResult(value=node.value, output_text=self._format_value(node.value))

            case StringNode():
                return MathResult(value=node.value, output_text=self._format_value(node.value))

            case SymbolNode():
                return self._eval_symbol(node)

            case BinaryOpNode():
                return self._eval_binary(node)

            case UnaryOpNode():
                val = self._eval_node(node.operand).value
                if node.op == "not":
                    result = float(not val) if np.isscalar(val) else (~np.asarray(val, dtype=bool)).astype(float)
                elif node.op == "-":
                    result = -val
                else:
                    result = val
                return MathResult(value=result, output_text=self._format_value(result))

            case FuncCallNode():
                return self._eval_func(node)

            case VectorNode():
                return self._eval_vector(node)

            case MatrixNode():
                return self._eval_matrix(node)

            case AssignmentNode():
                return self._eval_assignment(node)

            case IndexAccessNode():
                return self._eval_index_access(node)

            case TernaryNode():
                return self._eval_ternary(node)

            case PipeNode():
                return self._eval_pipe(node)

            case _:
                raise EvaluationError(f"Unknown AST node type: {type(node).__name__}")

    def _eval_symbol(self, node: SymbolNode) -> MathResult:
        if node.name not in self._scope:
            raise UndefinedSymbolError(node.name)
        val = self._scope[node.name]
        return MathResult(value=val, output_text=self._format_value(val))

    def _eval_binary(self, node: BinaryOpNode) -> MathResult:
        lv = self._eval_node(node.left).value
        rv = self._eval_node(node.right).value
        match node.op:
            case "+":
                # String concatenation: "hello" + " world"
                if isinstance(lv, str) or isinstance(rv, str):
                    val = str(lv) + str(rv)
                else:
                    val = lv + rv
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
            case "and": val = float(bool(lv) and bool(rv))
            case "or":  val = float(bool(lv) or bool(rv))
            case _: raise EvaluationError(f"Unknown operator: {node.op!r}")
        return MathResult(value=val, output_text=self._format_value(val))

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

        # ── Phase 4: Advanced graphing commands ───────────────────────
        if node.name == "fplot":
            return self._eval_fplot_call(node)
        if node.name == "polar":
            return self._eval_polar_call(node)
        if node.name == "parametric":
            return self._eval_parametric_call(node)
        if node.name == "parametric3d":
            return self._eval_parametric3d_call(node)
        if node.name == "surface":
            return self._eval_surface_call(node)
        if node.name == "wireframe":
            return self._eval_wireframe_call(node)
        if node.name == "plotderiv":
            return self._eval_plotderiv_call(node)
        if node.name == "plotintegral":
            return self._eval_plotintegral_call(node)
        if node.name == "tangentline":
            return self._eval_tangentline_call(node)
        if node.name == "implicit":
            return self._eval_implicit_call(node)
        if node.name == "contour":
            return self._eval_contour_call(node)
        if node.name == "slopefield":
            return self._eval_slopefield_call(node)
        if node.name == "heatmap":
            return self._eval_heatmap_call(node)
        if node.name == "vectorfield":
            return self._eval_vectorfield_call(node)
        if node.name == "stem":
            return self._eval_stem_call(node)
        if node.name == "step":
            return self._eval_step_call(node)
        if node.name == "pie":
            return self._eval_pie_call(node)
        if node.name == "errorbar":
            return self._eval_errorbar_call(node)
        if node.name == "scatter3d":
            return self._eval_scatter3d_call(node)
        if node.name == "surfparam":
            return self._eval_surfparam_call(node)
        if node.name == "bar3d":
            return self._eval_bar3d_call(node)
        if node.name == "logplot":
            return self._eval_logplot_call(node)
        if node.name == "semilogx":
            return self._eval_semilogx_call(node)
        if node.name == "semilogy":
            return self._eval_semilogy_call(node)
        if node.name == "area":
            return self._eval_area_call(node)

        # Symbolic algebra commands — operate on string expressions
        if node.name in self._SYMBOLIC_DISPATCH:
            return self._eval_symbolic_call(node)

        # Canvas commands — xlabel, ylabel, title, grid
        if node.name in ("xlabel", "ylabel", "title", "grid"):
            return self._eval_canvas_cmd(node)
        # Hold / clear commands
        if node.name == "hold":
            return self._eval_hold_call(node)
        # Help command
        if node.name == "help":
            return self._eval_help_call(node)
        # GPU info command
        if node.name == "gpuinfo":
            info = gpu_info()
            return MathResult(value=info, output_text=info)

        if node.name not in self._scope:
            raise UndefinedSymbolError(node.name)
        fn = self._scope[node.name]
        if not callable(fn):
            raise EvaluationError(f"'{node.name}' is not callable")
        args = [self._eval_node(a).value for a in node.args]
        val = fn(*args)
        return MathResult(value=val, output_text=self._format_value(val))

    def _eval_vector(self, node: VectorNode) -> MathResult:
        elements = [self._eval_node(e).value for e in node.elements]
        val = np.array(elements, dtype=float)
        return MathResult(value=val, output_text=self._format_value(val))

    def _eval_matrix(self, node: MatrixNode) -> MathResult:
        """Evaluate a matrix literal ``[1,2; 3,4]`` to a 2-D ``np.ndarray``.

        Also handles nested brackets: ``[[1,2];[3,4]]`` — inner vectors are
        flattened so MATLAB-style notation works seamlessly.
        """
        rows: list[list[float]] = []
        col_count: int | None = None
        for row_nodes in node.rows:
            row_vals: list[float] = []
            for e in row_nodes:
                val = self._eval_node(e).value
                # Flatten inner vectors/arrays so [[1,2];[3,4]] works
                if isinstance(val, np.ndarray) and val.ndim >= 1:
                    row_vals.extend(float(x) for x in val.flat)
                else:
                    row_vals.append(float(val))
            if col_count is None:
                col_count = len(row_vals)
            elif len(row_vals) != col_count:
                raise DimensionError(
                    f"Matrix row length mismatch: expected {col_count}, got {len(row_vals)}"
                )
            rows.append(row_vals)
        val = np.array(rows, dtype=float)
        return MathResult(value=val, output_text=self._format_value(val))

    def _eval_assignment(self, node: AssignmentNode) -> MathResult:
        result = self._eval_node(node.value)
        if node.name in self._BUILTINS:
            raise EvaluationError(
                f"Cannot reassign built-in '{node.name}'"
            )
        self._scope[node.name] = result.value

        # ── Equation graphing: y = f(x) auto-plot ───────────────────
        # If the name is "y" and the RHS is a 1-D array that looks like
        # it was computed from an x vector in scope, auto-plot it.
        if (
            node.name == "y"
            and isinstance(result.value, np.ndarray)
            and result.value.ndim == 1
            and "x" in self._scope
            and isinstance(self._scope["x"], np.ndarray)
            and self._scope["x"].ndim == 1
            and len(self._scope["x"]) == len(result.value)
        ):
            cmd = PlotCommand(
                kind=PlotKind.LINE_2D,
                data={"x": self._scope["x"], "y": result.value},
                label="y",
            )
            return MathResult(
                value=result.value,
                plot_commands=[cmd],
                output_text=f"y = … → auto-plotted ({len(result.value)} points)",
            )

        return MathResult(
            value=result.value,
            output_text=f"{node.name} = {self._format_value(result.value)}",
        )

    def _eval_index_access(self, node: IndexAccessNode) -> MathResult:
        """Handle ``v[i]`` element access on arrays / matrices."""
        obj = self._eval_node(node.obj).value
        idx = self._eval_node(node.index).value
        try:
            val = obj[int(idx)]
        except (IndexError, TypeError) as exc:
            raise EvaluationError(f"Index error: {exc}") from exc
        return MathResult(value=val, output_text=self._format_value(val))

    def _eval_ternary(self, node: TernaryNode) -> MathResult:
        """Handle ``cond ? if_true : if_false``."""
        cond = self._eval_node(node.condition).value
        if np.isscalar(cond):
            branch = node.if_true if bool(cond) else node.if_false
            result = self._eval_node(branch)
            return MathResult(value=result.value, output_text=self._format_value(result.value))
        # Element-wise ternary for arrays
        tv = self._eval_node(node.if_true).value
        fv = self._eval_node(node.if_false).value
        val = np.where(np.asarray(cond, dtype=bool), tv, fv)
        return MathResult(value=val, output_text=self._format_value(val))

    def _eval_pipe(self, node: PipeNode) -> MathResult:
        """Handle ``expr |> func`` — passes expr result as first arg to func."""
        val = self._eval_node(node.value).value
        func_node = FuncCallNode(name=node.func_name, args=[NumberNode(value=0)])
        # Temporarily replace the arg with the actual value
        if node.func_name not in self._scope:
            raise UndefinedSymbolError(node.func_name)
        fn = self._scope[node.func_name]
        if not callable(fn):
            raise EvaluationError(f"'{node.func_name}' is not callable")
        result = fn(val)
        return MathResult(value=result, output_text=self._format_value(result))

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
            raise EvaluationError(
                "plot() requires 1 or 2 arguments: plot(y) or plot(x, y)\n"
                "  Example: x = linspace(0, 10, 100); plot(x, sin(x))"
            )

        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": x_data, "y": y_data},
        )
        return MathResult(plot_commands=[cmd], output_text="→ plot rendered")

    def _eval_scatter_call(self, node: FuncCallNode) -> MathResult:
        """Handle ``scatter(x, y)``."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 2:
            raise EvaluationError(
                "scatter() requires 2 arguments: scatter(x, y)\n"
                "  Example: scatter(linspace(0,10,50), sin(linspace(0,10,50)))"
            )
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
            raise EvaluationError(
                "vector() requires 2 or 4 arguments:\n"
                "  vector(dx, dy)           — from origin\n"
                "  vector(x0, y0, dx, dy)   — from (x0, y0)"
            )
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
            raise EvaluationError(
                "bar() requires 1 or 2 arguments: bar(heights) or bar(x, heights)\n"
                "  Example: bar([3, 7, 2, 5])"
            )
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
            raise EvaluationError(
                "hist() requires 1 or 2 arguments: hist(data) or hist(data, bins)\n"
                "  Example: hist(linspace(0, 10, 100), 20)"
            )
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
        "limit": _sym_limit,
        "series": _sym_series,
        "partial": _sym_partial,
        "gradient": _sym_gradient,
        "divergence": _sym_divergence,
        "curl": _sym_curl,
        "laplacian": _sym_laplacian,
        "laplace": _sym_laplace,
        "invlaplace": _sym_inv_laplace,
        "taylor": _sym_taylor,
        "summation": _sym_summation,
        "product": _sym_product,
        "defint": _sym_defintegral,
        "nsolve": _sym_nsolve,
        "rref": _sym_rref,
        "nullspace": _sym_nullspace,
        "colspace": _sym_colspace,
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
        # Substitute user-defined scalars into the expression
        args[0] = self._subst_vars(args[0], reserved=set())
        result_str = fn(*args)
        return MathResult(value=result_str, output_text=result_str)

    # ------------------------------------------------------------------
    # Canvas command helpers
    # ------------------------------------------------------------------

    def _eval_canvas_cmd(self, node: FuncCallNode) -> MathResult:
        """Handle ``xlabel("X")``, ``ylabel("Y")``, ``title("T")``, ``grid()``."""
        args = [self._eval_node(a).value for a in node.args]
        data: dict[str, Any] = {"cmd": node.name}
        if node.name in ("xlabel", "ylabel", "title"):
            if not args or not isinstance(args[0], str):
                raise EvaluationError(f'{node.name}() requires a string argument')
            data["text"] = args[0]
        elif node.name == "grid":
            # grid() toggles; grid(1)/grid(0) sets explicitly
            data["visible"] = bool(args[0]) if args else None
        cmd = PlotCommand(kind=PlotKind.CANVAS_CMD, data=data)
        return MathResult(
            plot_commands=[cmd],
            output_text=f"→ {node.name} set",
        )

    def _eval_hold_call(self, node: FuncCallNode) -> MathResult:
        """Handle ``hold()``, ``hold(1)``, ``hold(0)``."""
        args = [self._eval_node(a).value for a in node.args]
        if args:
            self._hold_mode = bool(args[0])
        else:
            self._hold_mode = not self._hold_mode
        state = "on" if self._hold_mode else "off"
        return MathResult(
            value=float(self._hold_mode),
            output_text=f"→ hold {state}",
        )

    def _eval_help_call(self, node: FuncCallNode) -> MathResult:
        """Handle ``help()`` — list all available functions and constants."""
        functions = sorted(
            k for k, v in self._BUILTINS.items() if callable(v)
        )
        constants = sorted(
            k for k, v in self._BUILTINS.items() if not callable(v)
        )
        commands = [
            # ── Plotting (basic) ──
            "plot(y) / plot(x,y)", "scatter(x,y)", "vector(dx,dy) / vector(x0,y0,dx,dy)",
            "bar(h) / bar(x,h)", "hist(data) / hist(data,bins)",
            'fplot("expr") / fplot("expr", a, b)',
            'polar("r(t)") / polar("r(t)", t0, t1)',
            'parametric("x(t)", "y(t)") / parametric("x(t)","y(t)", t0, t1)',
            'parametric3d("x(t)","y(t)","z(t)", t0, t1)',
            'surface("f(x,y)") / surface("f(x,y)", x0, x1, y0, y1)',
            'wireframe("f(x,y)")',
            'plotderiv("expr") / plotderiv("expr", a, b)',
            'plotintegral("expr", a, b)',
            'tangentline("expr", x0)',
            'implicit("f(x,y)")',
            'contour("f(x,y)")',
            'slopefield("dy/dx expr")',
            # ── Plotting (new Phase 7) ──
            "heatmap(Z) / heatmap(Z,cmap)", "vectorfield(U,V) / vectorfield(X,Y,U,V)",
            "stem(y) / stem(x,y)", "step(y) / step(x,y)",
            "pie(vals) / pie(vals,labels)", "errorbar(x,y,yerr)",
            "scatter3d(x,y,z)", 'surfparam("x(u,v)","y(u,v)","z(u,v)")',
            "bar3d(x,y,z,h)",
            "logplot(x,y)", "semilogx(x,y)", "semilogy(x,y)", "area(x,y)",
            # ── Canvas / UI ──
            "xlabel(s) / ylabel(s) / title(s)", "grid() / grid(1/0)",
            "hold() / hold(1/0)", "help()", "gpuinfo()",
            # ── Symbolic algebra ──
            'simplify("expr")', 'factor("expr")', 'expand("expr")',
            'diff("expr","var")', 'integrate("expr","var")', 'solve("expr","var")',
            # ── Calculus ──
            'limit("expr","var",val)', 'series("expr","var",point,n)',
            'taylor("expr","var",point,n)', 'partial("expr","var")',
            'defint("expr","var",a,b)',
            'summation("expr","var",a,b)', 'product("expr","var",a,b)',
            # ── Vector calculus ──
            'gradient("expr","x,y,...")', 'divergence("F1,F2,...","x,y,...")',
            'curl("F1,F2,F3","x,y,z")', 'laplacian("expr","x,y,...")',
            # ── Transforms ──
            'laplace("expr","t","s")', 'invlaplace("expr","s","t")',
            # ── Numerical / Linear algebra ──
            'nsolve("expr","var",x0)',
            'rref("[[a,b];[c,d]]")', 'nullspace("[[...]]")', 'colspace("[[...]]")',
        ]
        lines = [
            "── GraphUG Help ──",
            f"Functions ({len(functions)}): " + ", ".join(functions),
            f"Constants ({len(constants)}): " + ", ".join(constants),
            "Commands: " + " | ".join(commands),
            "Operators: + - * / % ^ == != < > <= >= and or not",
            "Syntax: var = expr ; [v1,v2] ; [r1;r2] matrix",
        ]
        text = "\n".join(lines)
        return MathResult(value=text, output_text=text)

    # ==================================================================
    # Phase 4 — Advanced graphing commands
    # ==================================================================

    _FPLOT_N: int = 500  # default sample count for function plots

    def _require_sympy(self, cmd_name: str) -> None:
        if not _sympy_available():
            raise EvaluationError(
                f"{cmd_name}() requires SymPy.  Run: pip install sympy"
            )

    def _subst_vars(self, expr_str: str, reserved: set[str] | None = None) -> str:
        """Substitute user-defined scalar variables into *expr_str*.

        Only replaces names that exist in ``_scope``, are numeric scalars,
        and are **not** in *reserved* (e.g. ``{"x", "y", "t"}``).
        This lets users write ``a = 2; fplot("a*x^2")``.
        """
        import re as _re

        if reserved is None:
            reserved = set()
        # Iterate user variables (skip builtins — they're already known to SymPy)
        for name, val in self._scope.items():
            if name in self._BUILTINS:
                continue
            if name in reserved:
                continue
            if not isinstance(val, (int, float)):
                if isinstance(val, np.floating):
                    val = float(val)
                else:
                    continue
            # Replace whole-word occurrences with the numeric value
            expr_str = _re.sub(
                rf"\b{_re.escape(name)}\b", f"({val:g})", expr_str
            )
        return expr_str

    # ── fplot ─────────────────────────────────────────────────────────

    def _eval_fplot_call(self, node: FuncCallNode) -> MathResult:
        """``fplot("sin(x)")`` or ``fplot("x^2", -5, 5)`` or ``fplot("x^2", -5, 5, 800)``."""
        self._require_sympy("fplot")
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                'fplot() first argument must be a string expression of x.\n'
                '  Usage: fplot("sin(x)") or fplot("x^2", -5, 5)\n'
                '  Optional: fplot("expr", xmin, xmax, num_points)'
            )
        expr_str = args[0]
        a, b = -10.0, 10.0
        n = self._FPLOT_N
        if len(args) >= 3:
            a, b = float(args[1]), float(args[2])
        if len(args) >= 4:
            n = int(args[3])

        expr_str = self._subst_vars(expr_str, reserved={"x"})
        fn = _sym_lambdify(expr_str)
        x = np.linspace(a, b, n)
        y = fn(x)
        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": x, "y": y},
            label=args[0],
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ fplot: {args[0]}")

    # ── polar ─────────────────────────────────────────────────────────

    def _eval_polar_call(self, node: FuncCallNode) -> MathResult:
        """``polar("2*cos(t)")`` or ``polar("1+sin(t)", 0, 2*pi)``."""
        self._require_sympy("polar")
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                'polar() first argument must be a string expression of t.\n'
                '  Usage: polar("2*cos(t)") or polar("1+sin(t)", 0, 2*pi)'
            )
        expr_str = args[0]
        t0, t1 = 0.0, 2.0 * math.pi
        if len(args) >= 3:
            t0, t1 = float(args[1]), float(args[2])

        expr_str = self._subst_vars(expr_str, reserved={"t"})
        fn = _sym_lambdify(expr_str, var="t")
        t = np.linspace(t0, t1, self._FPLOT_N)
        r = fn(t)
        x = r * np.cos(t)
        y = r * np.sin(t)
        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": x, "y": y},
            label=f"r = {expr_str}",
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ polar: r = {expr_str}")

    # ── parametric 2D ─────────────────────────────────────────────────

    def _eval_parametric_call(self, node: FuncCallNode) -> MathResult:
        """``parametric("cos(t)", "sin(t)")`` or ``parametric("cos(t)", "sin(t)", 0, 6.28)``."""
        self._require_sympy("parametric")
        args = [self._eval_node(a).value for a in node.args]
        if len(args) < 2 or not isinstance(args[0], str) or not isinstance(args[1], str):
            raise EvaluationError(
                'parametric() requires two string arguments: x(t) and y(t).\n'
                '  Usage: parametric("cos(t)", "sin(t)")\n'
                '  Optional range: parametric("cos(t)", "sin(t)", 0, 6.28)'
            )
        x_expr, y_expr = args[0], args[1]
        t0, t1 = 0.0, 2.0 * math.pi
        if len(args) >= 4:
            t0, t1 = float(args[2]), float(args[3])

        x_expr = self._subst_vars(x_expr, reserved={"t"})
        y_expr = self._subst_vars(y_expr, reserved={"t"})
        fx = _sym_lambdify(x_expr, var="t")
        fy = _sym_lambdify(y_expr, var="t")
        t = np.linspace(t0, t1, self._FPLOT_N)
        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": fx(t), "y": fy(t)},
            label=f"({x_expr}, {y_expr})",
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ parametric: ({x_expr}, {y_expr})")

    # ── parametric 3D ─────────────────────────────────────────────────

    def _eval_parametric3d_call(self, node: FuncCallNode) -> MathResult:
        """``parametric3d("cos(t)", "sin(t)", "t/10", 0, 20)``."""
        self._require_sympy("parametric3d")
        args = [self._eval_node(a).value for a in node.args]
        if len(args) < 3:
            raise EvaluationError(
                'parametric3d() requires at least 3 string arguments: x(t), y(t), z(t).\n'
                '  Usage: parametric3d("cos(t)", "sin(t)", "t/10", 0, 20)'
            )
        for i in range(3):
            if not isinstance(args[i], str):
                raise EvaluationError(f"parametric3d() argument {i+1} must be a string expression")
        x_expr, y_expr, z_expr = args[0], args[1], args[2]
        t0, t1 = 0.0, 2.0 * math.pi
        if len(args) >= 5:
            t0, t1 = float(args[3]), float(args[4])

        x_expr = self._subst_vars(x_expr, reserved={"t"})
        y_expr = self._subst_vars(y_expr, reserved={"t"})
        z_expr = self._subst_vars(z_expr, reserved={"t"})
        fx = _sym_lambdify(x_expr, var="t")
        fy = _sym_lambdify(y_expr, var="t")
        fz = _sym_lambdify(z_expr, var="t")
        t = np.linspace(t0, t1, self._FPLOT_N)
        cmd = PlotCommand(
            kind=PlotKind.PARAMETRIC_3D,
            data={"x": fx(t), "y": fy(t), "z": fz(t)},
            label=f"({x_expr}, {y_expr}, {z_expr})",
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ parametric3d rendered")

    # ── surface ───────────────────────────────────────────────────────

    def _eval_surface_call(self, node: FuncCallNode) -> MathResult:
        """``surface("sin(x)*cos(y)")`` or ``surface("x^2+y^2", -3, 3, -3, 3)``."""
        self._require_sympy("surface")
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                'surface() first argument must be a string expression of x and y.\n'
                '  Usage: surface("sin(x)*cos(y)")\n'
                '  With range: surface("x^2+y^2", -3, 3, -3, 3)'
            )
        expr_str = args[0]
        x0, x1, y0, y1 = -5.0, 5.0, -5.0, 5.0
        if len(args) >= 5:
            x0, x1, y0, y1 = float(args[1]), float(args[2]), float(args[3]), float(args[4])

        expr_str = self._subst_vars(expr_str, reserved={"x", "y"})
        fn = _sym_lambdify_2d(expr_str)
        n = 80
        x = np.linspace(x0, x1, n)
        y = np.linspace(y0, y1, n)
        X, Y = np.meshgrid(x, y)
        Z = fn(X, Y)
        cmd = PlotCommand(
            kind=PlotKind.SURFACE_3D,
            data={"x": X, "y": Y, "z": Z},
            label=expr_str,
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ surface: {expr_str}")

    # ── wireframe ─────────────────────────────────────────────────────

    def _eval_wireframe_call(self, node: FuncCallNode) -> MathResult:
        """``wireframe("sin(x)*cos(y)")`` or ``wireframe("expr", x0, x1, y0, y1)``."""
        self._require_sympy("wireframe")
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                'wireframe() first argument must be a string expression of x and y.\n'
                '  Usage: wireframe("sin(x)*cos(y)")'
            )
        expr_str = args[0]
        x0, x1, y0, y1 = -5.0, 5.0, -5.0, 5.0
        if len(args) >= 5:
            x0, x1, y0, y1 = float(args[1]), float(args[2]), float(args[3]), float(args[4])

        expr_str = self._subst_vars(expr_str, reserved={"x", "y"})
        fn = _sym_lambdify_2d(expr_str)
        n = 40
        x = np.linspace(x0, x1, n)
        y = np.linspace(y0, y1, n)
        X, Y = np.meshgrid(x, y)
        Z = fn(X, Y)
        cmd = PlotCommand(
            kind=PlotKind.WIREFRAME_3D,
            data={"x": X, "y": Y, "z": Z},
            label=expr_str,
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ wireframe: {expr_str}")

    # ── plotderiv ─────────────────────────────────────────────────────

    def _eval_plotderiv_call(self, node: FuncCallNode) -> MathResult:
        """``plotderiv("sin(x)")`` or ``plotderiv("x^2", -5, 5)``."""
        self._require_sympy("plotderiv")
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                'plotderiv() first argument must be a string expression of x.\n'
                '  Usage: plotderiv("sin(x)") or plotderiv("x^2", -5, 5)'
            )
        expr_str = args[0]
        a, b = -10.0, 10.0
        if len(args) >= 3:
            a, b = float(args[1]), float(args[2])

        expr_str = self._subst_vars(expr_str, reserved={"x"})
        deriv_str = _sym_diff_expr(expr_str)
        fn_orig = _sym_lambdify(expr_str)
        fn_deriv = _sym_lambdify(deriv_str)
        x = np.linspace(a, b, self._FPLOT_N)
        cmds = [
            PlotCommand(kind=PlotKind.LINE_2D, data={"x": x, "y": fn_orig(x)}, label=f"f(x) = {expr_str}"),
            PlotCommand(kind=PlotKind.LINE_2D, data={"x": x, "y": fn_deriv(x)}, label=f"f'(x) = {deriv_str}"),
        ]
        return MathResult(plot_commands=cmds, output_text=f"→ plotderiv: f'(x) = {deriv_str}")

    # ── plotintegral ──────────────────────────────────────────────────

    def _eval_plotintegral_call(self, node: FuncCallNode) -> MathResult:
        """``plotintegral("x^2", 0, 2)`` — plot function and shade the integral area."""
        self._require_sympy("plotintegral")
        args = [self._eval_node(a).value for a in node.args]
        if len(args) < 3 or not isinstance(args[0], str):
            raise EvaluationError(
                'plotintegral() requires: plotintegral("expr", a, b)\n'
                '  Example: plotintegral("x^2", 0, 2)'
            )
        expr_str = args[0]
        a_val, b_val = float(args[1]), float(args[2])

        expr_str = self._subst_vars(expr_str, reserved={"x"})
        fn = _sym_lambdify(expr_str)
        # Full curve
        x_full = np.linspace(min(a_val, b_val) - 2, max(a_val, b_val) + 2, self._FPLOT_N)
        y_full = fn(x_full)
        # Integration region
        x_fill = np.linspace(a_val, b_val, 300)
        y_fill = fn(x_fill)

        # Compute numerical integral value for display
        area = float(np.trapezoid(y_fill, x_fill))

        cmds = [
            PlotCommand(kind=PlotKind.LINE_2D, data={"x": x_full, "y": y_full}, label=expr_str),
            PlotCommand(
                kind=PlotKind.FILL_BETWEEN,
                data={"x": x_fill, "y1": y_fill, "y2": np.zeros_like(x_fill)},
                label=f"∫ [{a_val:g}, {b_val:g}]",
            ),
        ]
        return MathResult(
            plot_commands=cmds,
            output_text=f"→ ∫ {expr_str} dx from {a_val:g} to {b_val:g} ≈ {area:g}",
        )

    # ── tangentline ───────────────────────────────────────────────────

    def _eval_tangentline_call(self, node: FuncCallNode) -> MathResult:
        """``tangentline("x^2", 1)`` — plot function and its tangent at x0."""
        self._require_sympy("tangentline")
        args = [self._eval_node(a).value for a in node.args]
        if len(args) < 2 or not isinstance(args[0], str):
            raise EvaluationError(
                'tangentline() requires: tangentline("expr", x0)\n'
                '  Example: tangentline("x^2", 1)\n'
                '  Optional range: tangentline("x^2", 1, -3, 5)'
            )
        expr_str = args[0]
        x0 = float(args[1])
        a, b = x0 - 5.0, x0 + 5.0
        if len(args) >= 4:
            a, b = float(args[2]), float(args[3])

        expr_str = self._subst_vars(expr_str, reserved={"x"})
        slope, y0 = _sym_tangent_at(expr_str, x0)
        fn = _sym_lambdify(expr_str)
        x = np.linspace(a, b, self._FPLOT_N)
        # Tangent line: y = slope*(x - x0) + y0
        y_tan = slope * (x - x0) + y0

        cmds = [
            PlotCommand(kind=PlotKind.LINE_2D, data={"x": x, "y": fn(x)}, label=expr_str),
            PlotCommand(kind=PlotKind.LINE_2D, data={"x": x, "y": y_tan}, label=f"tangent at x={x0:g}"),
            PlotCommand(
                kind=PlotKind.SCATTER,
                data={"x": np.array([x0]), "y": np.array([y0])},
                label=f"({x0:g}, {y0:g})",
            ),
        ]
        return MathResult(
            plot_commands=cmds,
            output_text=f"→ tangent at x={x0:g}: y = {slope:g}·(x − {x0:g}) + {y0:g}",
        )

    # ── implicit ──────────────────────────────────────────────────────

    def _eval_implicit_call(self, node: FuncCallNode) -> MathResult:
        """``implicit("x^2 + y^2 - 1")`` — plot the zero level-set of f(x,y)."""
        self._require_sympy("implicit")
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                'implicit() first argument must be a string expression of x and y.\n'
                '  Usage: implicit("x^2 + y^2 - 1") plots the curve f(x,y) = 0'
            )
        expr_str = args[0]
        x0, x1, y0, y1 = -5.0, 5.0, -5.0, 5.0
        if len(args) >= 5:
            x0, x1, y0, y1 = float(args[1]), float(args[2]), float(args[3]), float(args[4])

        expr_str = self._subst_vars(expr_str, reserved={"x", "y"})
        fn = _sym_lambdify_2d(expr_str)
        n = 200
        x = np.linspace(x0, x1, n)
        y = np.linspace(y0, y1, n)
        X, Y = np.meshgrid(x, y)
        Z = fn(X, Y)

        cmd = PlotCommand(
            kind=PlotKind.IMPLICIT_2D,
            data={"z": Z, "x_range": (x0, x1), "y_range": (y0, y1)},
            label=f"{expr_str} = 0",
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ implicit: {expr_str} = 0")

    # ── contour ───────────────────────────────────────────────────────

    def _eval_contour_call(self, node: FuncCallNode) -> MathResult:
        """``contour("x^2 + y^2")`` or ``contour("x^2+y^2", -5, 5, -5, 5, 10)``."""
        self._require_sympy("contour")
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                'contour() first argument must be a string expression of x and y.\n'
                '  Usage: contour("x^2 + y^2")\n'
                '  With range: contour("x^2+y^2", -5, 5, -5, 5, 10)'
            )
        expr_str = args[0]
        x0, x1, y0, y1 = -5.0, 5.0, -5.0, 5.0
        n_levels = 10
        if len(args) >= 5:
            x0, x1, y0, y1 = float(args[1]), float(args[2]), float(args[3]), float(args[4])
        if len(args) >= 6:
            n_levels = int(args[5])

        expr_str = self._subst_vars(expr_str, reserved={"x", "y"})
        fn = _sym_lambdify_2d(expr_str)
        n = 200
        x = np.linspace(x0, x1, n)
        y = np.linspace(y0, y1, n)
        X, Y = np.meshgrid(x, y)
        Z = fn(X, Y)

        z_min, z_max = float(np.nanmin(Z)), float(np.nanmax(Z))
        levels = np.linspace(z_min, z_max, n_levels + 2)[1:-1].tolist()

        cmd = PlotCommand(
            kind=PlotKind.CONTOUR,
            data={
                "z": Z,
                "x_range": (x0, x1),
                "y_range": (y0, y1),
                "levels": levels,
            },
            label=expr_str,
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ contour: {expr_str}")

    # ── slopefield ────────────────────────────────────────────────────

    def _eval_slopefield_call(self, node: FuncCallNode) -> MathResult:
        """``slopefield("y - x")`` — slope field where dy/dx = f(x, y)."""
        self._require_sympy("slopefield")
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                'slopefield() first argument must be a string expression of x and y.\n'
                '  This plots the slope field where dy/dx = f(x, y).\n'
                '  Usage: slopefield("y - x")'
            )
        expr_str = args[0]
        x0, x1, y0, y1 = -5.0, 5.0, -5.0, 5.0
        n_grid = 20
        if len(args) >= 5:
            x0, x1, y0, y1 = float(args[1]), float(args[2]), float(args[3]), float(args[4])
        if len(args) >= 6:
            n_grid = int(args[5])

        expr_str = self._subst_vars(expr_str, reserved={"x", "y"})
        fn = _sym_lambdify_2d(expr_str)
        xs = np.linspace(x0, x1, n_grid)
        ys = np.linspace(y0, y1, n_grid)
        X, Y = np.meshgrid(xs, ys)
        DY = fn(X, Y)
        DX = np.ones_like(DY)
        # Normalise arrow lengths
        mag = np.sqrt(DX**2 + DY**2)
        mag[mag == 0] = 1.0
        scale = min(x1 - x0, y1 - y0) / (n_grid * 2.5)
        DX = DX / mag * scale
        DY = DY / mag * scale

        cmd = PlotCommand(
            kind=PlotKind.SLOPE_FIELD,
            data={"X": X, "Y": Y, "DX": DX, "DY": DY},
            label=f"dy/dx = {expr_str}",
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ slope field: dy/dx = {expr_str}")

    # ==================================================================
    # Phase 7 — New graphing commands
    # ==================================================================

    # ── heatmap ───────────────────────────────────────────────────────

    def _eval_heatmap_call(self, node: FuncCallNode) -> MathResult:
        """``heatmap("sin(x)*cos(y)")`` or ``heatmap("expr", x0, x1, y0, y1)``."""
        self._require_sympy("heatmap")
        args = [self._eval_node(a).value for a in node.args]
        if not args or not isinstance(args[0], str):
            raise EvaluationError(
                'heatmap() first argument must be a string expression of x and y.\n'
                '  Usage: heatmap("sin(x)*cos(y)")\n'
                '  With range: heatmap("x^2+y^2", -5, 5, -5, 5)'
            )
        expr_str = args[0]
        x0, x1, y0, y1 = -5.0, 5.0, -5.0, 5.0
        if len(args) >= 5:
            x0, x1, y0, y1 = float(args[1]), float(args[2]), float(args[3]), float(args[4])

        expr_str = self._subst_vars(expr_str, reserved={"x", "y"})
        fn = _sym_lambdify_2d(expr_str)
        n = 150
        x = np.linspace(x0, x1, n)
        y = np.linspace(y0, y1, n)
        X, Y = np.meshgrid(x, y)
        Z = fn(X, Y)

        cmd = PlotCommand(
            kind=PlotKind.HEATMAP,
            data={"z": Z, "x_range": (x0, x1), "y_range": (y0, y1)},
            label=expr_str,
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ heatmap: {expr_str}")

    # ── vectorfield ───────────────────────────────────────────────────

    def _eval_vectorfield_call(self, node: FuncCallNode) -> MathResult:
        """``vectorfield("-y", "x")`` — 2-D vector field (u, v) = (f1(x,y), f2(x,y))."""
        self._require_sympy("vectorfield")
        args = [self._eval_node(a).value for a in node.args]
        if len(args) < 2 or not isinstance(args[0], str) or not isinstance(args[1], str):
            raise EvaluationError(
                'vectorfield() requires two string expressions u(x,y) and v(x,y).\n'
                '  Usage: vectorfield("-y", "x")\n'
                '  With range: vectorfield("-y", "x", -5, 5, -5, 5)'
            )
        u_expr, v_expr = args[0], args[1]
        x0, x1, y0, y1 = -5.0, 5.0, -5.0, 5.0
        n_grid = 20
        if len(args) >= 6:
            x0, x1, y0, y1 = float(args[2]), float(args[3]), float(args[4]), float(args[5])
        if len(args) >= 7:
            n_grid = int(args[6])

        u_expr = self._subst_vars(u_expr, reserved={"x", "y"})
        v_expr = self._subst_vars(v_expr, reserved={"x", "y"})
        fu = _sym_lambdify_2d(u_expr)
        fv = _sym_lambdify_2d(v_expr)
        xs = np.linspace(x0, x1, n_grid)
        ys = np.linspace(y0, y1, n_grid)
        X, Y = np.meshgrid(xs, ys)
        U = fu(X, Y)
        V = fv(X, Y)
        # Normalise
        mag = np.sqrt(U**2 + V**2)
        mag[mag == 0] = 1.0
        scale = min(x1 - x0, y1 - y0) / (n_grid * 2.0)
        U_n = U / mag * scale
        V_n = V / mag * scale

        cmd = PlotCommand(
            kind=PlotKind.VECTOR_FIELD_2D,
            data={"X": X, "Y": Y, "U": U_n, "V": V_n, "mag": mag},
            label=f"F = ({u_expr}, {v_expr})",
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ vector field: ({u_expr}, {v_expr})")

    # ── stem ──────────────────────────────────────────────────────────

    def _eval_stem_call(self, node: FuncCallNode) -> MathResult:
        """``stem(y)`` or ``stem(x, y)`` — stem (lollipop) plot."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) == 1:
            y_data = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            x_data = np.arange(len(y_data), dtype=float)
        elif len(args) == 2:
            x_data = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            y_data = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        else:
            raise EvaluationError(
                "stem() requires 1 or 2 arguments: stem(y) or stem(x, y)"
            )
        cmd = PlotCommand(
            kind=PlotKind.STEM,
            data={"x": x_data, "y": y_data},
        )
        return MathResult(plot_commands=[cmd], output_text="→ stem plot rendered")

    # ── step ──────────────────────────────────────────────────────────

    def _eval_step_call(self, node: FuncCallNode) -> MathResult:
        """``step(y)`` or ``step(x, y)`` — staircase plot."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) == 1:
            y_data = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            x_data = np.arange(len(y_data), dtype=float)
        elif len(args) == 2:
            x_data = np.atleast_1d(np.asarray(args[0].value, dtype=float))
            y_data = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        else:
            raise EvaluationError(
                "step() requires 1 or 2 arguments: step(y) or step(x, y)"
            )
        cmd = PlotCommand(
            kind=PlotKind.STEP,
            data={"x": x_data, "y": y_data},
        )
        return MathResult(plot_commands=[cmd], output_text="→ step plot rendered")

    # ── pie ───────────────────────────────────────────────────────────

    def _eval_pie_call(self, node: FuncCallNode) -> MathResult:
        """``pie([30, 20, 50])`` — pie chart (rendered as a bar chart since
        pyqtgraph has no native pie widget)."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 1:
            raise EvaluationError("pie() requires 1 argument: pie(values)")
        values = np.atleast_1d(np.asarray(args[0].value, dtype=float))
        cmd = PlotCommand(
            kind=PlotKind.PIE,
            data={"values": values},
        )
        return MathResult(plot_commands=[cmd], output_text="→ pie chart rendered")

    # ── errorbar ──────────────────────────────────────────────────────

    def _eval_errorbar_call(self, node: FuncCallNode) -> MathResult:
        """``errorbar(x, y, err)`` — plot with error bars."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 3:
            raise EvaluationError(
                "errorbar() requires 3 arguments: errorbar(x, y, err)\n"
                "  Example: errorbar([1,2,3], [4,5,6], [0.5,0.3,0.4])"
            )
        x_data = np.atleast_1d(np.asarray(args[0].value, dtype=float))
        y_data = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        err = np.atleast_1d(np.asarray(args[2].value, dtype=float))
        cmd = PlotCommand(
            kind=PlotKind.ERRORBAR,
            data={"x": x_data, "y": y_data, "err": err},
        )
        return MathResult(plot_commands=[cmd], output_text="→ error bar plot rendered")

    # ── scatter3d ─────────────────────────────────────────────────────

    def _eval_scatter3d_call(self, node: FuncCallNode) -> MathResult:
        """``scatter3d(x, y, z)`` — 3-D scatter plot."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 3:
            raise EvaluationError(
                "scatter3d() requires 3 arguments: scatter3d(x, y, z)"
            )
        x = np.atleast_1d(np.asarray(args[0].value, dtype=float))
        y = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        z = np.atleast_1d(np.asarray(args[2].value, dtype=float))
        cmd = PlotCommand(
            kind=PlotKind.SCATTER_3D,
            data={"x": x, "y": y, "z": z},
        )
        return MathResult(plot_commands=[cmd], output_text="→ 3D scatter rendered")

    # ── surfparam (parametric surface) ────────────────────────────────

    def _eval_surfparam_call(self, node: FuncCallNode) -> MathResult:
        """``surfparam("cos(u)*sin(v)", "sin(u)*sin(v)", "cos(v)")``
        — parametric surface (u, v) → (x, y, z).  Optional u/v ranges."""
        self._require_sympy("surfparam")
        args = [self._eval_node(a).value for a in node.args]
        if len(args) < 3:
            raise EvaluationError(
                'surfparam() requires 3 string expressions: x(u,v), y(u,v), z(u,v).\n'
                '  Usage: surfparam("cos(u)*sin(v)", "sin(u)*sin(v)", "cos(v)")\n'
                '  With ranges: surfparam("...", "...", "...", u0, u1, v0, v1)'
            )
        for i in range(3):
            if not isinstance(args[i], str):
                raise EvaluationError(f"surfparam() argument {i+1} must be a string expression")
        x_expr, y_expr, z_expr = args[0], args[1], args[2]
        u0, u1 = 0.0, 2.0 * math.pi
        v0, v1 = 0.0, math.pi
        if len(args) >= 7:
            u0, u1, v0, v1 = float(args[3]), float(args[4]), float(args[5]), float(args[6])

        import sympy as sp
        su, sv = sp.Symbol("u"), sp.Symbol("v")
        for v_name in ("u", "v"):
            x_expr = self._subst_vars(x_expr, reserved={"u", "v"})
            y_expr = self._subst_vars(y_expr, reserved={"u", "v"})
            z_expr = self._subst_vars(z_expr, reserved={"u", "v"})
        fx = sp.lambdify((su, sv), sp.sympify(x_expr.replace("^", "**")), modules=["numpy"])
        fy = sp.lambdify((su, sv), sp.sympify(y_expr.replace("^", "**")), modules=["numpy"])
        fz = sp.lambdify((su, sv), sp.sympify(z_expr.replace("^", "**")), modules=["numpy"])
        n = 60
        u = np.linspace(u0, u1, n)
        v = np.linspace(v0, v1, n)
        U, V = np.meshgrid(u, v)
        X = np.asarray(fx(U, V), dtype=float)
        Y = np.asarray(fy(U, V), dtype=float)
        Z = np.asarray(fz(U, V), dtype=float)
        cmd = PlotCommand(
            kind=PlotKind.SURFACE_PARAM_3D,
            data={"x": X, "y": Y, "z": Z},
            label=f"({x_expr}, {y_expr}, {z_expr})",
        )
        return MathResult(plot_commands=[cmd], output_text=f"→ parametric surface rendered")

    # ── bar3d ─────────────────────────────────────────────────────────

    def _eval_bar3d_call(self, node: FuncCallNode) -> MathResult:
        """``bar3d(x, y, z)`` — 3-D bar chart."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 3:
            raise EvaluationError(
                "bar3d() requires 3 arguments: bar3d(x, y, heights)"
            )
        x = np.atleast_1d(np.asarray(args[0].value, dtype=float))
        y = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        z = np.atleast_1d(np.asarray(args[2].value, dtype=float))
        cmd = PlotCommand(
            kind=PlotKind.BAR_3D,
            data={"x": x, "y": y, "z": z},
        )
        return MathResult(plot_commands=[cmd], output_text="→ 3D bar chart rendered")

    # ── logplot ───────────────────────────────────────────────────────

    def _eval_logplot_call(self, node: FuncCallNode) -> MathResult:
        """``logplot(x, y)`` — plot with log-log scale (rendered as LINE_2D with meta)."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 2:
            raise EvaluationError("logplot() requires 2 arguments: logplot(x, y)")
        x = np.atleast_1d(np.asarray(args[0].value, dtype=float))
        y = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        cmds = [
            PlotCommand(kind=PlotKind.LINE_2D, data={"x": x, "y": y}),
            PlotCommand(kind=PlotKind.CANVAS_CMD, data={"cmd": "loglog"}),
        ]
        return MathResult(plot_commands=cmds, output_text="→ log-log plot rendered")

    def _eval_semilogx_call(self, node: FuncCallNode) -> MathResult:
        """``semilogx(x, y)`` — plot with log x axis."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 2:
            raise EvaluationError("semilogx() requires 2 arguments: semilogx(x, y)")
        x = np.atleast_1d(np.asarray(args[0].value, dtype=float))
        y = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        cmds = [
            PlotCommand(kind=PlotKind.LINE_2D, data={"x": x, "y": y}),
            PlotCommand(kind=PlotKind.CANVAS_CMD, data={"cmd": "semilogx"}),
        ]
        return MathResult(plot_commands=cmds, output_text="→ semilog-x plot rendered")

    def _eval_semilogy_call(self, node: FuncCallNode) -> MathResult:
        """``semilogy(x, y)`` — plot with log y axis."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 2:
            raise EvaluationError("semilogy() requires 2 arguments: semilogy(x, y)")
        x = np.atleast_1d(np.asarray(args[0].value, dtype=float))
        y = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        cmds = [
            PlotCommand(kind=PlotKind.LINE_2D, data={"x": x, "y": y}),
            PlotCommand(kind=PlotKind.CANVAS_CMD, data={"cmd": "semilogy"}),
        ]
        return MathResult(plot_commands=cmds, output_text="→ semilog-y plot rendered")

    # ── area ──────────────────────────────────────────────────────────

    def _eval_area_call(self, node: FuncCallNode) -> MathResult:
        """``area(x, y)`` — filled area plot under curve."""
        args = [self._eval_node(a) for a in node.args]
        if len(args) != 2:
            raise EvaluationError("area() requires 2 arguments: area(x, y)")
        x = np.atleast_1d(np.asarray(args[0].value, dtype=float))
        y = np.atleast_1d(np.asarray(args[1].value, dtype=float))
        cmds = [
            PlotCommand(kind=PlotKind.LINE_2D, data={"x": x, "y": y}),
            PlotCommand(
                kind=PlotKind.FILL_BETWEEN,
                data={"x": x, "y1": y, "y2": np.zeros_like(y)},
            ),
        ]
        return MathResult(plot_commands=cmds, output_text="→ area plot rendered")
