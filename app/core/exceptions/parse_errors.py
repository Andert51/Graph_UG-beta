"""GraphUG exception hierarchy.

All exceptions inherit from ``GraphUGError`` so that callers can either catch
the base class to swallow all domain errors, or catch a specific subclass for
precise handling.
"""

from __future__ import annotations

import difflib


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
        return (
            f"SyntaxError{loc}: {super().__str__()}\n"
            f"  Hint: Check for missing parentheses, operators, or unmatched brackets."
        )


# ---------------------------------------------------------------------------
# Evaluation errors
# ---------------------------------------------------------------------------


class EvaluationError(GraphUGError):
    """Raised when a syntactically valid expression cannot be evaluated.

    Examples include type mismatches, shape errors, or unsupported operations.
    """


# All built-in names for "did you mean?" suggestions
_KNOWN_NAMES: list[str] = sorted({
    # Trig
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "sec", "csc", "cot", "sinc", "deg2rad", "rad2deg",
    # Transcendentals / math
    "sqrt", "cbrt", "exp", "exp2", "expm1",
    "log", "log2", "log10", "log1p",
    "abs", "ceil", "floor", "round",
    "sign", "clip", "mod", "gcd", "lcm",
    "factorial", "comb", "perm", "hypot",
    # Array constructors
    "linspace", "arange", "logspace",
    "zeros", "ones", "eye", "diag", "full",
    "rand", "randn", "randint",
    "meshgrid", "flatten", "sort", "unique", "reverse",
    "concat", "stack", "tile", "repeat",
    # Linear algebra
    "dot", "cross", "norm", "det", "inv", "transpose",
    "trace", "rank", "eig", "eigvals", "svd", "pinv",
    "solve_linear", "lu", "qr", "cholesky",
    "cond", "outer", "inner", "kron", "matmul",
    # Stats
    "sum", "mean", "min", "max", "std", "var", "len", "reshape",
    "median", "percentile", "cumsum", "cumprod", "prod",
    "argmin", "argmax", "histogram", "corrcoef", "cov",
    # Introspection
    "typeof", "size", "ndim", "isnan", "isinf",
    # Utility / numerical
    "where", "interp", "gradient", "diff_array", "trapz",
    "polyfit", "polyval", "roots", "convolve",
    "fft", "ifft", "fftfreq",
    # Vector calculus (numeric)
    "magnitude", "normalize", "angle", "proj", "reject",
    # Symbolic
    "simplify", "factor", "expand", "diff", "integrate", "solve",
    "limit", "series", "partial", "taylor", "defint",
    "summation", "product", "nsolve",
    "divergence", "curl", "laplacian",
    "laplace", "invlaplace",
    "rref", "nullspace", "colspace",
    # Plot
    "plot", "scatter", "vector", "bar", "hist",
    "fplot", "polar", "parametric", "parametric3d",
    "surface", "wireframe",
    "plotderiv", "plotintegral", "tangentline",
    "implicit", "contour", "slopefield",
    # Phase 7 — new plot commands
    "heatmap", "vectorfield", "stem", "step", "pie", "errorbar",
    "scatter3d", "surfparam", "bar3d",
    "logplot", "semilogx", "semilogy", "area",
    # Phase 7 — complex numbers
    "complex", "real", "imag", "conj", "phase",
    # Phase 7 — special matrices
    "vander", "toeplitz", "hilbert", "companion", "triu", "tril", "block_diag",
    # Phase 7 — extended signal processing
    "fftshift", "rfft", "fft2", "hamming", "hanning", "blackman", "kaiser",
    # Phase 7 — set operations
    "union", "intersect", "setdiff", "in1d",
    # Phase 7 — cumulative / moving
    "cummax", "cummin", "movmean",
    # Phase 7 — bitwise
    "bitand", "bitor", "bitxor", "bitnot", "shl", "shr",
    # Phase 7 — functional / regression
    "map_arr", "linreg", "spline_interp",
    # Phase 7 — GPU
    "gpuinfo",
    # Canvas
    "xlabel", "ylabel", "title", "grid", "hold", "help",
    # Constants
    "pi", "e", "inf", "nan", "true", "false",
    "phi", "tau", "euler_gamma",
})


class UndefinedSymbolError(EvaluationError):
    """Raised when an undeclared variable or function is referenced."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        suggestion = self._suggest(symbol)
        hint = f"  Did you mean '{suggestion}'?" if suggestion else ""
        msg = f"Undefined symbol: '{symbol}'{hint}"
        super().__init__(msg)

    @staticmethod
    def _suggest(symbol: str) -> str | None:
        """Return the closest known name, or ``None``."""
        matches = difflib.get_close_matches(symbol, _KNOWN_NAMES, n=1, cutoff=0.6)
        return matches[0] if matches else None


class DimensionError(EvaluationError):
    """Raised on shape/dimension mismatches in matrix or vector operations."""
