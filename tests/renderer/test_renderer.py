"""Tests for PyQtGraphRenderer — item tracking, colour cycling, canvas commands."""

from __future__ import annotations

import numpy as np
import pytest

from app.core.models.plot_command import PlotCommand, PlotKind


@pytest.fixture
def renderer(qtbot):
    """Create a renderer backed by a real PlotWidget (needs QApp from qtbot)."""
    import pyqtgraph as pg
    from app.renderer.pyqtgraph_renderer import PyQtGraphRenderer

    widget = pg.PlotWidget()
    return PyQtGraphRenderer(widget)


class TestRendererItemTracking:
    def test_render_adds_item(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": np.array([0, 1, 2]), "y": np.array([0, 1, 4])},
        )
        renderer.render(cmd)
        assert len(renderer._items) == 1

    def test_clear_removes_items(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": np.array([0, 1]), "y": np.array([0, 1])},
        )
        renderer.render(cmd)
        renderer.render(cmd)
        assert len(renderer._items) == 2
        renderer.clear()
        assert len(renderer._items) == 0

    def test_scatter_tracking(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.SCATTER,
            data={"x": np.array([1, 2, 3]), "y": np.array([4, 5, 6])},
        )
        renderer.render(cmd)
        assert len(renderer._items) == 1

    def test_vector_tracking(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.VECTOR_2D,
            data={"x0": 0.0, "y0": 0.0, "dx": 1.0, "dy": 1.0},
        )
        renderer.render(cmd)
        # Vector creates 2 items: shaft + arrowhead
        assert len(renderer._items) == 2

    def test_bar_tracking(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.BAR,
            data={"x": np.array([0, 1, 2]), "height": np.array([3, 7, 2]), "width": 0.8},
        )
        renderer.render(cmd)
        assert len(renderer._items) == 1

    def test_histogram_tracking(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.HISTOGRAM,
            data={"values": np.random.randn(100), "bins": 10},
        )
        renderer.render(cmd)
        assert len(renderer._items) == 1


class TestColourCycling:
    def test_default_colour_cycles(self, renderer) -> None:
        """Multiple renders without explicit colour should cycle through palette."""
        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": np.array([0, 1]), "y": np.array([0, 1])},
        )
        renderer.render(cmd)
        renderer.render(cmd)
        # color_index should be 2 after two renders
        assert renderer._color_index == 2

    def test_explicit_colour_skips_cycle(self, renderer) -> None:
        """Explicit colour should not advance the cycle."""
        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": np.array([0, 1]), "y": np.array([0, 1])},
            color="#ff0000",
        )
        renderer.render(cmd)
        assert renderer._color_index == 0

    def test_clear_resets_colour(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.LINE_2D,
            data={"x": np.array([0, 1]), "y": np.array([0, 1])},
        )
        renderer.render(cmd)
        renderer.render(cmd)
        renderer.clear()
        assert renderer._color_index == 0


class TestCanvasCommands:
    def test_xlabel(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.CANVAS_CMD,
            data={"cmd": "xlabel", "text": "X Axis"},
        )
        renderer.render(cmd)
        # No items added for canvas commands
        assert len(renderer._items) == 0

    def test_ylabel(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.CANVAS_CMD,
            data={"cmd": "ylabel", "text": "Y Axis"},
        )
        renderer.render(cmd)
        assert len(renderer._items) == 0

    def test_title(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.CANVAS_CMD,
            data={"cmd": "title", "text": "My Title"},
        )
        renderer.render(cmd)

    def test_grid_toggle(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.CANVAS_CMD,
            data={"cmd": "grid", "visible": None},
        )
        renderer.render(cmd)
        assert renderer._grid_visible is True
        renderer.render(cmd)
        assert renderer._grid_visible is False

    def test_grid_explicit(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.CANVAS_CMD,
            data={"cmd": "grid", "visible": True},
        )
        renderer.render(cmd)
        assert renderer._grid_visible is True

    def test_unsupported_kind(self, renderer) -> None:
        cmd = PlotCommand(
            kind=PlotKind.SURFACE_3D,
            data={},
        )
        with pytest.raises(NotImplementedError):
            renderer.render(cmd)
