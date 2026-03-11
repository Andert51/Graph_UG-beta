"""Tests for the symbolic module — Phase 4 lambdify and calculus helpers."""

from __future__ import annotations

import numpy as np
import pytest

from app.math_engine.symbolic import (
    diff_expr,
    lambdify_expr,
    lambdify_expr_2d,
    tangent_at,
)


class TestLambdifyExpr:
    def test_sin(self) -> None:
        fn = lambdify_expr("sin(x)")
        x = np.array([0.0, np.pi / 2, np.pi])
        y = fn(x)
        assert y[0] == pytest.approx(0.0, abs=1e-10)
        assert y[1] == pytest.approx(1.0, abs=1e-10)
        assert y[2] == pytest.approx(0.0, abs=1e-10)

    def test_polynomial(self) -> None:
        fn = lambdify_expr("x^2 + 2*x + 1")
        assert fn(np.array([0.0]))[0] == pytest.approx(1.0)
        assert fn(np.array([1.0]))[0] == pytest.approx(4.0)

    def test_constant(self) -> None:
        fn = lambdify_expr("5")
        x = np.linspace(-1, 1, 10)
        y = fn(x)
        assert np.allclose(y, 5.0)

    def test_exp(self) -> None:
        fn = lambdify_expr("exp(x)")
        assert fn(np.array([0.0]))[0] == pytest.approx(1.0)


class TestLambdifyExpr2D:
    def test_basic(self) -> None:
        fn = lambdify_expr_2d("x + y")
        assert fn(np.array([1.0]), np.array([2.0]))[0] == pytest.approx(3.0)

    def test_product(self) -> None:
        fn = lambdify_expr_2d("x * y")
        assert fn(np.array([3.0]), np.array([4.0]))[0] == pytest.approx(12.0)

    def test_grid(self) -> None:
        fn = lambdify_expr_2d("x^2 + y^2")
        X, Y = np.meshgrid(np.array([0, 1]), np.array([0, 1]))
        Z = fn(X, Y)
        assert Z[0, 0] == pytest.approx(0.0)  # 0² + 0²
        assert Z[1, 1] == pytest.approx(2.0)  # 1² + 1²


class TestDiffExpr:
    def test_polynomial(self) -> None:
        result = diff_expr("x^3")
        assert "3*x**2" in result

    def test_sin(self) -> None:
        result = diff_expr("sin(x)")
        assert "cos" in result

    def test_with_var(self) -> None:
        result = diff_expr("t^2", var="t")
        assert "2*t" in result


class TestTangentAt:
    def test_quadratic_at_origin(self) -> None:
        slope, y0 = tangent_at("x^2", 0)
        assert slope == pytest.approx(0.0)
        assert y0 == pytest.approx(0.0)

    def test_quadratic_at_2(self) -> None:
        slope, y0 = tangent_at("x^2", 2)
        assert slope == pytest.approx(4.0)
        assert y0 == pytest.approx(4.0)

    def test_sin_at_zero(self) -> None:
        slope, y0 = tangent_at("sin(x)", 0)
        assert slope == pytest.approx(1.0, abs=1e-10)
        assert y0 == pytest.approx(0.0, abs=1e-10)
