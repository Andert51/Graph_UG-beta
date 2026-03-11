"""InsertVectorDialog — graphical modal for composing a 2D vector command.

The dialog is intentionally ignorant of the evaluator or renderer.  On
acceptance it produces a plain GraphUG command string (via the ``command``
property) that the calling code emits as if the user had typed it in the
editor.  This keeps the dialog a pure View component.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class InsertVectorDialog(QDialog):
    """Modal for specifying a 2D vector by origin and direction components.

    Produces a ``plot(x_arr, y_arr)`` command string describing the vector
    shaft, which the caller hands back to the controller as plain text input.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Insert Vector")
        self.setMinimumWidth(340)
        self.setModal(True)
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def command(self) -> str:
        """Return the synthesised GraphUG command string for this vector."""
        x0 = self._x0.value()
        y0 = self._y0.value()
        dx = self._dx.value()
        dy = self._dy.value()
        return f"vector({x0:g}, {y0:g}, {dx:g}, {dy:g})"

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        description = QLabel(
            "Define a 2D vector by its origin and direction components."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #a6adc8; font-size: 12px;")
        root.addWidget(description)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        self._x0 = self._make_spinbox()
        self._y0 = self._make_spinbox()
        self._dx = self._make_spinbox()
        self._dy = self._make_spinbox(default=1.0)

        form.addRow("Origin X (x₀):", self._x0)
        form.addRow("Origin Y (y₀):", self._y0)
        form.addRow("Component ΔX:", self._dx)
        form.addRow("Component ΔY:", self._dy)
        root.addLayout(form)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root.addWidget(button_box)

    @staticmethod
    def _make_spinbox(default: float = 0.0) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(-1_000_000.0, 1_000_000.0)
        sb.setDecimals(4)
        sb.setSingleStep(0.5)
        sb.setValue(default)
        return sb
