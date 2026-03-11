"""Unit tests for MathEvaluator — the core parsing and evaluation pipeline.

These tests cover:
- Basic arithmetic operators and precedence
- Variable assignment and recall
- Built-in function calls (sin, sqrt, linspace)
- Vector (array) literals
- Multi-line input
- Error handling: syntax, undefined symbols, division by zero
- Plot command generation (plot() calls)
- Session reset
"""

from __future__ import annotations

import numpy as np
import pytest

from app.parser.evaluator import MathEvaluator


@pytest.fixture
def ev() -> MathEvaluator:
    """Fresh evaluator for each test (no shared state)."""
    return MathEvaluator()


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


class TestArithmetic:
    def test_addition(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("1 + 2").value == pytest.approx(3.0)

    def test_subtraction(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("10 - 3").value == pytest.approx(7.0)

    def test_multiplication(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("4 * 5").value == pytest.approx(20.0)

    def test_division(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("9 / 4").value == pytest.approx(2.25)

    def test_power(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("2^10").value == pytest.approx(1024.0)

    def test_unary_negation(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("-5").value == pytest.approx(-5.0)

    def test_nested_precedence(self, ev: MathEvaluator) -> None:
        # 2 + 3 * 4 = 14 (not 20)
        assert ev.evaluate("2 + 3 * 4").value == pytest.approx(14.0)

    def test_right_assoc_power(self, ev: MathEvaluator) -> None:
        # 2^3^2 = 2^(3^2) = 2^9 = 512
        assert ev.evaluate("2^3^2").value == pytest.approx(512.0)

    def test_parentheses(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("(2 + 3) * 4").value == pytest.approx(20.0)

    def test_division_by_zero_captured(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("1 / 0")
        assert result.is_error

    def test_float_literal(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("3.14").value == pytest.approx(3.14)

    def test_scientific_notation(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("1e3").value == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------


class TestVariables:
    def test_assignment_and_recall(self, ev: MathEvaluator) -> None:
        ev.evaluate("x = 42")
        assert ev.evaluate("x").value == pytest.approx(42.0)

    def test_expression_assignment(self, ev: MathEvaluator) -> None:
        ev.evaluate("a = 3")
        ev.evaluate("b = 4")
        ev.evaluate("c = a^2 + b^2")
        assert ev.evaluate("c").value == pytest.approx(25.0)

    def test_undefined_symbol_is_error(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("unknown_var")
        assert result.is_error
        assert "undefined" in result.error.lower()  # type: ignore[union-attr]

    def test_reset_clears_variables(self, ev: MathEvaluator) -> None:
        ev.evaluate("x = 99")
        ev.reset_state()
        result = ev.evaluate("x")
        assert result.is_error

    def test_cannot_overwrite_builtin(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("sin = 1")
        assert result.is_error


# ---------------------------------------------------------------------------
# Built-in functions
# ---------------------------------------------------------------------------


class TestBuiltins:
    def test_sin(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("sin(0)")
        assert result.value == pytest.approx(0.0)

    def test_cos(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("cos(0)").value == pytest.approx(1.0)

    def test_sqrt(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("sqrt(16)").value == pytest.approx(4.0)

    def test_pi_constant(self, ev: MathEvaluator) -> None:
        import math
        assert ev.evaluate("pi").value == pytest.approx(math.pi)

    def test_linspace_float_coercion(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("linspace(0, 1, 5)")
        assert len(result.value) == 5

    def test_unknown_function_is_error(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("no_such_func(1, 2)")
        assert result.is_error


# ---------------------------------------------------------------------------
# Vectors
# ---------------------------------------------------------------------------


class TestVectors:
    def test_vector_literal(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("[1, 2, 3]")
        np.testing.assert_array_equal(result.value, [1.0, 2.0, 3.0])

    def test_nested_expression_in_vector(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("[1 + 1, 2 * 3]")
        np.testing.assert_array_equal(result.value, [2.0, 6.0])

    def test_empty_vector(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("[]")
        assert result.value is not None
        assert len(result.value) == 0


# ---------------------------------------------------------------------------
# Multi-line input
# ---------------------------------------------------------------------------


class TestMultiLine:
    def test_two_statements(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("x = 10\nx * 2")
        assert result.value == pytest.approx(20.0)

    def test_comment_lines_skipped(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("# this is a comment\n5 + 5")
        assert result.value == pytest.approx(10.0)

    def test_blank_lines_skipped(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("\n\n3 * 3\n\n")
        assert result.value == pytest.approx(9.0)

    def test_error_on_second_line_returned(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("x = 1\n@@@")
        assert result.is_error


# ---------------------------------------------------------------------------
# Plot commands
# ---------------------------------------------------------------------------


class TestPlotCommands:
    def test_plot_1d_produces_command(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("plot([0, 1, 2])")
        assert result.has_plot
        assert not result.is_error
        np.testing.assert_array_equal(result.plot_commands[0].data["y"], [0.0, 1.0, 2.0])
        # x should be auto-generated as [0, 1, 2]
        np.testing.assert_array_equal(result.plot_commands[0].data["x"], [0.0, 1.0, 2.0])

    def test_plot_2d_produces_command(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("plot([0, 1], [0, 1])")
        assert result.has_plot
        np.testing.assert_array_equal(result.plot_commands[0].data["x"], [0.0, 1.0])
        np.testing.assert_array_equal(result.plot_commands[0].data["y"], [0.0, 1.0])

    def test_plot_wrong_arity_is_error(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("plot()")
        assert result.is_error


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_string(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("")
        assert not result.is_error
        assert result.value is None

    def test_whitespace_only(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("   \n  ")
        assert not result.is_error

    def test_syntax_error_captured(self, ev: MathEvaluator) -> None:
        result = ev.evaluate("@@@")
        assert result.is_error
        assert result.error is not None
