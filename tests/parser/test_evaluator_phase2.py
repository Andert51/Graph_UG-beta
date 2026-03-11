"""Extended tests for Phase 2 evaluator features.

Covers: modulo, comparisons, matrices, semicolons, string literals,
        symbolic functions, new builtins, new plot commands.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.parser.evaluator import MathEvaluator
from app.core.models.plot_command import PlotKind


@pytest.fixture
def ev() -> MathEvaluator:
    return MathEvaluator()


# ---------------------------------------------------------------------------
# Modulo operator
# ---------------------------------------------------------------------------


class TestModulo:
    def test_basic_modulo(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("10 % 3").value == pytest.approx(1.0)

    def test_float_modulo(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("7.5 % 2").value == pytest.approx(1.5)

    def test_modulo_precedence(self, ev: MathEvaluator) -> None:
        # % has same precedence as * and /
        # 10 + 7 % 3 = 10 + 1 = 11
        assert ev.evaluate("10 + 7 % 3").value == pytest.approx(11.0)


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------


class TestComparisons:
    def test_eq_true(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("3 == 3").value == pytest.approx(1.0)

    def test_eq_false(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("3 == 4").value == pytest.approx(0.0)

    def test_ne(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("3 != 4").value == pytest.approx(1.0)

    def test_lt(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("2 < 5").value == pytest.approx(1.0)

    def test_gt(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("5 > 2").value == pytest.approx(1.0)

    def test_le(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("3 <= 3").value == pytest.approx(1.0)

    def test_ge(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("4 >= 5").value == pytest.approx(0.0)

    def test_comparison_with_expressions(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("2 + 1 == 3").value == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Matrix literals
# ---------------------------------------------------------------------------


class TestMatrices:
    def test_2x2_matrix(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("[1, 2; 3, 4]")
        expected = np.array([[1. ,2.], [3., 4.]])
        np.testing.assert_array_equal(result.value, expected)

    def test_3x3_matrix(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("[1, 0, 0; 0, 1, 0; 0, 0, 1]")
        np.testing.assert_array_equal(result.value, np.eye(3))

    def test_matrix_row_mismatch_error(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("[1, 2; 3]")
        assert result.is_error
        assert "mismatch" in result.error.lower()

    def test_matrix_with_expressions(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("[1+1, 2*3; 4, 5^2]")
        expected = np.array([[2., 6.], [4., 25.]])
        np.testing.assert_array_equal(result.value, expected)

    def test_det_of_identity(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("det([1,0; 0,1])").value == pytest.approx(1.0)

    def test_det_of_2x2(self, ev: MathEvaluator) -> None:
        # det([1,2; 3,4]) = 1*4 - 2*3 = -2
        assert ev.evaluate("det([1,2; 3,4])").value == pytest.approx(-2.0)

    def test_inv_2x2(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("inv([1,0; 0,2])")
        expected = np.array([[1., 0.], [0., 0.5]])
        np.testing.assert_array_almost_equal(result.value, expected)

    def test_transpose(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("transpose([1,2; 3,4])")
        expected = np.array([[1., 3.], [2., 4.]])
        np.testing.assert_array_equal(result.value, expected)

    def test_matrix_assigned_to_variable(self, ev: MathEvaluator) -> None:
        ev.evaluate("m = [1,2; 3,4]")
        result = ev.evaluate("det(m)")
        assert result.value == pytest.approx(-2.0)


# ---------------------------------------------------------------------------
# Semicolons (statement separation)
# ---------------------------------------------------------------------------


class TestSemicolons:
    def test_inline_semicolons(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("a = 5; b = 3; a + b")
        assert result.value == pytest.approx(8.0)

    def test_semicolons_inside_brackets_not_split(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("[1, 2; 3, 4]")
        assert result.value is not None
        assert result.value.shape == (2, 2)

    def test_semicolons_mixed_with_matrix(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("m = [1,0; 0,1]; det(m)")
        assert result.value == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# String literals
# ---------------------------------------------------------------------------


class TestStringLiterals:
    def test_double_quoted_string(self, ev: MathEvaluator) -> None:
        result = ev.evaluate('"hello"')
        assert result.value == "hello"

    def test_single_quoted_string(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("'world'")
        assert result.value == "world"


# ---------------------------------------------------------------------------
# Symbolic algebra
# ---------------------------------------------------------------------------


class TestSymbolic:
    def test_diff_polynomial(self, ev: MathEvaluator) -> None:
        result = ev.evaluate('diff("x**3 + 2*x", "x")')
        assert "3*x**2" in result.output_text
        assert "2" in result.output_text

    def test_integrate_polynomial(self, ev: MathEvaluator) -> None:
        result = ev.evaluate('integrate("x**2", "x")')
        assert "x**3/3" in result.output_text

    def test_simplify_trig(self, ev: MathEvaluator) -> None:
        result = ev.evaluate('simplify("sin(x)**2 + cos(x)**2")')
        assert result.output_text.strip() == "1"

    def test_factor(self, ev: MathEvaluator) -> None:
        result = ev.evaluate('factor("x**2 - 1")')
        assert "(x - 1)" in result.output_text
        assert "(x + 1)" in result.output_text

    def test_expand(self, ev: MathEvaluator) -> None:
        result = ev.evaluate('expand("(x + 1)**2")')
        assert "x**2" in result.output_text

    def test_solve_quadratic(self, ev: MathEvaluator) -> None:
        result = ev.evaluate('solve("x**2 - 4", "x")')
        assert "-2" in result.output_text
        assert "2" in result.output_text

    def test_diff_default_var(self, ev: MathEvaluator) -> None:
        result = ev.evaluate('diff("sin(x)")')
        assert "cos(x)" in result.output_text

    def test_symbolic_non_string_error(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("diff(3)")
        assert result.is_error


# ---------------------------------------------------------------------------
# New builtins
# ---------------------------------------------------------------------------


class TestNewBuiltins:
    def test_sinh(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("sinh(0)").value == pytest.approx(0.0)

    def test_cosh(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("cosh(0)").value == pytest.approx(1.0)

    def test_tanh(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("tanh(0)").value == pytest.approx(0.0)

    def test_ceil(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("ceil(2.3)").value == pytest.approx(3.0)

    def test_floor(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("floor(2.7)").value == pytest.approx(2.0)

    def test_round(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("round(2.567)").value == pytest.approx(3.0)

    def test_eye(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("eye(3)")
        np.testing.assert_array_equal(result.value, np.eye(3))

    def test_zeros(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("zeros(3)")
        np.testing.assert_array_equal(result.value, np.zeros(3))

    def test_ones(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("ones(4)")
        np.testing.assert_array_equal(result.value, np.ones(4))

    def test_norm(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("norm([3, 4])").value == pytest.approx(5.0)

    def test_dot_product(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("dot([1, 2], [3, 4])")
        assert result.value == pytest.approx(11.0)

    def test_cross_product(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("cross([1, 0, 0], [0, 1, 0])")
        np.testing.assert_array_equal(result.value, [0., 0., 1.])

    def test_sum(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("sum([1, 2, 3])").value == pytest.approx(6.0)

    def test_mean(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("mean([2, 4, 6])").value == pytest.approx(4.0)

    def test_len(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("len([1, 2, 3, 4])").value == pytest.approx(4.0)

    def test_abs(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("abs(-7)").value == pytest.approx(7.0)

    def test_log2(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("log2(8)").value == pytest.approx(3.0)

    def test_log10(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("log10(1000)").value == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# New plot commands
# ---------------------------------------------------------------------------


class TestNewPlotCommands:
    def test_scatter(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("scatter([1,2,3], [4,5,6])")
        assert result.has_plot
        assert result.plot_commands[0].kind == PlotKind.SCATTER

    def test_vector_2d(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("vector(3, 4)")
        assert result.has_plot
        assert result.plot_commands[0].kind == PlotKind.VECTOR_2D

    def test_vector_with_origin(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("vector(1, 1, 3, 4)")
        assert result.has_plot
        cmd = result.plot_commands[0]
        assert cmd.data["x0"] == pytest.approx(1.0)
        assert cmd.data["y0"] == pytest.approx(1.0)

    def test_bar(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("bar([1, 2, 3, 4])")
        assert result.has_plot
        assert result.plot_commands[0].kind == PlotKind.BAR

    def test_bar_with_x(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("bar([10, 20, 30], [5, 10, 15])")
        assert result.has_plot

    def test_hist(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("hist([1, 2, 2, 3, 3, 3])")
        assert result.has_plot
        assert result.plot_commands[0].kind == PlotKind.HISTOGRAM

    def test_hist_with_bins(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("hist([1, 2, 3, 4, 5], 3)")
        assert result.has_plot
        assert result.plot_commands[0].data["bins"] == 3


# ---------------------------------------------------------------------------
# Unary +
# ---------------------------------------------------------------------------


class TestUnaryPlus:
    def test_unary_plus(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("+5").value == pytest.approx(5.0)

    def test_unary_plus_expression(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("+(3 + 4)").value == pytest.approx(7.0)
