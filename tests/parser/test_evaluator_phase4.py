"""Tests for Phase 4 evaluator features — advanced graphing commands.

Covers: fplot, polar, parametric, parametric3d, surface, wireframe,
        plotderiv, plotintegral, tangentline, implicit, contour, slopefield.
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


# ── fplot ─────────────────────────────────────────────────────────────


class TestFplot:
    def test_fplot_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('fplot("sin(x)")')
        assert not r.is_error
        assert len(r.plot_commands) == 1
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.LINE_2D
        assert "x" in cmd.data and "y" in cmd.data
        assert len(cmd.data["x"]) == 500  # default sample count

    def test_fplot_with_range(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('fplot("x^2", -5, 5)')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.data["x"][0] == pytest.approx(-5.0)
        assert cmd.data["x"][-1] == pytest.approx(5.0)

    def test_fplot_with_samples(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('fplot("x^2", 0, 1, 100)')
        assert not r.is_error
        assert len(r.plot_commands[0].data["x"]) == 100

    def test_fplot_constant(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('fplot("5")')
        assert not r.is_error
        y = r.plot_commands[0].data["y"]
        assert np.allclose(y, 5.0)

    def test_fplot_no_string_error(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("fplot(42)")
        assert r.is_error
        assert "string" in r.error.lower()

    def test_fplot_label(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('fplot("cos(x)")')
        assert r.plot_commands[0].label == "cos(x)"


# ── polar ─────────────────────────────────────────────────────────────


class TestPolar:
    def test_polar_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('polar("2*cos(t)")')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.LINE_2D
        assert len(cmd.data["x"]) == 500

    def test_polar_with_range(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('polar("1+sin(t)", 0, 6.28)')
        assert not r.is_error
        assert r.plot_commands[0].kind == PlotKind.LINE_2D

    def test_polar_circle(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('polar("3")')
        assert not r.is_error
        x, y = r.plot_commands[0].data["x"], r.plot_commands[0].data["y"]
        # All points should be ~3 from origin
        radii = np.sqrt(x**2 + y**2)
        assert np.allclose(radii, 3.0, atol=0.01)

    def test_polar_no_string_error(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("polar(42)")
        assert r.is_error


# ── parametric 2D ─────────────────────────────────────────────────────


class TestParametric:
    def test_parametric_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('parametric("cos(t)", "sin(t)")')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.LINE_2D
        # Should approximate a unit circle
        x, y = cmd.data["x"], cmd.data["y"]
        radii = np.sqrt(x**2 + y**2)
        assert np.allclose(radii, 1.0, atol=0.01)

    def test_parametric_with_range(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('parametric("cos(t)", "sin(t)", 0, 3.14)')
        assert not r.is_error

    def test_parametric_error_one_arg(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('parametric("cos(t)")')
        assert r.is_error

    def test_parametric_label(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('parametric("cos(t)", "sin(t)")')
        assert "cos(t)" in r.plot_commands[0].label


# ── parametric 3D ─────────────────────────────────────────────────────


class TestParametric3D:
    def test_parametric3d_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('parametric3d("cos(t)", "sin(t)", "t/10")')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.PARAMETRIC_3D
        assert "x" in cmd.data and "y" in cmd.data and "z" in cmd.data

    def test_parametric3d_with_range(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('parametric3d("cos(t)", "sin(t)", "t", 0, 20)')
        assert not r.is_error
        assert r.plot_commands[0].kind == PlotKind.PARAMETRIC_3D

    def test_parametric3d_error_too_few(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('parametric3d("cos(t)", "sin(t)")')
        assert r.is_error

    def test_parametric3d_error_non_string(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('parametric3d("cos(t)", 42, "t")')
        assert r.is_error


# ── surface ───────────────────────────────────────────────────────────


class TestSurface:
    def test_surface_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('surface("sin(x)*cos(y)")')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.SURFACE_3D
        assert cmd.data["z"].shape == (80, 80)

    def test_surface_with_bounds(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('surface("x^2 + y^2", -3, 3, -3, 3)')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.SURFACE_3D

    def test_surface_no_string_error(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("surface(42)")
        assert r.is_error


# ── wireframe ─────────────────────────────────────────────────────────


class TestWireframe:
    def test_wireframe_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('wireframe("sin(x)*cos(y)")')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.WIREFRAME_3D
        assert cmd.data["z"].shape == (40, 40)

    def test_wireframe_with_bounds(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('wireframe("x^2 - y^2", -2, 2, -2, 2)')
        assert not r.is_error


# ── plotderiv ─────────────────────────────────────────────────────────


class TestPlotDeriv:
    def test_plotderiv_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('plotderiv("sin(x)")')
        assert not r.is_error
        assert len(r.plot_commands) == 2
        assert all(c.kind == PlotKind.LINE_2D for c in r.plot_commands)
        # Second command is the derivative (cos(x))
        assert "cos" in r.plot_commands[1].label.lower()

    def test_plotderiv_with_range(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('plotderiv("x^3", -2, 2)')
        assert not r.is_error
        assert len(r.plot_commands) == 2

    def test_plotderiv_output_contains_derivative(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('plotderiv("x^2")')
        assert "2*x" in r.output_text


# ── plotintegral ──────────────────────────────────────────────────────


class TestPlotIntegral:
    def test_plotintegral_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('plotintegral("x^2", 0, 1)')
        assert not r.is_error
        assert len(r.plot_commands) == 2
        assert r.plot_commands[0].kind == PlotKind.LINE_2D
        assert r.plot_commands[1].kind == PlotKind.FILL_BETWEEN

    def test_plotintegral_area_approx(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('plotintegral("x^2", 0, 1)')
        # ∫₀¹ x² dx = 1/3 ≈ 0.333
        assert "0.333" in r.output_text

    def test_plotintegral_fill_data(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('plotintegral("x", 0, 2)')
        fill = r.plot_commands[1]
        assert "x" in fill.data and "y1" in fill.data and "y2" in fill.data
        assert np.allclose(fill.data["y2"], 0.0)

    def test_plotintegral_error_too_few(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('plotintegral("x^2")')
        assert r.is_error


# ── tangentline ───────────────────────────────────────────────────────


class TestTangentLine:
    def test_tangentline_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('tangentline("x^2", 2)')
        assert not r.is_error
        assert len(r.plot_commands) == 3  # curve + tangent + point
        assert r.plot_commands[0].kind == PlotKind.LINE_2D
        assert r.plot_commands[1].kind == PlotKind.LINE_2D
        assert r.plot_commands[2].kind == PlotKind.SCATTER

    def test_tangentline_point_values(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('tangentline("x^2", 2)')
        scatter = r.plot_commands[2]
        assert scatter.data["x"][0] == pytest.approx(2.0)
        assert scatter.data["y"][0] == pytest.approx(4.0)  # 2²

    def test_tangentline_slope(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('tangentline("x^2", 3)')
        # slope of x² at x=3 is 6, y0 = 9
        assert "6" in r.output_text

    def test_tangentline_error_no_point(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('tangentline("x^2")')
        assert r.is_error


# ── implicit ──────────────────────────────────────────────────────────


class TestImplicit:
    def test_implicit_circle(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('implicit("x^2 + y^2 - 1")')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.IMPLICIT_2D
        assert cmd.data["z"].shape == (200, 200)

    def test_implicit_with_bounds(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('implicit("x^2 + y^2 - 4", -3, 3, -3, 3)')
        assert not r.is_error

    def test_implicit_label(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('implicit("x^2 + y^2 - 1")')
        assert "= 0" in r.plot_commands[0].label

    def test_implicit_no_string_error(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("implicit(42)")
        assert r.is_error


# ── contour ───────────────────────────────────────────────────────────


class TestContour:
    def test_contour_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('contour("x^2 + y^2")')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.CONTOUR
        assert "levels" in cmd.data
        assert len(cmd.data["levels"]) == 10  # default

    def test_contour_with_bounds(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('contour("x^2 + y^2", -3, 3, -3, 3)')
        assert not r.is_error

    def test_contour_custom_levels(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('contour("x^2 + y^2", -3, 3, -3, 3, 5)')
        assert not r.is_error
        assert len(r.plot_commands[0].data["levels"]) == 5


# ── slopefield ────────────────────────────────────────────────────────


class TestSlopeField:
    def test_slopefield_basic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('slopefield("y - x")')
        assert not r.is_error
        cmd = r.plot_commands[0]
        assert cmd.kind == PlotKind.SLOPE_FIELD
        assert cmd.data["X"].shape == (20, 20)

    def test_slopefield_with_bounds(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('slopefield("x*y", -3, 3, -3, 3)')
        assert not r.is_error

    def test_slopefield_custom_grid(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('slopefield("y", -2, 2, -2, 2, 10)')
        assert not r.is_error
        assert r.plot_commands[0].data["X"].shape == (10, 10)

    def test_slopefield_no_string_error(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("slopefield(42)")
        assert r.is_error


# ── Integration: hold mode with new commands ──────────────────────────


class TestHoldModeNewCommands:
    def test_fplot_with_hold(self, ev: MathEvaluator) -> None:
        ev.evaluate("hold(1)")
        r1 = ev.evaluate('fplot("sin(x)")')
        r2 = ev.evaluate('fplot("cos(x)")')
        assert not r1.is_error
        assert not r2.is_error

    def test_multiple_commands_single_input(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('hold(1); fplot("sin(x)"); fplot("cos(x)")')
        assert not r.is_error
        # Should have 2 LINE_2D plot commands
        line_cmds = [c for c in r.plot_commands if c.kind == PlotKind.LINE_2D]
        assert len(line_cmds) == 2
