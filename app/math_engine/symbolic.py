"""Symbolic computation layer — SymPy integration (Phase 2 placeholder).

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


def simplify(expr_str: str) -> str:
    """Parse *expr_str* as a SymPy expression and return its simplified form."""
    _require_sympy()
    expr = sp.sympify(expr_str)
    return str(sp.simplify(expr))


def diff(expr_str: str, var: str = "x") -> str:
    """Differentiate *expr_str* with respect to *var*."""
    _require_sympy()
    x = sp.Symbol(var)
    expr = sp.sympify(expr_str)
    return str(sp.diff(expr, x))


def integrate(expr_str: str, var: str = "x") -> str:
    """Indefinitely integrate *expr_str* with respect to *var*."""
    _require_sympy()
    x = sp.Symbol(var)
    expr = sp.sympify(expr_str)
    return str(sp.integrate(expr, x))
