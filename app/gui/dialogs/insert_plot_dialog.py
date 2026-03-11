"""Insert Plot Command dialog — quick-insertion for graphing commands.

Provides a configurable dialog that generates plot command strings
(fplot, polar, parametric, surface, tangentline, plotintegral, etc.)
based on user input fields.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

# Each template maps: (label, list-of-field-descriptors, format-function)
# Field descriptor: (field_label, default_value)
_TEMPLATES: dict[str, dict] = {
    "fplot — Function Plot": {
        "fields": [
            ("Expression (of x)", "sin(x)"),
            ("x min", "-10"),
            ("x max", "10"),
        ],
        "format": lambda f: f'fplot("{f[0]}", {f[1]}, {f[2]})',
    },
    "polar — Polar Plot": {
        "fields": [
            ("r(t) expression", "2*cos(t)"),
            ("t min", "0"),
            ("t max", "2*pi"),
        ],
        "format": lambda f: f'polar("{f[0]}", {f[1]}, {f[2]})',
    },
    "parametric — 2D Parametric": {
        "fields": [
            ("x(t) expression", "cos(t)"),
            ("y(t) expression", "sin(t)"),
            ("t min", "0"),
            ("t max", "2*pi"),
        ],
        "format": lambda f: f'parametric("{f[0]}", "{f[1]}", {f[2]}, {f[3]})',
    },
    "parametric3d — 3D Parametric": {
        "fields": [
            ("x(t) expression", "cos(t)"),
            ("y(t) expression", "sin(t)"),
            ("z(t) expression", "t/10"),
            ("t min", "0"),
            ("t max", "20"),
        ],
        "format": lambda f: f'parametric3d("{f[0]}", "{f[1]}", "{f[2]}", {f[3]}, {f[4]})',
    },
    "surface — 3D Surface": {
        "fields": [
            ("f(x,y) expression", "sin(x)*cos(y)"),
            ("x min", "-5"),
            ("x max", "5"),
            ("y min", "-5"),
            ("y max", "5"),
        ],
        "format": lambda f: f'surface("{f[0]}", {f[1]}, {f[2]}, {f[3]}, {f[4]})',
    },
    "tangentline — Tangent Line": {
        "fields": [
            ("f(x) expression", "x^2"),
            ("x₀ (point)", "1"),
        ],
        "format": lambda f: f'tangentline("{f[0]}", {f[1]})',
    },
    "plotintegral — Integral Plot": {
        "fields": [
            ("f(x) expression", "x^2"),
            ("a (lower bound)", "0"),
            ("b (upper bound)", "2"),
        ],
        "format": lambda f: f'plotintegral("{f[0]}", {f[1]}, {f[2]})',
    },
    "plotderiv — Derivative Plot": {
        "fields": [
            ("f(x) expression", "sin(x)"),
            ("x min", "-10"),
            ("x max", "10"),
        ],
        "format": lambda f: f'plotderiv("{f[0]}", {f[1]}, {f[2]})',
    },
    "implicit — Implicit Curve": {
        "fields": [
            ("f(x,y) = 0 expression", "x^2 + y^2 - 1"),
        ],
        "format": lambda f: f'implicit("{f[0]}")',
    },
    "contour — Contour Plot": {
        "fields": [
            ("f(x,y) expression", "x^2 + y^2"),
        ],
        "format": lambda f: f'contour("{f[0]}")',
    },
    "slopefield — Slope Field": {
        "fields": [
            ("dy/dx = f(x,y)", "y - x"),
        ],
        "format": lambda f: f'slopefield("{f[0]}")',
    },
}


class InsertPlotDialog(QDialog):
    """Dialog for inserting a plot command via guided form fields."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Plot Command")
        self.setFixedWidth(440)
        self.command: str = ""
        self._field_widgets: list[QLineEdit] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Command type selector
        layout.addWidget(QLabel("Command type:"))
        self._combo = QComboBox()
        self._combo.addItems(list(_TEMPLATES.keys()))
        self._combo.currentTextChanged.connect(self._on_template_changed)
        layout.addWidget(self._combo)

        # Dynamic form area
        self._form_container = QWidget()
        self._form_layout = QFormLayout(self._form_container)
        self._form_layout.setContentsMargins(0, 6, 0, 0)
        layout.addWidget(self._form_container)

        # Preview
        self._preview = QLabel()
        self._preview.setStyleSheet(
            "background:#11111b; color:#89b4fa; padding:6px; "
            "border:1px solid #313244; border-radius:4px; font-family:monospace;"
        )
        self._preview.setWordWrap(True)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self._preview)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initialise with first template
        self._on_template_changed(self._combo.currentText())

    def _on_template_changed(self, name: str) -> None:
        # Clear existing fields
        while self._form_layout.rowCount():
            self._form_layout.removeRow(0)
        self._field_widgets.clear()

        template = _TEMPLATES.get(name)
        if not template:
            return

        for label, default in template["fields"]:
            edit = QLineEdit(default)
            edit.textChanged.connect(self._update_preview)
            self._form_layout.addRow(label + ":", edit)
            self._field_widgets.append(edit)

        self._update_preview()

    def _update_preview(self) -> None:
        name = self._combo.currentText()
        template = _TEMPLATES.get(name)
        if not template:
            return
        values = [w.text() for w in self._field_widgets]
        try:
            cmd = template["format"](values)
            self._preview.setText(cmd)
        except (IndexError, KeyError):
            self._preview.setText("…")

    def _on_accept(self) -> None:
        name = self._combo.currentText()
        template = _TEMPLATES.get(name)
        if template:
            values = [w.text() for w in self._field_widgets]
            self.command = template["format"](values)
        self.accept()
