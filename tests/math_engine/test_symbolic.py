"""Tests for the SymPy symbolic computation layer."""

from __future__ import annotations

import pytest

from app.math_engine.symbolic import (
    diff,
    expand,
    factor,
    integrate,
    is_available,
    simplify,
    solve,
)


@pytest.mark.skipif(not is_available(), reason="SymPy not installed")
class TestSymbolic:
    def test_simplify_trig_identity(self) -> None:
        assert simplify("sin(x)**2 + cos(x)**2") == "1"

    def test_factor_difference_of_squares(self) -> None:
        result = factor("x**2 - 1")
        assert result == "(x - 1)*(x + 1)"

    def test_expand_product(self) -> None:
        result = expand("(x + 1)*(x - 1)")
        assert "x**2" in result
        assert "- 1" in result

    def test_diff_power(self) -> None:
        assert diff("x**3", "x") == "3*x**2"

    def test_diff_sin(self) -> None:
        assert diff("sin(x)", "x") == "cos(x)"

    def test_integrate_power(self) -> None:
        assert integrate("x**2", "x") == "x**3/3"

    def test_integrate_cos(self) -> None:
        assert integrate("cos(x)", "x") == "sin(x)"

    def test_solve_linear(self) -> None:
        result = solve("x - 5", "x")
        assert "5" in result

    def test_solve_quadratic(self) -> None:
        result = solve("x**2 - 9", "x")
        assert "-3" in result
        assert "3" in result

    def test_diff_default_var(self) -> None:
        # Default variable is x
        assert diff("x**2") == "2*x"
