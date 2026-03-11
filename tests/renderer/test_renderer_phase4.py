"""Tests for the new 2D renderer methods — Phase 4: fill_between, contour, implicit, slope_field."""

from __future__ import annotations

import numpy as np
import pytest

from app.core.models.plot_command import PlotCommand, PlotKind


@pytest.fixture
def renderer(qtbot):
    import pyqtgraph as pg
    from app.renderer.pyqtgraph_renderer import PyQtGraphRenderer

    w = pg.PlotWidget()
    w.show()
    qtbot.addWidget(w)
    return PyQtGraphRenderer(w)


class TestFillBetween:
    def test_render_fill_between(self, renderer) -> None:
        x = np.linspace(0, 1, 50)
        cmd = PlotCommand(
            kind=PlotKind.FILL_BETWEEN,
            data={"x": x, "y1": x**2, "y2": np.zeros_like(x)},
        )
        renderer.render(cmd)
        # FillBetweenItem + 2 boundary curves
        assert len(renderer._items) == 3


class TestContourRender:
    def test_render_contour(self, renderer) -> None:
        n = 50
        x = np.linspace(-2, 2, n)
        y = np.linspace(-2, 2, n)
        X, Y = np.meshgrid(x, y)
        Z = X**2 + Y**2
        cmd = PlotCommand(
            kind=PlotKind.CONTOUR,
            data={
                "z": Z,
                "x_range": (-2.0, 2.0),
                "y_range": (-2.0, 2.0),
                "levels": [1.0, 2.0, 3.0],
            },
        )
        renderer.render(cmd)
        assert len(renderer._items) == 3  # one IsocurveItem per level


class TestImplicit2DRender:
    def test_render_implicit(self, renderer) -> None:
        n = 50
        x = np.linspace(-2, 2, n)
        y = np.linspace(-2, 2, n)
        X, Y = np.meshgrid(x, y)
        Z = X**2 + Y**2 - 1
        cmd = PlotCommand(
            kind=PlotKind.IMPLICIT_2D,
            data={"z": Z, "x_range": (-2.0, 2.0), "y_range": (-2.0, 2.0)},
        )
        renderer.render(cmd)
        assert len(renderer._items) == 1  # single IsocurveItem at level=0


class TestSlopeFieldRender:
    def test_render_slope_field(self, renderer) -> None:
        xs = np.linspace(-2, 2, 5)
        ys = np.linspace(-2, 2, 5)
        X, Y = np.meshgrid(xs, ys)
        DX = np.ones_like(X) * 0.1
        DY = Y * 0.1
        cmd = PlotCommand(
            kind=PlotKind.SLOPE_FIELD,
            data={"X": X, "Y": Y, "DX": DX, "DY": DY},
        )
        renderer.render(cmd)
        assert len(renderer._items) == 25  # 5×5 grid


class TestClearAfterNew:
    def test_clear_removes_new_items(self, renderer) -> None:
        x = np.linspace(0, 1, 10)
        renderer.render(PlotCommand(
            kind=PlotKind.FILL_BETWEEN,
            data={"x": x, "y1": x, "y2": np.zeros_like(x)},
        ))
        assert len(renderer._items) > 0
        renderer.clear()
        assert len(renderer._items) == 0
