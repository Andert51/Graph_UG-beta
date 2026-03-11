"""Insert Calculus Command dialog — quick-insertion for symbolic math commands.

Provides a configurable dialog that generates symbolic command strings
(diff, integrate, limit, series, taylor, gradient, laplace, etc.)
based on user input fields.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

_TEMPLATES: dict[str, dict] = {
    "diff — Derivative": {
        "fields": [("Expression", "x^3 + 2*x"), ("Variable", "x")],
        "format": lambda f: f'diff("{f[0]}", "{f[1]}")',
    },
    "integrate — Indefinite Integral": {
        "fields": [("Expression", "x^2"), ("Variable", "x")],
        "format": lambda f: f'integrate("{f[0]}", "{f[1]}")',
    },
    "defint — Definite Integral": {
        "fields": [("Expression", "x^2"), ("Variable", "x"), ("Lower (a)", "0"), ("Upper (b)", "1")],
        "format": lambda f: f'defint("{f[0]}", "{f[1]}", {f[2]}, {f[3]})',
    },
    "limit — Limit": {
        "fields": [("Expression", "sin(x)/x"), ("Variable", "x"), ("Point", "0")],
        "format": lambda f: f'limit("{f[0]}", "{f[1]}", {f[2]})',
    },
    "series — Series Expansion": {
        "fields": [("Expression", "exp(x)"), ("Variable", "x"), ("Point", "0"), ("Terms", "6")],
        "format": lambda f: f'series("{f[0]}", "{f[1]}", {f[2]}, {f[3]})',
    },
    "taylor — Taylor Polynomial": {
        "fields": [("Expression", "sin(x)"), ("Variable", "x"), ("Point", "0"), ("Order", "5")],
        "format": lambda f: f'taylor("{f[0]}", "{f[1]}", {f[2]}, {f[3]})',
    },
    "partial — Partial Derivative": {
        "fields": [("Expression", "x^2*y + y^3"), ("Variable", "x")],
        "format": lambda f: f'partial("{f[0]}", "{f[1]}")',
    },
    "summation — Summation Σ": {
        "fields": [("Expression", "k^2"), ("Variable", "k"), ("From", "1"), ("To", "10")],
        "format": lambda f: f'summation("{f[0]}", "{f[1]}", {f[2]}, {f[3]})',
    },
    "product — Product Π": {
        "fields": [("Expression", "k"), ("Variable", "k"), ("From", "1"), ("To", "5")],
        "format": lambda f: f'product("{f[0]}", "{f[1]}", {f[2]}, {f[3]})',
    },
    "gradient — Gradient ∇f": {
        "fields": [("Expression", "x^2 + y^2 + z^2"), ("Variables", "x,y,z")],
        "format": lambda f: f'gradient("{f[0]}", "{f[1]}")',
    },
    "divergence — Divergence ∇·F": {
        "fields": [("Components (comma-sep)", "x^2, y^2, z^2"), ("Variables", "x,y,z")],
        "format": lambda f: f'divergence("{f[0]}", "{f[1]}")',
    },
    "curl — Curl ∇×F": {
        "fields": [("Components (F1,F2,F3)", "-y, x, 0"), ("Variables", "x,y,z")],
        "format": lambda f: f'curl("{f[0]}", "{f[1]}")',
    },
    "laplacian — Laplacian ∇²f": {
        "fields": [("Expression", "x^2 + y^2"), ("Variables", "x,y")],
        "format": lambda f: f'laplacian("{f[0]}", "{f[1]}")',
    },
    "laplace — Laplace Transform": {
        "fields": [("Expression", "exp(-a*t)"), ("t variable", "t"), ("s variable", "s")],
        "format": lambda f: f'laplace("{f[0]}", "{f[1]}", "{f[2]}")',
    },
    "invlaplace — Inverse Laplace": {
        "fields": [("Expression", "1/(s+a)"), ("s variable", "s"), ("t variable", "t")],
        "format": lambda f: f'invlaplace("{f[0]}", "{f[1]}", "{f[2]}")',
    },
    "simplify — Simplify": {
        "fields": [("Expression", "(x^2 - 1)/(x - 1)")],
        "format": lambda f: f'simplify("{f[0]}")',
    },
    "factor — Factor": {
        "fields": [("Expression", "x^2 - 1")],
        "format": lambda f: f'factor("{f[0]}")',
    },
    "expand — Expand": {
        "fields": [("Expression", "(x+1)^3")],
        "format": lambda f: f'expand("{f[0]}")',
    },
    "solve — Solve Equation": {
        "fields": [("Equation (= 0)", "x^2 - 4"), ("Variable", "x")],
        "format": lambda f: f'solve("{f[0]}", "{f[1]}")',
    },
    "nsolve — Numerical Solve": {
        "fields": [("Equation (= 0)", "cos(x) - x"), ("Variable", "x"), ("Initial guess", "1")],
        "format": lambda f: f'nsolve("{f[0]}", "{f[1]}", {f[2]})',
    },
    "rref — Row Echelon Form": {
        "fields": [("Matrix", "[[1,2,3];[4,5,6]]")],
        "format": lambda f: f'rref("{f[0]}")',
    },
}


class InsertCalculusDialog(QDialog):
    """Dialog for inserting a calculus / symbolic command via guided form fields."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Calculus / Algebra Command")
        self.setFixedWidth(480)
        self.command: str = ""
        self._field_widgets: list[QLineEdit] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Command type:"))
        self._combo = QComboBox()
        self._combo.addItems(list(_TEMPLATES.keys()))
        self._combo.currentTextChanged.connect(self._on_template_changed)
        layout.addWidget(self._combo)

        self._form_container = QWidget()
        self._form_layout = QFormLayout(self._form_container)
        self._form_layout.setContentsMargins(0, 6, 0, 0)
        layout.addWidget(self._form_container)

        self._preview = QLabel()
        self._preview.setStyleSheet(
            "background:#11111b; color:#89b4fa; padding:6px; "
            "border:1px solid #313244; border-radius:4px; font-family:monospace;"
        )
        self._preview.setWordWrap(True)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self._preview)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_template_changed(self._combo.currentText())

    def _on_template_changed(self, name: str) -> None:
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
