"""GraphUG dark QSS stylesheet.

Based on the Catppuccin Mocha palette — a modern, low-contrast dark theme
suitable for long working sessions.

Usage
-----
    from app.gui.styles.dark_theme import DARK_STYLESHEET
    app.setStyleSheet(DARK_STYLESHEET)
"""

DARK_STYLESHEET: str = """
/* ═══════════════════════════════════════════════════════════════════
   GraphUG — Dark Professional Theme (Catppuccin Mocha)
   ═══════════════════════════════════════════════════════════════════ */

QMainWindow,
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

/* ── Menu bar ─────────────────────────────────────────────────────── */
QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 2px 0;
}
QMenuBar::item:selected { background-color: #313244; border-radius: 3px; }

QMenu {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 4px 0;
}
QMenu::item            { padding: 5px 24px; }
QMenu::item:selected   { background-color: #45475a; border-radius: 3px; }
QMenu::separator       { height: 1px; background: #313244; margin: 4px 0; }

/* ── Splitter ─────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #313244;
}
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical   { height: 3px; }
QSplitter::handle:hover      { background-color: #89b4fa; }

/* ── Text editors ─────────────────────────────────────────────────── */
QTextEdit,
QPlainTextEdit {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    selection-background-color: #585b70;
    font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
    font-size: 13px;
}
QTextEdit:focus,
QPlainTextEdit:focus {
    border-color: #89b4fa;
}

/* ── Buttons ──────────────────────────────────────────────────────── */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 4px 14px;
    font-size: 12px;
}
QPushButton:hover  { background-color: #45475a; border-color: #89b4fa; }
QPushButton:pressed { background-color: #585b70; }
QPushButton:disabled { color: #585b70; border-color: #313244; }

/* ── Status bar ───────────────────────────────────────────────────── */
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
    font-size: 11px;
}

/* ── Scroll bars ──────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1e1e2e;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #585b70; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #1e1e2e;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #585b70; }
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }

/* ── Dialog / Spin-boxes ──────────────────────────────────────────── */
QDialog {
    background-color: #1e1e2e;
}
QDoubleSpinBox,
QSpinBox {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 3px 6px;
}
QDoubleSpinBox:focus,
QSpinBox:focus { border-color: #89b4fa; }

QLabel { color: #cdd6f4; }

/* ── Dialog button box ────────────────────────────────────────────── */
QDialogButtonBox QPushButton { min-width: 72px; }
"""
