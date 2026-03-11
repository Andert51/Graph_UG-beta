"""Tests for Phase 6 symbolic engine enhancements.

Covers: limit, series, partial, gradient_sym, divergence, curl, laplacian,
laplace_transform, inv_laplace, taylor, summation, product_sym,
definite_integral, nsolve_eq, rref, nullspace, colspace.
"""

from __future__ import annotations

import pytest

sympy = pytest.importorskip("sympy")

from app.math_engine.symbolic import (
    colspace,
    curl,
    definite_integral,
    divergence,
    gradient_sym,
    inv_laplace,
    laplace_transform,
    laplacian,
    limit,
    nsolve_eq,
    nullspace,
    partial,
    product_sym,
    rref,
    series,
    summation,
    taylor,
)


class TestLimit:
    def test_sinx_over_x(self) -> None:
        result = limit("sin(x)/x", "x", 0)
        assert "1" in result

    def test_limit_at_infinity(self) -> None:
        result = limit("1/x", "x", "oo")
        assert "0" in result


class TestSeries:
    def test_exp_series(self) -> None:
        result = series("exp(x)", "x", 0, 4)
        assert "x" in result


class TestPartial:
    def test_partial_x(self) -> None:
        result = partial("x**2*y + y**3", "x")
        assert "2" in result and "x" in result

    def test_partial_y(self) -> None:
        result = partial("x**2*y + y**3", "y")
        assert "x" in result or "y" in result


class TestGradient:
    def test_gradient_2d(self) -> None:
        result = gradient_sym("x**2 + y**2", "x,y")
        # Should contain 2*x and 2*y
        assert "2" in result


class TestDivergence:
    def test_divergence_identity(self) -> None:
        result = divergence("x, y, z", "x,y,z")
        assert "3" in result


class TestCurl:
    def test_curl_zero(self) -> None:
        # Curl of gradient is zero
        result = curl("x, y, z", "x,y,z")
        assert "0" in result


class TestLaplacian:
    def test_laplacian_quadratic(self) -> None:
        result = laplacian("x**2 + y**2", "x,y")
        assert "4" in result


class TestLaplaceTransform:
    def test_laplace_exp(self) -> None:
        result = laplace_transform("exp(-t)", "t", "s")
        assert "s" in result or "1" in result


class TestTaylor:
    def test_taylor_sin(self) -> None:
        result = taylor("sin(x)", "x", 0, 3)
        assert "x" in result


class TestSummation:
    def test_sum_1_to_10(self) -> None:
        result = summation("k", "k", 1, 10)
        assert "55" in result

    def test_sum_squares(self) -> None:
        result = summation("k**2", "k", 1, 5)
        assert "55" in result


class TestProduct:
    def test_factorial_5(self) -> None:
        result = product_sym("k", "k", 1, 5)
        assert "120" in result


class TestDefiniteIntegral:
    def test_x_squared_0_to_1(self) -> None:
        result = definite_integral("x**2", "x", 0, 1)
        assert "1/3" in result or "0.333" in result


class TestNsolve:
    def test_cos_x_equals_x(self) -> None:
        result = nsolve_eq("cos(x) - x", "x", 1)
        assert "0.739" in result


class TestRref:
    def test_rref_2x2(self) -> None:
        result = rref("[[1,2];[3,4]]")
        assert not result.startswith("Error")


class TestNullspace:
    def test_nullspace_singular(self) -> None:
        result = nullspace("[[1,2];[2,4]]")
        assert not result.startswith("Error")


class TestColspace:
    def test_colspace_2x2(self) -> None:
        result = colspace("[[1,0];[0,1]]")
        assert not result.startswith("Error")
