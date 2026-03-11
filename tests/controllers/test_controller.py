"""Tests for MainController — signal emission, hold mode, clear canvas."""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from app.controllers.main_controller import MainController
from app.core.models.math_result import MathResult
from app.core.models.plot_command import PlotCommand, PlotKind


@pytest.fixture
def mock_evaluator():
    ev = MagicMock()
    ev.hold_mode = False
    return ev


@pytest.fixture
def mock_renderer():
    return MagicMock()


@pytest.fixture
def controller(qtbot, mock_evaluator, mock_renderer):
    return MainController(mock_evaluator, mock_renderer)


class TestHandleInput:
    def test_result_ready_emitted(self, qtbot, controller, mock_evaluator) -> None:
        mock_evaluator.evaluate.return_value = MathResult(value=42.0, output_text="42")
        with qtbot.waitSignal(controller.result_ready, timeout=1000):
            controller.handle_input("42")

    def test_error_emitted_on_error(self, qtbot, controller, mock_evaluator) -> None:
        mock_evaluator.evaluate.return_value = MathResult(error="ParseError: bad")
        with qtbot.waitSignal(controller.error_occurred, timeout=1000):
            controller.handle_input("???")

    def test_renderer_called_for_plot(self, controller, mock_evaluator, mock_renderer) -> None:
        cmd = PlotCommand(kind=PlotKind.LINE_2D, data={"x": np.array([0]), "y": np.array([0])})
        mock_evaluator.evaluate.return_value = MathResult(plot_commands=[cmd], output_text="plot")
        controller.handle_input("plot(x,y)")
        mock_renderer.render.assert_called_once_with(cmd)

    def test_clear_before_plot_when_no_hold(self, controller, mock_evaluator, mock_renderer) -> None:
        cmd = PlotCommand(kind=PlotKind.LINE_2D, data={"x": np.array([0]), "y": np.array([0])})
        mock_evaluator.evaluate.return_value = MathResult(plot_commands=[cmd], output_text="plot")
        mock_evaluator.hold_mode = False
        controller.handle_input("plot(x,y)")
        mock_renderer.clear.assert_called_once()

    def test_no_clear_when_hold_mode(self, controller, mock_evaluator, mock_renderer) -> None:
        cmd = PlotCommand(kind=PlotKind.LINE_2D, data={"x": np.array([0]), "y": np.array([0])})
        mock_evaluator.evaluate.return_value = MathResult(plot_commands=[cmd], output_text="plot")
        mock_evaluator.hold_mode = True
        controller.handle_input("plot(x,y)")
        mock_renderer.clear.assert_not_called()

    def test_canvas_cmd_does_not_trigger_clear(self, controller, mock_evaluator, mock_renderer) -> None:
        cmd = PlotCommand(kind=PlotKind.CANVAS_CMD, data={"cmd": "grid"})
        mock_evaluator.evaluate.return_value = MathResult(plot_commands=[cmd], output_text="grid")
        controller.handle_input("grid()")
        mock_renderer.clear.assert_not_called()


class TestResetSession:
    def test_reset_clears_evaluator_and_renderer(self, qtbot, controller, mock_evaluator, mock_renderer) -> None:
        with qtbot.waitSignal(controller.result_ready, timeout=1000):
            controller.reset_session()
        mock_evaluator.reset_state.assert_called_once()
        mock_renderer.clear.assert_called_once()


class TestClearCanvas:
    def test_clear_canvas_only_clears_renderer(self, controller, mock_evaluator, mock_renderer) -> None:
        controller.clear_canvas()
        mock_renderer.clear.assert_called_once()
        mock_evaluator.reset_state.assert_not_called()
