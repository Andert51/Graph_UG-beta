"""InsertMatrixDialog — graphical modal for composing a matrix literal.

The dialog produces a plain GraphUG command string (via the ``command``
property) that the calling code emits as if the user had typed it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class InsertMatrixDialog(QDialog):
    """Modal for specifying a numeric matrix by entering cell values.

    The dimension spin-boxes dynamically resize the value grid.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Insert Matrix")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._cells: list[list[QDoubleSpinBox]] = []
        self._build_ui()
        self._rebuild_grid()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def command(self) -> str:
        """Return the synthesised GraphUG matrix literal, e.g. ``[1,2; 3,4]``."""
        rows_str: list[str] = []
        for row in self._cells:
            entries = ", ".join(
                f"{sb.value():g}" for sb in row
            )
            rows_str.append(entries)
        return "[" + "; ".join(rows_str) + "]"

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        desc = QLabel("Define matrix dimensions, then fill in the values.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; font-size: 12px;")
        root.addWidget(desc)

        # Dimension selectors
        dim_row = QHBoxLayout()
        dim_row.addWidget(QLabel("Rows:"))
        self._rows_spin = QSpinBox()
        self._rows_spin.setRange(1, 10)
        self._rows_spin.setValue(2)
        self._rows_spin.valueChanged.connect(self._rebuild_grid)
        dim_row.addWidget(self._rows_spin)

        dim_row.addWidget(QLabel("  Cols:"))
        self._cols_spin = QSpinBox()
        self._cols_spin.setRange(1, 10)
        self._cols_spin.setValue(2)
        self._cols_spin.valueChanged.connect(self._rebuild_grid)
        dim_row.addWidget(self._cols_spin)
        dim_row.addStretch()
        root.addLayout(dim_row)

        # Grid container
        self._grid_container = QVBoxLayout()
        root.addLayout(self._grid_container)

        # Preset buttons
        preset_row = QHBoxLayout()
        identity_btn = QPushButton("Identity")
        identity_btn.clicked.connect(self._fill_identity)
        preset_row.addWidget(identity_btn)
        zeros_btn = QPushButton("Zeros")
        zeros_btn.clicked.connect(self._fill_zeros)
        preset_row.addWidget(zeros_btn)
        preset_row.addStretch()
        root.addLayout(preset_row)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root.addWidget(button_box)

    def _rebuild_grid(self) -> None:
        """Rebuild the grid of QDoubleSpinBox to match current dimensions."""
        # Clear existing
        if hasattr(self, "_grid_widget") and self._grid_widget is not None:
            self._grid_container.removeWidget(self._grid_widget)
            self._grid_widget.deleteLater()

        rows = self._rows_spin.value()
        cols = self._cols_spin.value()

        self._grid_widget = QWidget()
        grid = QGridLayout(self._grid_widget)
        grid.setSpacing(4)

        self._cells = []
        for r in range(rows):
            row_cells: list[QDoubleSpinBox] = []
            for c in range(cols):
                sb = QDoubleSpinBox()
                sb.setRange(-1_000_000.0, 1_000_000.0)
                sb.setDecimals(4)
                sb.setSingleStep(1.0)
                sb.setValue(0.0)
                grid.addWidget(sb, r, c)
                row_cells.append(sb)
            self._cells.append(row_cells)

        self._grid_container.addWidget(self._grid_widget)

    def _fill_identity(self) -> None:
        """Fill the grid as an identity matrix."""
        for r, row in enumerate(self._cells):
            for c, sb in enumerate(row):
                sb.setValue(1.0 if r == c else 0.0)

    def _fill_zeros(self) -> None:
        """Fill all cells with zeros."""
        for row in self._cells:
            for sb in row:
                sb.setValue(0.0)
