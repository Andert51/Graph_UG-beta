"""Tests for Phase 5 enhancements.

Covers: variable substitution in plot strings, equation graphing (y = f(x)
auto-plot), improved error messages, completer token list, insert plot dialog.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.core.models.plot_command import PlotKind
from app.parser.evaluator import MathEvaluator


@pytest.fixture()
def ev() -> MathEvaluator:
    return MathEvaluator()


# ══════════════════════════════════════════════════════════════════════
# Variable substitution in plot expression strings
# ══════════════════════════════════════════════════════════════════════


class TestVariableSubstitution:
    """After ``a = 2``, ``fplot("a*x^2")`` should substitute a=2."""

    def test_fplot_with_user_var(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('a = 3\nfplot("a*x^2", 0, 1, 50)')
        assert not r.is_error
        cmd = r.plot_commands[0]
        # At x=1, y should be 3*1^2 = 3
        assert cmd.data["y"][-1] == pytest.approx(3.0, rel=0.01)

    def test_fplot_no_overwrite_x(self, ev: MathEvaluator) -> None:
        """Variable 'x' itself should not be substituted (it's the free var)."""
        ev.evaluate("x = 999")
        r = ev.evaluate('fplot("sin(x)", 0, 3.14, 50)')
        assert not r.is_error
        # The fplot should still sweep x over [0, 3.14], not use x=999
        cmd = r.plot_commands[0]
        assert len(cmd.data["x"]) == 50
        assert cmd.data["x"][0] == pytest.approx(0.0)

    def test_polar_with_user_var(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('k = 2\npolar("k*cos(t)", 0, 6.28)')
        assert not r.is_error

    def test_surface_with_user_var(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('c = 1\nsurface("c*sin(x)*cos(y)", -3, 3, -3, 3)')
        assert not r.is_error
        assert r.plot_commands[0].kind == PlotKind.SURFACE_3D

    def test_symbolic_with_user_var(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('a = 2\nsimplify("a*x + a*x")')
        assert not r.is_error
        # After substitution: simplify("(2)*x + (2)*x") → 4*x
        assert "4*x" in r.output_text

    def test_plotderiv_with_user_var(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('c = 3\nplotderiv("c*x^2", -2, 2)')
        assert not r.is_error
        assert len(r.plot_commands) == 2  # original + derivative

    def test_implicit_with_user_var(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('r = 2\nimplicit("x^2 + y^2 - r^2")')
        assert not r.is_error
        assert r.plot_commands[0].kind == PlotKind.IMPLICIT_2D


# ══════════════════════════════════════════════════════════════════════
# Equation graphing — y = f(x) auto-plot
# ══════════════════════════════════════════════════════════════════════


class TestEquationGraphing:
    """Assigning y = f(x) where x is a matching 1-D array should auto-plot."""

    def test_y_equals_sin_x_autoplots(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("x = linspace(0, 6.28, 100)\ny = sin(x)")
        assert not r.is_error
        assert any(c.kind == PlotKind.LINE_2D for c in r.plot_commands)
        cmd = [c for c in r.plot_commands if c.kind == PlotKind.LINE_2D][0]
        assert len(cmd.data["x"]) == 100
        assert "auto-plotted" in r.output_text

    def test_y_equals_scalar_no_autoplot(self, ev: MathEvaluator) -> None:
        """Assigning y to a scalar should NOT auto-plot."""
        r = ev.evaluate("y = 5")
        assert not r.is_error
        assert len(r.plot_commands) == 0
        assert "auto-plotted" not in r.output_text

    def test_y_equals_no_x_in_scope(self, ev: MathEvaluator) -> None:
        """Without x in scope, no auto-plot should happen."""
        r = ev.evaluate("t = linspace(0, 10, 50)\ny = sin(t)")
        assert not r.is_error
        # y is assigned but x is not present, so no auto-plot
        # (unless x happens to be from a prior scope — reset ensures clean)
        assert len(r.plot_commands) == 0

    def test_y_equals_complex_expression(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("x = linspace(-5, 5, 200)\ny = x^2 - 3*x + 1")
        assert not r.is_error
        assert any(c.kind == PlotKind.LINE_2D for c in r.plot_commands)


# ══════════════════════════════════════════════════════════════════════
# Improved error messages
# ══════════════════════════════════════════════════════════════════════


class TestImprovedErrors:
    def test_undefined_symbol_suggestion(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("sni(1)")
        assert r.is_error
        # Should suggest "sin"
        assert "sin" in r.error

    def test_undefined_symbol_no_match(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("zzzzz")
        assert r.is_error
        assert "Undefined symbol" in r.error

    def test_error_shows_statement(self, ev: MathEvaluator) -> None:
        """Error messages should show the offending statement."""
        r = ev.evaluate("fplot(123)")
        assert r.is_error
        assert "fplot(123)" in r.error

    def test_division_by_zero_hint(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("1/0")
        assert r.is_error
        assert "zero" in r.error.lower()

    def test_fplot_bad_arg_verbose(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("fplot(42)")
        assert r.is_error
        assert "string" in r.error.lower()
        assert "Usage" in r.error or "fplot" in r.error

    def test_scatter_wrong_args_verbose(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("scatter(1, 2, 3)")
        assert r.is_error
        assert "scatter" in r.error.lower()

    def test_vector_wrong_args_verbose(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("vector(1)")
        assert r.is_error
        assert "vector" in r.error.lower()

    def test_parse_error_has_hint(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("1 +")
        assert r.is_error
        assert "Hint" in r.error or "SyntaxError" in r.error


# ══════════════════════════════════════════════════════════════════════
# Completer token list
# ══════════════════════════════════════════════════════════════════════


class TestCompleterTokens:
    def test_completions_contain_all_builtins(self) -> None:
        from app.gui.widgets.completer import COMPLETIONS

        for name in ["sin", "cos", "fplot", "surface", "parametric3d",
                      "slopefield", "linspace", "help", "pi"]:
            assert name in COMPLETIONS

    def test_completions_sorted(self) -> None:
        from app.gui.widgets.completer import COMPLETIONS

        assert COMPLETIONS == sorted(COMPLETIONS)


# ══════════════════════════════════════════════════════════════════════
# Insert Plot Dialog templates
# ══════════════════════════════════════════════════════════════════════


class TestInsertPlotTemplates:
    def test_fplot_template(self) -> None:
        from app.gui.dialogs.insert_plot_dialog import _TEMPLATES

        t = _TEMPLATES["fplot — Function Plot"]
        result = t["format"](["sin(x)", "-10", "10"])
        assert result == 'fplot("sin(x)", -10, 10)'

    def test_polar_template(self) -> None:
        from app.gui.dialogs.insert_plot_dialog import _TEMPLATES

        t = _TEMPLATES["polar — Polar Plot"]
        result = t["format"](["2*cos(t)", "0", "2*pi"])
        assert result == 'polar("2*cos(t)", 0, 2*pi)'

    def test_surface_template(self) -> None:
        from app.gui.dialogs.insert_plot_dialog import _TEMPLATES

        t = _TEMPLATES["surface — 3D Surface"]
        result = t["format"](["sin(x)*cos(y)", "-5", "5", "-5", "5"])
        assert result == 'surface("sin(x)*cos(y)", -5, 5, -5, 5)'

    def test_tangentline_template(self) -> None:
        from app.gui.dialogs.insert_plot_dialog import _TEMPLATES

        t = _TEMPLATES["tangentline — Tangent Line"]
        result = t["format"](["x^2", "1"])
        assert result == 'tangentline("x^2", 1)'

    def test_all_templates_callable(self) -> None:
        from app.gui.dialogs.insert_plot_dialog import _TEMPLATES

        for name, tmpl in _TEMPLATES.items():
            defaults = [f[1] for f in tmpl["fields"]]
            result = tmpl["format"](defaults)
            assert isinstance(result, str)
            assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════
# Parse errors module
# ══════════════════════════════════════════════════════════════════════


class TestParseErrors:
    def test_undefined_symbol_did_you_mean(self) -> None:
        from app.core.exceptions.parse_errors import UndefinedSymbolError

        err = UndefinedSymbolError("cosn")
        assert "cos" in str(err)

    def test_undefined_symbol_no_suggestion(self) -> None:
        from app.core.exceptions.parse_errors import UndefinedSymbolError

        err = UndefinedSymbolError("xyzzy123")
        assert "Undefined symbol" in str(err)

    def test_parse_error_includes_hint(self) -> None:
        from app.core.exceptions.parse_errors import ParseError

        err = ParseError("unexpected token", line=3, column=5)
        s = str(err)
        assert "line 3" in s
        assert "col 5" in s
        assert "Hint" in s
