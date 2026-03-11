"""Symbolic computation layer — SymPy integration.

SymPy is imported lazily to avoid slowing down cold starts in environments
where symbolic algebra is not needed.  All public functions check
``is_available()`` and raise ``ImportError`` with an actionable message if
SymPy is not installed.
"""

from __future__ import annotations

try:
    import sympy as sp

    _SYMPY_AVAILABLE: bool = True
except ImportError:
    _SYMPY_AVAILABLE = False


def is_available() -> bool:
    """Return ``True`` if SymPy is installed and importable."""
    return _SYMPY_AVAILABLE


def _require_sympy() -> None:
    if not _SYMPY_AVAILABLE:
        raise ImportError(
            "SymPy is not installed.  Run: pip install sympy"
        )


def _prep(expr_str: str) -> "sp.Expr":
    """Parse *expr_str* to a SymPy expression (caret → power)."""
    _require_sympy()
    return sp.sympify(expr_str.replace("^", "**"))


# ── Core symbolic operations ──────────────────────────────────────────

def simplify(expr_str: str) -> str:
    return str(sp.simplify(_prep(expr_str)))


def factor(expr_str: str) -> str:
    return str(sp.factor(_prep(expr_str)))


def expand(expr_str: str) -> str:
    return str(sp.expand(_prep(expr_str)))


def diff(expr_str: str, var: str = "x") -> str:
    _require_sympy()
    return str(sp.diff(_prep(expr_str), sp.Symbol(var)))


def integrate(expr_str: str, var: str = "x") -> str:
    _require_sympy()
    return str(sp.integrate(_prep(expr_str), sp.Symbol(var)))


def solve(expr_str: str, var: str = "x") -> str:
    _require_sympy()
    x = sp.Symbol(var)
    solutions = sp.solve(_prep(expr_str), x)
    return ", ".join(str(s) for s in solutions)


# ── Phase 6: Advanced symbolic operations ─────────────────────────────

def limit(expr_str: str, var: str = "x", point: str = "0") -> str:
    """Compute limit as *var* → *point*.  Use ``"oo"`` for +∞."""
    _require_sympy()
    x = sp.Symbol(var)
    return str(sp.limit(_prep(expr_str), x, sp.sympify(point)))


def series(expr_str: str, var: str = "x", point: str = "0", n: str = "6") -> str:
    """Taylor/Maclaurin series about *point* to order *n*."""
    _require_sympy()
    x = sp.Symbol(var)
    return str(sp.series(_prep(expr_str), x, sp.sympify(point), int(sp.sympify(n))))


def partial(expr_str: str, var: str = "x") -> str:
    """Partial derivative ∂f/∂var."""
    _require_sympy()
    return str(sp.diff(_prep(expr_str), sp.Symbol(var)))


def gradient_sym(expr_str: str, vars_str: str = "x,y") -> str:
    """Symbolic gradient [∂f/∂x, ∂f/∂y, …]."""
    _require_sympy()
    expr = _prep(expr_str)
    symbols = [sp.Symbol(v.strip()) for v in vars_str.split(",")]
    return "[" + ", ".join(str(sp.diff(expr, s)) for s in symbols) + "]"


def divergence(components_str: str, vars_str: str = "x,y,z") -> str:
    """Symbolic divergence ∇·F.  Components as comma-separated string."""
    _require_sympy()
    parts = [c.strip() for c in components_str.split(",")]
    names = [v.strip() for v in vars_str.split(",")]
    symbols = [sp.Symbol(n) for n in names[:len(parts)]]
    return str(sum(sp.diff(_prep(c), s) for c, s in zip(parts, symbols)))


def curl(components_str: str, vars_str: str = "x,y,z") -> str:
    """Symbolic curl ∇×F of a 3-D vector field.  Components as comma-separated string."""
    _require_sympy()
    parts = [c.strip() for c in components_str.split(",")]
    if len(parts) != 3:
        return "Error: curl requires exactly 3 components"
    names = [v.strip() for v in vars_str.split(",")]
    x, y, z = (sp.Symbol(n) for n in names[:3])
    Fx, Fy, Fz = _prep(parts[0]), _prep(parts[1]), _prep(parts[2])
    cx = sp.diff(Fz, y) - sp.diff(Fy, z)
    cy = sp.diff(Fx, z) - sp.diff(Fz, x)
    cz = sp.diff(Fy, x) - sp.diff(Fx, y)
    return f"[{cx}, {cy}, {cz}]"


def laplacian(expr_str: str, vars_str: str = "x,y") -> str:
    """Symbolic Laplacian ∇²f."""
    _require_sympy()
    expr = _prep(expr_str)
    symbols = [sp.Symbol(v.strip()) for v in vars_str.split(",")]
    return str(sum(sp.diff(expr, s, 2) for s in symbols))


def laplace_transform(expr_str: str, t_var: str = "t", s_var: str = "s") -> str:
    """Laplace transform L{f(t)}(s)."""
    _require_sympy()
    t, s = sp.Symbol(t_var), sp.Symbol(s_var)
    return str(sp.laplace_transform(_prep(expr_str), t, s, noconds=True))


def inv_laplace(expr_str: str, s_var: str = "s", t_var: str = "t") -> str:
    """Inverse Laplace transform L⁻¹{F(s)}(t)."""
    _require_sympy()
    s, t = sp.Symbol(s_var), sp.Symbol(t_var)
    return str(sp.inverse_laplace_transform(_prep(expr_str), s, t))


def taylor(expr_str: str, var: str = "x", point: str = "0", n: str = "6") -> str:
    """Taylor polynomial (without O-term)."""
    _require_sympy()
    x = sp.Symbol(var)
    s = sp.series(_prep(expr_str), x, sp.sympify(point), int(sp.sympify(n)))
    return str(s.removeO())


def summation(expr_str: str, var: str = "k", a: str = "0", b: str = "10") -> str:
    """Symbolic summation Σ."""
    _require_sympy()
    k = sp.Symbol(var)
    return str(sp.summation(_prep(expr_str), (k, sp.sympify(a), sp.sympify(b))))


def product_sym(expr_str: str, var: str = "k", a: str = "1", b: str = "10") -> str:
    """Symbolic product Π."""
    _require_sympy()
    k = sp.Symbol(var)
    return str(sp.product(_prep(expr_str), (k, sp.sympify(a), sp.sympify(b))))


def definite_integral(expr_str: str, var: str = "x", a: str = "0", b: str = "1") -> str:
    """Definite integral ∫_a^b expr dx."""
    _require_sympy()
    x = sp.Symbol(var)
    return str(sp.integrate(_prep(expr_str), (x, sp.sympify(a), sp.sympify(b))))


def nsolve_eq(expr_str: str, var: str = "x", x0: str = "1") -> str:
    """Numerical root-finding for expr = 0 near x0."""
    _require_sympy()
    x = sp.Symbol(var)
    return str(sp.nsolve(_prep(expr_str), x, float(sp.sympify(x0))))


def _parse_matrix(matrix_str: str) -> "sp.Matrix":
    """Parse GraphUG matrix notation ``[[1,2];[3,4]]`` into a SymPy Matrix."""
    _require_sympy()
    s = matrix_str.strip().replace("^", "**")
    # Strip outer brackets
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    rows = []
    for row_str in s.split(";"):
        row_str = row_str.strip()
        if row_str.startswith("[") and row_str.endswith("]"):
            row_str = row_str[1:-1]
        row_vals = [sp.sympify(v.strip()) for v in row_str.split(",")]
        rows.append(row_vals)
    return sp.Matrix(rows)


def rref(matrix_str: str) -> str:
    """Row-reduced echelon form of a matrix."""
    m = _parse_matrix(matrix_str)
    result, _ = m.rref()
    return str(result.tolist())


def nullspace(matrix_str: str) -> str:
    """Null space basis vectors."""
    m = _parse_matrix(matrix_str)
    return str([list(v) for v in m.nullspace()])


def colspace(matrix_str: str) -> str:
    """Column space basis vectors."""
    m = _parse_matrix(matrix_str)
    return str([list(v) for v in m.columnspace()])


# ---------------------------------------------------------------------------
# Lambdification helpers  (Phase 4 — graphing support)
# ---------------------------------------------------------------------------

def lambdify_expr(expr_str: str, var: str = "x"):
    """Parse *expr_str* and return a NumPy-callable ``f(var)``."""
    _require_sympy()
    import numpy as _np

    sym = sp.Symbol(var)
    expr = _prep(expr_str)
    fn = sp.lambdify(sym, expr, modules=["numpy"])
    # Wrap to guarantee ndarray output even for constants
    def _safe(v):
        result = fn(v)
        return _np.full_like(v, result, dtype=float) if _np.ndim(result) == 0 else _np.asarray(result, dtype=float)
    return _safe


def lambdify_expr_2d(expr_str: str, var_x: str = "x", var_y: str = "y"):
    """Parse *expr_str* and return a NumPy-callable ``f(x, y)``."""
    _require_sympy()
    import numpy as _np

    sx, sy = sp.Symbol(var_x), sp.Symbol(var_y)
    expr = _prep(expr_str)
    fn = sp.lambdify((sx, sy), expr, modules=["numpy"])
    def _safe(x, y):
        result = fn(x, y)
        return _np.full_like(x, result, dtype=float) if _np.ndim(result) == 0 else _np.asarray(result, dtype=float)
    return _safe


def diff_expr(expr_str: str, var: str = "x") -> str:
    """Return the symbolic derivative as a string (for display)."""
    _require_sympy()
    return str(sp.diff(_prep(expr_str), sp.Symbol(var)))


def tangent_at(expr_str: str, x0: float, var: str = "x") -> tuple[float, float]:
    """Return ``(slope, y0)`` of the tangent to *expr_str* at *x0*."""
    _require_sympy()
    sym = sp.Symbol(var)
    expr = _prep(expr_str)
    y0 = float(expr.subs(sym, x0))
    slope = float(sp.diff(expr, sym).subs(sym, x0))
    return slope, y0
