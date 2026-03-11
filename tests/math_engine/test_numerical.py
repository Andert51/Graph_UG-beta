"""Unit tests for the numerical math engine helper functions."""

from __future__ import annotations

import numpy as np
import pytest

from app.math_engine.numerical import arange, cross, dot, linspace, norm


class TestLinspace:
    def test_count(self) -> None:
        arr = linspace(0.0, 1.0, 5)
        assert len(arr) == 5

    def test_endpoints(self) -> None:
        arr = linspace(0.0, 10.0, 11)
        np.testing.assert_allclose(arr[0], 0.0)
        np.testing.assert_allclose(arr[-1], 10.0)

    def test_float_num_coercion(self) -> None:
        # 5.9 should be truncated to 5
        arr = linspace(0.0, 1.0, 5.9)  # type: ignore[arg-type]
        assert len(arr) == 5


class TestArange:
    def test_basic(self) -> None:
        arr = arange(0.0, 5.0, 1.0)
        np.testing.assert_array_equal(arr, [0.0, 1.0, 2.0, 3.0, 4.0])

    def test_float_step(self) -> None:
        arr = arange(0.0, 1.0, 0.5)
        np.testing.assert_allclose(arr, [0.0, 0.5])


class TestNorm:
    def test_l2_norm(self) -> None:
        v = np.array([3.0, 4.0])
        assert norm(v) == pytest.approx(5.0)

    def test_l1_norm(self) -> None:
        v = np.array([1.0, -2.0, 3.0])
        assert norm(v, order=1) == pytest.approx(6.0)


class TestDot:
    def test_orthogonal(self) -> None:
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert dot(a, b) == pytest.approx(0.0)

    def test_parallel(self) -> None:
        a = np.array([2.0, 0.0])
        b = np.array([3.0, 0.0])
        assert dot(a, b) == pytest.approx(6.0)


class TestCross:
    def test_z_axis(self) -> None:
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        result = cross(a, b)
        np.testing.assert_allclose(result, [0.0, 0.0, 1.0])
