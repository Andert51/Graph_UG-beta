"""Tests for the PyQtGraph3DRenderer — Phase 4 3-D rendering."""

from __future__ import annotations

import numpy as np
import pytest

from app.core.models.plot_command import PlotCommand, PlotKind


@pytest.fixture()
def gl_widget(qtbot):
    """Create a GLViewWidget for testing."""
    import pyqtgraph.opengl as gl

    w = gl.GLViewWidget()
    w.show()
    qtbot.addWidget(w)
    return w


@pytest.fixture()
def renderer_3d(gl_widget):
    from app.renderer.pyqtgraph_3d_renderer import PyQtGraph3DRenderer

    return PyQtGraph3DRenderer(gl_widget)


class TestPyQtGraph3DRenderer:
    def test_render_surface(self, renderer_3d) -> None:
        n = 20
        x = np.linspace(-2, 2, n)
        y = np.linspace(-2, 2, n)
        X, Y = np.meshgrid(x, y)
        Z = np.sin(X) * np.cos(Y)
        cmd = PlotCommand(
            kind=PlotKind.SURFACE_3D,
            data={"x": X, "y": Y, "z": Z},
        )
        renderer_3d.render(cmd)
        assert len(renderer_3d._items) == 1

    def test_render_wireframe(self, renderer_3d) -> None:
        n = 10
        x = np.linspace(-1, 1, n)
        y = np.linspace(-1, 1, n)
        X, Y = np.meshgrid(x, y)
        Z = X**2 + Y**2
        cmd = PlotCommand(
            kind=PlotKind.WIREFRAME_3D,
            data={"x": X, "y": Y, "z": Z},
        )
        renderer_3d.render(cmd)
        assert len(renderer_3d._items) == 1

    def test_render_parametric_3d(self, renderer_3d) -> None:
        t = np.linspace(0, 10, 200)
        cmd = PlotCommand(
            kind=PlotKind.PARAMETRIC_3D,
            data={"x": np.cos(t), "y": np.sin(t), "z": t / 5},
        )
        renderer_3d.render(cmd)
        assert len(renderer_3d._items) == 1

    def test_clear(self, renderer_3d) -> None:
        t = np.linspace(0, 1, 50)
        cmd = PlotCommand(
            kind=PlotKind.PARAMETRIC_3D,
            data={"x": t, "y": t, "z": t},
        )
        renderer_3d.render(cmd)
        assert len(renderer_3d._items) == 1
        renderer_3d.clear()
        assert len(renderer_3d._items) == 0

    def test_unsupported_kind(self, renderer_3d) -> None:
        cmd = PlotCommand(kind=PlotKind.LINE_2D, data={"x": [1], "y": [1]})
        with pytest.raises(NotImplementedError):
            renderer_3d.render(cmd)

    def test_color_cycling(self, renderer_3d) -> None:
        t = np.linspace(0, 1, 10)
        for _ in range(3):
            cmd = PlotCommand(
                kind=PlotKind.PARAMETRIC_3D,
                data={"x": t, "y": t, "z": t},
            )
            renderer_3d.render(cmd)
        assert renderer_3d._color_index == 3
        assert len(renderer_3d._items) == 3

    def test_surface_colors_static(self) -> None:
        from app.renderer.pyqtgraph_3d_renderer import PyQtGraph3DRenderer

        z = np.array([[0, 1], [2, 3]], dtype=float)
        colors = PyQtGraph3DRenderer._surface_colors(z)
        assert colors.shape == (2, 2, 4)
        assert (colors[..., 3] == 0.85).all()
