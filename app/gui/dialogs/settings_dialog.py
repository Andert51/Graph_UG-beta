"""Settings dialog — theme selection, font size, and editor preferences."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.gui.styles.theme_manager import ThemeManager

from app.gui.styles.theme_manager import THEMES


class SettingsDialog(QDialog):
    """Preferences dialog with theme selector and font size control."""

    theme_changed = Signal(str)
    font_size_changed = Signal(int)

    def __init__(
        self,
        theme_manager: "ThemeManager",
        current_font_size: int = 13,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Settings")
        self.setFixedSize(420, 300)
        self.setModal(True)
        self._tm = theme_manager
        self._font_size = current_font_size
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # ── Appearance ────────────────────────────────────────────────
        appearance = QGroupBox("Appearance")
        form = QFormLayout(appearance)
        form.setSpacing(10)

        self._theme_combo = QComboBox()
        for key, palette in THEMES.items():
            self._theme_combo.addItem(palette.display_name, key)
        idx = self._theme_combo.findData(self._tm.current_name)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        form.addRow("Theme:", self._theme_combo)

        self._font_spin = QSpinBox()
        self._font_spin.setRange(9, 24)
        self._font_spin.setValue(self._font_size)
        self._font_spin.setSuffix(" px")
        form.addRow("Editor font size:", self._font_spin)

        root.addWidget(appearance)

        # ── Preview ───────────────────────────────────────────────────
        preview = QGroupBox("Preview")
        prev_layout = QVBoxLayout(preview)
        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        self._update_preview()
        prev_layout.addWidget(self._preview_label)
        root.addWidget(preview)

        self._theme_combo.currentIndexChanged.connect(self._update_preview)

        # ── Buttons ───────────────────────────────────────────────────
        root.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _update_preview(self) -> None:
        key = self._theme_combo.currentData()
        if key and key in THEMES:
            p = THEMES[key]
            self._preview_label.setText(
                f'<span style="font-size:11px; color:{p.fg_secondary};">'
                f"Background: {p.bg_dark} &nbsp; Text: {p.fg_primary} &nbsp; "
                f'Accent: <span style="color:{p.accent};">{p.accent}</span></span>'
            )

    def _on_accept(self) -> None:
        theme_key = self._theme_combo.currentData()
        if theme_key:
            self.theme_changed.emit(theme_key)
        font_size = self._font_spin.value()
        if font_size != self._font_size:
            self.font_size_changed.emit(font_size)
        self.accept()
