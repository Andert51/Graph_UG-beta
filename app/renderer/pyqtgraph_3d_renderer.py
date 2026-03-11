"""PyQtGraph3DRenderer — concrete IRenderer backed by pyqtgraph.opengl.

Handles 3-D plot primitives: surfaces, wireframes, and parametric curves.
The GLViewWidget is owned by CanvasPanel; this renderer receives it via
constructor injection — same pattern as the 2-D counterpart.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl

from app.core.interfaces.i_renderer import IRenderer
from app.core.models.plot_command import PlotCommand, PlotKind
from app.utils.logger import get_logger

_log = get_logger(__name__)


class PyQtGraph3DRenderer(IRenderer):
    """Renders 3-D ``PlotCommand`` DTOs onto a ``gl.GLViewWidget``."""

    # Colour cycle (Catppuccin-inspired, same palette as 2-D renderer)
    _COLOR_CYCLE: list[tuple[float, float, float, float]] = [
        (0.537, 0.706, 0.980, 0.8),  # blue
        (0.953, 0.545, 0.659, 0.8),  # red
        (0.651, 0.890, 0.631, 0.8),  # green
        (0.980, 0.702, 0.529, 0.8),  # peach
        (0.796, 0.651, 0.969, 0.8),  # mauve
        (0.976, 0.886, 0.686, 0.8),  # yellow
        (0.580, 0.886, 0.835, 0.8),  # teal
        (0.961, 0.761, 0.906, 0.8),  # pink
    ]

    def __init__(self, view_widget: gl.GLViewWidget) -> None:
        self._widget: gl.GLViewWidget = view_widget
        self._items: list[gl.GLGraphicsItem.GLGraphicsItem] = []
        self._color_index: int = 0

    # ------------------------------------------------------------------
    # IRenderer interface
    # ------------------------------------------------------------------

    def render(self, command: PlotCommand) -> None:
        _log.debug("3D render: kind=%s label=%r", command.kind.name, command.label)
        match command.kind:
            case PlotKind.SURFACE_3D:
                self._render_surface(command)
            case PlotKind.WIREFRAME_3D:
                self._render_wireframe(command)
            case PlotKind.PARAMETRIC_3D:
                self._render_parametric_3d(command)
            case PlotKind.SCATTER_3D:
                self._render_scatter_3d(command)
            case PlotKind.SURFACE_PARAM_3D:
                self._render_surface_parametric(command)
            case PlotKind.BAR_3D:
                self._render_bar_3d(command)
            case _:
                raise NotImplementedError(
                    f"PyQtGraph3DRenderer does not support: {command.kind}"
                )

    def clear(self) -> None:
        for item in self._items:
            self._widget.removeItem(item)
        self._items.clear()
        self._color_index = 0

    # ------------------------------------------------------------------
    # Colour cycling
    # ------------------------------------------------------------------

    def _next_color(self) -> tuple[float, float, float, float]:
        c = self._COLOR_CYCLE[self._color_index % len(self._COLOR_CYCLE)]
        self._color_index += 1
        return c

    # ------------------------------------------------------------------
    # Build a height-based colour map for surfaces
    # ------------------------------------------------------------------

    @staticmethod
    def _surface_colors(z: np.ndarray) -> np.ndarray:
        """Return an RGBA colour array shaped *(rows, cols, 4)* from *z* heights."""
        z_norm = z.copy()
        z_min, z_max = np.nanmin(z_norm), np.nanmax(z_norm)
        if z_max - z_min > 0:
            z_norm = (z_norm - z_min) / (z_max - z_min)
        else:
            z_norm = np.full_like(z_norm, 0.5)
        # Cool (blue) → warm (peach) gradient
        colors = np.empty((*z.shape, 4), dtype=float)
        colors[..., 0] = 0.537 + z_norm * (0.980 - 0.537)
        colors[..., 1] = 0.706 - z_norm * (0.706 - 0.545)
        colors[..., 2] = 0.980 - z_norm * (0.980 - 0.529)
        colors[..., 3] = 0.85
        return colors

    # ------------------------------------------------------------------
    # Private render strategies
    # ------------------------------------------------------------------

    def _render_surface(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (2D), ``y`` (2D), ``z`` (2D)."""
        z = np.asarray(cmd.data["z"], dtype=float)
        colors = self._surface_colors(z)
        item = gl.GLSurfacePlotItem(
            x=np.asarray(cmd.data["x"][0, :], dtype=float),
            y=np.asarray(cmd.data["y"][:, 0], dtype=float),
            z=z,
            colors=colors,
            shader="shaded",
            smooth=True,
        )
        self._widget.addItem(item)
        self._items.append(item)

    def _render_wireframe(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (2D), ``y`` (2D), ``z`` (2D)."""
        z = np.asarray(cmd.data["z"], dtype=float)
        color = self._next_color()
        item = gl.GLSurfacePlotItem(
            x=np.asarray(cmd.data["x"][0, :], dtype=float),
            y=np.asarray(cmd.data["y"][:, 0], dtype=float),
            z=z,
            shader=None,
            drawEdges=True,
            drawFaces=False,
            edgeColor=color,
        )
        self._widget.addItem(item)
        self._items.append(item)

    def _render_parametric_3d(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (1D), ``y`` (1D), ``z`` (1D)."""
        x = np.asarray(cmd.data["x"], dtype=float)
        y = np.asarray(cmd.data["y"], dtype=float)
        z = np.asarray(cmd.data["z"], dtype=float)
        color = self._next_color()
        pts = np.column_stack([x, y, z])
        item = gl.GLLinePlotItem(
            pos=pts,
            color=color,
            width=2.0,
            antialias=True,
        )
        self._widget.addItem(item)
        self._items.append(item)

    # ------------------------------------------------------------------
    # Phase 7 — New 3-D render strategies
    # ------------------------------------------------------------------

    def _render_scatter_3d(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (1D), ``y`` (1D), ``z`` (1D)."""
        x = np.asarray(cmd.data["x"], dtype=float)
        y = np.asarray(cmd.data["y"], dtype=float)
        z = np.asarray(cmd.data["z"], dtype=float)
        color = self._next_color()
        pts = np.column_stack([x, y, z])
        item = gl.GLScatterPlotItem(
            pos=pts,
            color=color,
            size=5.0,
            pxMode=True,
        )
        self._widget.addItem(item)
        self._items.append(item)

    def _render_surface_parametric(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (2D), ``y`` (2D), ``z`` (2D) — parametric surface."""
        X = np.asarray(cmd.data["x"], dtype=float)
        Y = np.asarray(cmd.data["y"], dtype=float)
        Z = np.asarray(cmd.data["z"], dtype=float)
        colors = self._surface_colors(Z)
        # GLSurfacePlotItem expects x as 1D, y as 1D, and z as 2D.
        # For parametric surfaces we use GLMeshItem instead.
        rows, cols = Z.shape
        verts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
        faces = []
        for i in range(rows - 1):
            for j in range(cols - 1):
                idx = i * cols + j
                faces.append([idx, idx + 1, idx + cols])
                faces.append([idx + 1, idx + cols + 1, idx + cols])
        faces = np.array(faces, dtype=np.uint32)
        # Per-face colours from average z of 3 vertices
        face_colors = np.empty((len(faces), 4), dtype=float)
        for fi, f in enumerate(faces):
            avg_z = np.mean([Z.ravel()[v] for v in f])
            z_min, z_max = np.nanmin(Z), np.nanmax(Z)
            t = (avg_z - z_min) / (z_max - z_min) if z_max > z_min else 0.5
            face_colors[fi] = [0.537 + t * 0.443, 0.706 - t * 0.161, 0.980 - t * 0.451, 0.85]

        md = gl.MeshData(vertexes=verts, faces=faces, faceColors=face_colors)
        item = gl.GLMeshItem(meshdata=md, smooth=True, shader="shaded")
        self._widget.addItem(item)
        self._items.append(item)

    def _render_bar_3d(self, cmd: PlotCommand) -> None:
        """``data`` keys: ``x`` (1D), ``y`` (1D), ``z`` (1D heights).
        Renders as vertical 3D bars using box meshes."""
        x = np.asarray(cmd.data["x"], dtype=float)
        y = np.asarray(cmd.data["y"], dtype=float)
        z = np.asarray(cmd.data["z"], dtype=float)
        for xi, yi, zi in zip(x, y, z):
            color = self._next_color()
            # Simple box: 8 vertices, 12 triangles
            w = 0.4
            verts = np.array([
                [xi - w, yi - w, 0], [xi + w, yi - w, 0],
                [xi + w, yi + w, 0], [xi - w, yi + w, 0],
                [xi - w, yi - w, zi], [xi + w, yi - w, zi],
                [xi + w, yi + w, zi], [xi - w, yi + w, zi],
            ])
            faces = np.array([
                [0, 1, 2], [0, 2, 3],  # bottom
                [4, 5, 6], [4, 6, 7],  # top
                [0, 1, 5], [0, 5, 4],  # front
                [2, 3, 7], [2, 7, 6],  # back
                [1, 2, 6], [1, 6, 5],  # right
                [0, 3, 7], [0, 7, 4],  # left
            ], dtype=np.uint32)
            face_colors = np.tile(list(color), (12, 1))
            md = gl.MeshData(vertexes=verts, faces=faces, faceColors=face_colors)
            item = gl.GLMeshItem(meshdata=md, smooth=False, shader="shaded")
            self._widget.addItem(item)
            self._items.append(item)
