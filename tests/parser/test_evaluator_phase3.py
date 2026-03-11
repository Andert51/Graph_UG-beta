"""Phase 3 tests — grammar v0.3, evaluator hardening, canvas commands, etc.

Covers: logical operators (and/or/not), string concatenation, new builtins
        (typeof, size), canvas commands (xlabel, ylabel, title, grid),
        hold mode, help(), pretty-printing, colour cycling, combined features.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core.models.plot_command import PlotKind
from app.parser.evaluator import MathEvaluator


@pytest.fixture
def ev() -> MathEvaluator:
    return MathEvaluator()


# ---------------------------------------------------------------------------
# Logical operators
# ---------------------------------------------------------------------------


class TestLogicalOperators:
    def test_and_true(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("1 and 1").value == pytest.approx(1.0)

    def test_and_false(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("1 and 0").value == pytest.approx(0.0)

    def test_or_true(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("0 or 1").value == pytest.approx(1.0)

    def test_or_false(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("0 or 0").value == pytest.approx(0.0)

    def test_not_true(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("not 0").value == pytest.approx(1.0)

    def test_not_false(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("not 1").value == pytest.approx(0.0)

    def test_not_expression(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("not (3 == 4)").value == pytest.approx(1.0)

    def test_and_or_precedence(self, ev: MathEvaluator) -> None:
        # and binds tighter than or: 0 or (1 and 1) = 1
        assert ev.evaluate("0 or 1 and 1").value == pytest.approx(1.0)

    def test_and_or_combined(self, ev: MathEvaluator) -> None:
        # (1 and 0) or 1 = 0 or 1 = 1
        assert ev.evaluate("1 and 0 or 1").value == pytest.approx(1.0)

    def test_not_and_combined(self, ev: MathEvaluator) -> None:
        # not 0 and 1 = (not 0) and 1 = 1 and 1 = 1
        assert ev.evaluate("not 0 and 1").value == pytest.approx(1.0)

    def test_logical_with_comparison(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("3 > 2 and 5 < 10").value == pytest.approx(1.0)

    def test_logical_complex(self, ev: MathEvaluator) -> None:
        # not(3 > 5) or (2 == 2) = 1 or 1 = 1
        assert ev.evaluate("not (3 > 5) or 2 == 2").value == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# String concatenation
# ---------------------------------------------------------------------------


class TestStringConcatenation:
    def test_string_plus_string(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('"hello" + " world"')
        assert r.value == "hello world"

    def test_string_plus_number(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('"value: " + "42"')
        assert r.value == "value: 42"


# ---------------------------------------------------------------------------
# New builtins: typeof, size
# ---------------------------------------------------------------------------


class TestNewBuiltins:
    def test_typeof_float(self, ev: MathEvaluator) -> None:
        assert ev.evaluate("typeof(3.14)").value == "float"

    def test_typeof_array(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("typeof([1,2,3])")
        assert r.value == "ndarray"

    def test_typeof_string(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('typeof("hello")')
        assert r.value == "str"

    def test_size_vector(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("size([1,2,3])")
        assert r.value == (3,)

    def test_size_matrix(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("size([1,2;3,4])")
        assert r.value == (2, 2)

    def test_size_scalar(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("size(42)")
        assert r.value == ()


# ---------------------------------------------------------------------------
# Canvas commands: xlabel, ylabel, title, grid
# ---------------------------------------------------------------------------


class TestCanvasCommands:
    def test_xlabel(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('xlabel("Time (s)")')
        assert len(r.plot_commands) == 1
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.CANVAS_CMD
        assert cmd.data["cmd"] == "xlabel"
        assert cmd.data["text"] == "Time (s)"

    def test_ylabel(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('ylabel("Amplitude")')
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.CANVAS_CMD
        assert cmd.data["cmd"] == "ylabel"

    def test_title(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('title("My Plot")')
        cmd = r.plot_commands[0]
        assert cmd.data["cmd"] == "title"
        assert cmd.data["text"] == "My Plot"

    def test_grid_toggle(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("grid()")
        cmd = r.plot_commands[0]
        assert cmd.data["cmd"] == "grid"
        assert cmd.data["visible"] is None  # toggle

    def test_grid_explicit(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("grid(1)")
        cmd = r.plot_commands[0]
        assert cmd.data["visible"] is True

    def test_xlabel_requires_string(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("xlabel(42)")
        assert r.is_error

    def test_canvas_cmd_in_multiline(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('xlabel("X"); ylabel("Y")')
        assert len(r.plot_commands) == 2
        assert r.plot_commands[0].data["cmd"] == "xlabel"
        assert r.plot_commands[1].data["cmd"] == "ylabel"


# ---------------------------------------------------------------------------
# Hold mode
# ---------------------------------------------------------------------------


class TestHoldMode:
    def test_hold_toggle(self, ev: MathEvaluator) -> None:
        assert not ev.hold_mode
        ev.evaluate("hold()")
        assert ev.hold_mode
        ev.evaluate("hold()")
        assert not ev.hold_mode

    def test_hold_explicit_on(self, ev: MathEvaluator) -> None:
        ev.evaluate("hold(1)")
        assert ev.hold_mode

    def test_hold_explicit_off(self, ev: MathEvaluator) -> None:
        ev.evaluate("hold(1)")
        ev.evaluate("hold(0)")
        assert not ev.hold_mode

    def test_hold_resets_with_session(self, ev: MathEvaluator) -> None:
        ev.evaluate("hold(1)")
        ev.reset_state()
        assert not ev.hold_mode


# ---------------------------------------------------------------------------
# Help function
# ---------------------------------------------------------------------------


class TestHelp:
    def test_help_returns_text(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("help()")
        assert "GraphUG Help" in r.output_text
        assert "sin" in r.output_text
        assert "plot" in r.output_text

    def test_help_no_error(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("help()")
        assert not r.is_error


# ---------------------------------------------------------------------------
# Pretty-printing (format_value)
# ---------------------------------------------------------------------------


class TestPrettyPrinting:
    def test_integer_displayed_without_decimal(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("4.0")
        assert r.output_text == "4"

    def test_float_displayed_concisely(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("3.14159")
        assert "3.14159" in r.output_text

    def test_vector_display(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("[1,2,3]")
        # Phase 7 format: "[ 1  2  3 ]"
        assert "1" in r.output_text and "2" in r.output_text and "3" in r.output_text
        assert "[" in r.output_text

    def test_matrix_display(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("[1,2;3,4]")
        assert "2×2" in r.output_text

    def test_assignment_pretty_print(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("x = 42")
        assert "x = 42" in r.output_text
        # Should not display as x = 42.0
        assert "42.0" not in r.output_text

    def test_size_tuple_display(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("size([1,2;3,4])")
        assert "2" in r.output_text


# ---------------------------------------------------------------------------
# Combined / integration scenarios
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_plot_with_labels(self, ev: MathEvaluator) -> None:
        """A multi-line script with plot + labels + grid."""
        script = """
        x = linspace(0, 2*pi, 100)
        plot(x, sin(x))
        xlabel("Angle (rad)")
        ylabel("sin(x)")
        title("Sine Wave")
        grid(1)
        """
        r = ev.evaluate(script)
        assert not r.is_error
        plot_cmds = [c for c in r.plot_commands if c.kind == PlotKind.LINE_2D]
        canvas_cmds = [c for c in r.plot_commands if c.kind == PlotKind.CANVAS_CMD]
        assert len(plot_cmds) == 1
        assert len(canvas_cmds) == 4  # xlabel, ylabel, title, grid

    def test_hold_overlay_two_plots(self, ev: MathEvaluator) -> None:
        """Hold mode should allow overlay of multiple plots."""
        ev.evaluate("hold(1)")
        r1 = ev.evaluate("x = linspace(0, 6, 50); plot(x, sin(x))")
        r2 = ev.evaluate("plot(x, cos(x))")
        assert not r1.is_error
        assert not r2.is_error
        assert len(r1.plot_commands) == 1
        assert len(r2.plot_commands) == 1

    def test_logical_assignment(self, ev: MathEvaluator) -> None:
        """Assign a logical result to a variable."""
        ev.evaluate("a = 3 > 2 and 5 < 10")
        r = ev.evaluate("a")
        assert r.value == pytest.approx(1.0)

    def test_full_workflow(self, ev: MathEvaluator) -> None:
        """Simulates a typical user session."""
        ev.evaluate("a = 5")
        ev.evaluate("b = a ^ 2")
        r = ev.evaluate("b")
        assert r.value == pytest.approx(25.0)
        r = ev.evaluate("b > 20 and b < 30")
        assert r.value == pytest.approx(1.0)
        r = ev.evaluate("typeof(b)")
        assert r.value == "float"
