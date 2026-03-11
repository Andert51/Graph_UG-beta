"""Tests for core models (MathResult, PlotCommand, Expression)."""

from __future__ import annotations

import pytest

from app.core.models.math_result import MathResult
from app.core.models.plot_command import PlotCommand, PlotKind
from app.core.models.expression import Expression, ExpressionKind


class TestMathResult:
    def test_is_error_when_error_set(self) -> None:
        r = MathResult(error="something went wrong")
        assert r.is_error
        assert r.error == "something went wrong"

    def test_is_not_error_when_no_error(self) -> None:
        r = MathResult(value=42.0)
        assert not r.is_error

    def test_has_plot_with_commands(self) -> None:
        cmd = PlotCommand(kind=PlotKind.LINE_2D, data={"x": [], "y": []})
        r = MathResult(plot_commands=[cmd])
        assert r.has_plot

    def test_has_no_plot_without_commands(self) -> None:
        r = MathResult(value=1.0)
        assert not r.has_plot

    def test_default_fields(self) -> None:
        r = MathResult()
        assert r.value is None
        assert r.plot_commands == []
        assert r.output_text == ""
        assert r.error is None
        assert not r.is_error
        assert not r.has_plot


class TestPlotCommand:
    def test_line_2d_kind(self) -> None:
        cmd = PlotCommand(kind=PlotKind.LINE_2D, data={"x": [0, 1], "y": [0, 1]})
        assert cmd.kind == PlotKind.LINE_2D
        assert cmd.data["x"] == [0, 1]

    def test_scatter_kind(self) -> None:
        cmd = PlotCommand(kind=PlotKind.SCATTER, data={})
        assert cmd.kind == PlotKind.SCATTER

    def test_all_plot_kinds_exist(self) -> None:
        expected = {"LINE_2D", "SCATTER", "VECTOR_2D", "BAR", "HISTOGRAM", "SURFACE_3D", "CANVAS_CMD"}
        actual = {k.name for k in PlotKind}
        assert expected == actual


class TestExpression:
    def test_expression_frozen(self) -> None:
        expr = Expression(raw="x + 1", kind=ExpressionKind.ARITHMETIC)
        with pytest.raises(AttributeError):
            expr.raw = "y + 2"  # type: ignore[misc]

    def test_expression_fields(self) -> None:
        expr = Expression(raw="plot(x, sin(x))", kind=ExpressionKind.PLOT_COMMAND)
        assert expr.raw == "plot(x, sin(x))"
        assert expr.kind == ExpressionKind.PLOT_COMMAND
