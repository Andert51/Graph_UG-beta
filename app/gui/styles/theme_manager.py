"""Theme manager — switchable palettes for the entire application.

Provides a ``ThemeManager`` that generates QSS from named colour palettes
and notifies connected widgets to refresh their non-QSS styling (e.g. the
PyQtGraph canvas, syntax highlighter, completer popup).

Usage
-----
    from app.gui.styles.theme_manager import ThemeManager
    tm = ThemeManager()
    tm.apply_theme("catppuccin_mocha", app)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


# ── Colour Palette ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Palette:
    """Canonical set of colours that every theme must supply."""

    name: str
    display_name: str

    # Backgrounds (darkest → lightest)
    bg_darkest: str    # deepest background (editors, inputs)
    bg_dark: str       # main window / panel background
    bg_medium: str     # headers, toolbars, sidebars
    bg_light: str      # hover / elevated surfaces

    # Foregrounds
    fg_primary: str    # main text
    fg_secondary: str  # muted / labels
    fg_dim: str        # very muted (camera info, hints)

    # Borders / separators
    border: str
    border_light: str

    # Accent colours
    accent: str        # primary accent (links, highlights)
    accent_alt: str    # secondary accent (keywords)
    green: str         # success / output
    red: str           # error
    yellow: str        # warnings
    peach: str         # numbers / constants
    lavender: str      # strings
    teal: str          # types / builtins
    pink: str          # operators

    # Canvas / graph
    canvas_bg: str
    grid_colour: str
    axis_colour: str


# ── Built-in palettes ────────────────────────────────────────────────

CATPPUCCIN_MOCHA = Palette(
    name="catppuccin_mocha",
    display_name="Catppuccin Mocha",
    bg_darkest="#11111b",
    bg_dark="#1e1e2e",
    bg_medium="#181825",
    bg_light="#313244",
    fg_primary="#cdd6f4",
    fg_secondary="#a6adc8",
    fg_dim="#6c7086",
    border="#313244",
    border_light="#45475a",
    accent="#89b4fa",
    accent_alt="#cba6f7",
    green="#a6e3a1",
    red="#f38ba8",
    yellow="#f9e2af",
    peach="#fab387",
    lavender="#b4befe",
    teal="#94e2d5",
    pink="#f5c2e7",
    canvas_bg="#11111b",
    grid_colour="#45475a",
    axis_colour="#a6adc8",
)

CATPPUCCIN_LATTE = Palette(
    name="catppuccin_latte",
    display_name="Catppuccin Latte",
    bg_darkest="#e6e9ef",
    bg_dark="#eff1f5",
    bg_medium="#dce0e8",
    bg_light="#ccd0da",
    fg_primary="#4c4f69",
    fg_secondary="#6c6f85",
    fg_dim="#9ca0b0",
    border="#ccd0da",
    border_light="#bcc0cc",
    accent="#1e66f5",
    accent_alt="#8839ef",
    green="#40a02b",
    red="#d20f39",
    yellow="#df8e1d",
    peach="#fe640b",
    lavender="#7287fd",
    teal="#179299",
    pink="#ea76cb",
    canvas_bg="#e6e9ef",
    grid_colour="#bcc0cc",
    axis_colour="#6c6f85",
)

NORD = Palette(
    name="nord",
    display_name="Nord",
    bg_darkest="#242933",
    bg_dark="#2e3440",
    bg_medium="#3b4252",
    bg_light="#434c5e",
    fg_primary="#d8dee9",
    fg_secondary="#b0b8c8",
    fg_dim="#7b88a1",
    border="#3b4252",
    border_light="#434c5e",
    accent="#88c0d0",
    accent_alt="#b48ead",
    green="#a3be8c",
    red="#bf616a",
    yellow="#ebcb8b",
    peach="#d08770",
    lavender="#81a1c1",
    teal="#8fbcbb",
    pink="#b48ead",
    canvas_bg="#242933",
    grid_colour="#434c5e",
    axis_colour="#b0b8c8",
)

DRACULA = Palette(
    name="dracula",
    display_name="Dracula",
    bg_darkest="#21222c",
    bg_dark="#282a36",
    bg_medium="#2d2f3f",
    bg_light="#44475a",
    fg_primary="#f8f8f2",
    fg_secondary="#c0c0c0",
    fg_dim="#6272a4",
    border="#44475a",
    border_light="#6272a4",
    accent="#bd93f9",
    accent_alt="#ff79c6",
    green="#50fa7b",
    red="#ff5555",
    yellow="#f1fa8c",
    peach="#ffb86c",
    lavender="#bd93f9",
    teal="#8be9fd",
    pink="#ff79c6",
    canvas_bg="#21222c",
    grid_colour="#44475a",
    axis_colour="#c0c0c0",
)

SOLARIZED_DARK = Palette(
    name="solarized_dark",
    display_name="Solarized Dark",
    bg_darkest="#002028",
    bg_dark="#002b36",
    bg_medium="#073642",
    bg_light="#586e75",
    fg_primary="#839496",
    fg_secondary="#93a1a1",
    fg_dim="#657b83",
    border="#073642",
    border_light="#586e75",
    accent="#268bd2",
    accent_alt="#6c71c4",
    green="#859900",
    red="#dc322f",
    yellow="#b58900",
    peach="#cb4b16",
    lavender="#6c71c4",
    teal="#2aa198",
    pink="#d33682",
    canvas_bg="#002028",
    grid_colour="#073642",
    axis_colour="#93a1a1",
)

THEMES: dict[str, Palette] = {
    p.name: p
    for p in [CATPPUCCIN_MOCHA, CATPPUCCIN_LATTE, NORD, DRACULA, SOLARIZED_DARK]
}


# ── QSS Generator ────────────────────────────────────────────────────


def generate_stylesheet(p: Palette) -> str:
    """Build a complete QSS string from palette *p*."""
    return f"""
/* ═══════════════════════════════════════════════════════════════════
   GraphUG — {p.display_name} Theme (auto-generated)
   ═══════════════════════════════════════════════════════════════════ */

QMainWindow,
QWidget {{
    background-color: {p.bg_dark};
    color: {p.fg_primary};
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}

/* ── Menu bar ─────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {p.bg_medium};
    color: {p.fg_primary};
    border-bottom: 1px solid {p.border};
    padding: 2px 0;
}}
QMenuBar::item:selected {{ background-color: {p.bg_light}; border-radius: 3px; }}

QMenu {{
    background-color: {p.bg_medium};
    border: 1px solid {p.border};
    border-radius: 4px;
    padding: 4px 0;
}}
QMenu::item            {{ padding: 5px 24px; }}
QMenu::item:selected   {{ background-color: {p.border_light}; border-radius: 3px; }}
QMenu::separator       {{ height: 1px; background: {p.border}; margin: 4px 0; }}

/* ── Toolbar ──────────────────────────────────────────────────────── */
QToolBar {{
    background-color: {p.bg_medium};
    border-bottom: 1px solid {p.border};
    spacing: 4px;
    padding: 2px 6px;
}}
QToolBar::separator {{
    width: 1px;
    background: {p.border};
    margin: 4px 2px;
}}
QToolButton {{
    background: transparent;
    color: {p.fg_secondary};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 12px;
}}
QToolButton:hover {{
    background-color: {p.bg_light};
    border-color: {p.border};
    color: {p.fg_primary};
}}
QToolButton:pressed {{
    background-color: {p.border_light};
}}

/* ── Dock widgets ─────────────────────────────────────────────────── */
QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
    font-size: 11px;
    color: {p.fg_secondary};
}}
QDockWidget::title {{
    background-color: {p.bg_medium};
    border: 1px solid {p.border};
    border-bottom: none;
    padding: 5px 8px;
    text-align: left;
    font-weight: bold;
    letter-spacing: 0.5px;
}}
QDockWidget::close-button,
QDockWidget::float-button {{
    background: transparent;
    border: none;
    padding: 2px;
}}
QDockWidget::close-button:hover,
QDockWidget::float-button:hover {{
    background-color: {p.bg_light};
    border-radius: 3px;
}}

/* ── Splitter ─────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {p.border};
}}
QSplitter::handle:horizontal {{ width: 3px; }}
QSplitter::handle:vertical   {{ height: 3px; }}
QSplitter::handle:hover      {{ background-color: {p.accent}; }}

/* ── Text editors ─────────────────────────────────────────────────── */
QTextEdit,
QPlainTextEdit {{
    background-color: {p.bg_darkest};
    color: {p.fg_primary};
    border: 1px solid {p.border};
    border-radius: 4px;
    selection-background-color: {p.border_light};
    font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
    font-size: 13px;
}}
QTextEdit:focus,
QPlainTextEdit:focus {{
    border-color: {p.accent};
}}

/* ── Buttons ──────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {p.bg_light};
    color: {p.fg_primary};
    border: 1px solid {p.border_light};
    border-radius: 5px;
    padding: 4px 14px;
    font-size: 12px;
}}
QPushButton:hover  {{ background-color: {p.border_light}; border-color: {p.accent}; }}
QPushButton:pressed {{ background-color: {p.bg_medium}; }}
QPushButton:disabled {{ color: {p.fg_dim}; border-color: {p.border}; }}

/* ── Status bar ───────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {p.bg_medium};
    color: {p.fg_secondary};
    border-top: 1px solid {p.border};
    font-size: 11px;
}}

/* ── Scroll bars ──────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {p.bg_dark};
    width: 10px;
    border-radius: 5px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p.border_light};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {p.fg_dim}; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {p.bg_dark};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {p.border_light};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {p.fg_dim}; }}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Dialog / Spin-boxes ──────────────────────────────────────────── */
QDialog {{
    background-color: {p.bg_dark};
}}
QDoubleSpinBox,
QSpinBox {{
    background-color: {p.bg_darkest};
    color: {p.fg_primary};
    border: 1px solid {p.border};
    border-radius: 4px;
    padding: 3px 6px;
}}
QDoubleSpinBox:focus,
QSpinBox:focus {{ border-color: {p.accent}; }}

QLabel {{ color: {p.fg_primary}; }}

QDialogButtonBox QPushButton {{ min-width: 72px; }}

/* ── Completer / List views ───────────────────────────────────────── */
QListView {{
    background-color: {p.bg_medium};
    color: {p.fg_primary};
    border: 1px solid {p.border_light};
    border-radius: 4px;
    padding: 2px;
    outline: none;
}}
QListView::item {{ padding: 3px 8px; border-radius: 3px; }}
QListView::item:selected {{ background-color: {p.bg_light}; color: {p.accent}; }}
QListView::item:hover {{ background-color: {p.bg_darkest}; }}

/* ── Tooltips ─────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {p.bg_medium};
    color: {p.fg_primary};
    border: 1px solid {p.border_light};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ── Combo box ────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {p.bg_darkest};
    color: {p.fg_primary};
    border: 1px solid {p.border};
    border-radius: 4px;
    padding: 3px 8px;
}}
QComboBox:focus {{ border-color: {p.accent}; }}
QComboBox::drop-down {{
    border: none;
    background: transparent;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {p.bg_medium};
    color: {p.fg_primary};
    border: 1px solid {p.border_light};
    selection-background-color: {p.bg_light};
    selection-color: {p.accent};
    border-radius: 4px;
}}

/* ── Line edit ────────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {p.bg_darkest};
    color: {p.fg_primary};
    border: 1px solid {p.border};
    border-radius: 4px;
    padding: 3px 6px;
}}
QLineEdit:focus {{ border-color: {p.accent}; }}

/* ── List widget ──────────────────────────────────────────────────── */
QListWidget {{
    background-color: {p.bg_darkest};
    color: {p.fg_primary};
    border: 1px solid {p.border};
    border-radius: 4px;
    outline: none;
}}
QListWidget::item {{ padding: 4px 8px; border-radius: 3px; }}
QListWidget::item:selected {{ background-color: {p.bg_light}; color: {p.accent}; }}
QListWidget::item:hover {{ background-color: {p.bg_dark}; }}

/* ── Group box ────────────────────────────────────────────────────── */
QGroupBox {{
    color: {p.accent};
    border: 1px solid {p.border};
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 12px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}

/* ── Tab widget ───────────────────────────────────────────────────── */
QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: 4px; }}
QTabBar::tab {{
    background-color: {p.bg_medium};
    color: {p.fg_secondary};
    border: 1px solid {p.border};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 5px 14px;
}}
QTabBar::tab:selected {{ background-color: {p.bg_dark}; color: {p.accent}; }}
QTabBar::tab:hover {{ background-color: {p.bg_light}; }}

/* ── Progress bar ─────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {p.bg_darkest};
    border: 1px solid {p.border};
    border-radius: 4px;
    text-align: center;
    color: {p.fg_primary};
}}
QProgressBar::chunk {{
    background-color: {p.accent};
    border-radius: 3px;
}}

/* ── Tab bar close button ─────────────────────────────────────────── */
QTabBar::close-button {{
    image: none;
    subcontrol-position: right;
}}
QTabBar::close-button:hover {{
    background: {p.bg_light};
    border-radius: 3px;
}}
"""


# ── Theme Manager ─────────────────────────────────────────────────────


class ThemeManager:
    """Holds the active palette and notifies listeners on change."""

    def __init__(self) -> None:
        self._palette: Palette = CATPPUCCIN_MOCHA
        self._listeners: list[Callable[[Palette], None]] = []

    @property
    def palette(self) -> Palette:
        return self._palette

    @property
    def current_name(self) -> str:
        return self._palette.name

    def add_listener(self, fn: Callable[[Palette], None]) -> None:
        """Register *fn* to be called with the new palette on theme changes."""
        self._listeners.append(fn)

    def apply_theme(self, name: str, app: object | None = None) -> None:
        """Switch to the named theme and notify all listeners.

        Parameters
        ----------
        name:
            Key in ``THEMES``.
        app:
            The ``QApplication`` — its stylesheet is updated automatically.
        """
        if name not in THEMES:
            return
        self._palette = THEMES[name]
        qss = generate_stylesheet(self._palette)
        if app is not None and hasattr(app, "setStyleSheet"):
            app.setStyleSheet(qss)
        for fn in self._listeners:
            fn(self._palette)
