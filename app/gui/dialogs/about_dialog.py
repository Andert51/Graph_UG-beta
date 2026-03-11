"""AboutDialog — project information modal."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)


_VERSION = "0.3.0"

_ABOUT_HTML = f"""\
<h2 style="margin-bottom: 4px;">GraphUG</h2>
<p style="color: #a6adc8; margin-top: 0;">
  Interactive Mathematical Environment &amp; Graphing Calculator<br/>
  Version <b>{_VERSION}</b>
</p>
<hr/>
<p>
  <b>Architecture:</b> MVC / Clean Architecture<br/>
  <b>Stack:</b> PySide6 · PyQtGraph · NumPy · SymPy · Lark<br/>
  <b>License:</b> MIT
</p>
<p style="color: #a6adc8; font-size: 11px;">
  Built with ♥ — open-source at
  <span style="color: #89b4fa;">github.com/Andert51/Graph_UG-beta</span>
</p>
"""


class AboutDialog(QDialog):
    """Simple project info dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("About GraphUG")
        self.setFixedSize(420, 280)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)

        label = QLabel(_ABOUT_HTML)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        root.addWidget(label)

        root.addStretch()

        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn.accepted.connect(self.accept)
        root.addWidget(btn)
