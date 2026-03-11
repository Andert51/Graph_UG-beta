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

/* ── Completer popup (autocomplete) ───────────────────────────────── */
QListView {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 2px;
    outline: none;
}
QListView::item { padding: 3px 8px; border-radius: 3px; }
QListView::item:selected { background-color: #313244; color: #89b4fa; }
QListView::item:hover { background-color: #11111b; }

/* ── Tooltips ─────────────────────────────────────────────────────── */
QToolTip {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}

/* ── Combo box dropdown ───────────────────────────────────────────── */
QComboBox {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 3px 8px;
}
QComboBox:focus { border-color: #89b4fa; }
QComboBox::drop-down {
    border: none;
    background: transparent;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    selection-background-color: #313244;
    selection-color: #89b4fa;
    border-radius: 4px;
}

/* ── Line edit ────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    padding: 3px 6px;
}
QLineEdit:focus { border-color: #89b4fa; }

/* ── List widget (snippet browser) ────────────────────────────────── */
QListWidget {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 4px;
    outline: none;
}
QListWidget::item { padding: 4px 8px; border-radius: 3px; }
QListWidget::item:selected { background-color: #313244; color: #89b4fa; }
QListWidget::item:hover { background-color: #1e1e2e; }

/* ── Group box ────────────────────────────────────────────────────── */
QGroupBox {
    color: #89b4fa;
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 12px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}

/* ── Tab widget (future use) ──────────────────────────────────────── */
QTabWidget::pane { border: 1px solid #313244; border-radius: 4px; }
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #313244;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 5px 14px;
}
QTabBar::tab:selected { background-color: #1e1e2e; color: #89b4fa; }
QTabBar::tab:hover { background-color: #313244; }

/* ── Progress bar ─────────────────────────────────────────────────── */
QProgressBar {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 4px;
    text-align: center;
    color: #cdd6f4;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 3px;
}
"""
