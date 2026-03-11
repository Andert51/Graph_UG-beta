"""GraphUG syntax highlighter for the editor panel.

Applies token-level colouring to the ``QPlainTextEdit`` editor using
``QSyntaxHighlighter``.  Rules are prioritised: later rules can override
earlier ones for the same span.

Colour palette: Catppuccin Mocha.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument


class GraphUGHighlighter(QSyntaxHighlighter):
    """Regex-based syntax highlighter for the GraphUG mathematical language."""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._rules: list[tuple[re.Pattern[str], QTextCharFormat]] = []
        self._build_rules()

    def _build_rules(self) -> None:
        def _fmt(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            if italic:
                f.setProperty(QTextCharFormat.Property.FontItalic, True)
            return f

        # Comments (#...)
        self._rules.append((re.compile(r"#.*$"), _fmt("#6c7086", italic=True)))

        # Strings ("..." or '...')
        self._rules.append((re.compile(r'"[^"]*"|\'[^\']*\''), _fmt("#a6e3a1")))

        # Numbers (integers, floats, scientific)
        self._rules.append((re.compile(r"\b[0-9]+(\.[0-9]*)?([eE][+-]?[0-9]+)?\b"), _fmt("#fab387")))

        # Keywords / logical
        self._rules.append((re.compile(r"\b(and|or|not)\b"), _fmt("#cba6f7", bold=True)))

        # Built-in constants
        self._rules.append((
            re.compile(r"\b(pi|e|inf|nan|true|false)\b"),
            _fmt("#f9e2af"),
        ))

        # Built-in functions
        builtins = (
            r"\b(sin|cos|tan|asin|acos|atan|atan2|sinh|cosh|tanh|"
            r"sqrt|exp|log|log2|log10|abs|ceil|floor|round|"
            r"linspace|arange|zeros|ones|eye|"
            r"dot|cross|norm|det|inv|transpose|"
            r"sum|mean|min|max|std|var|len|reshape|"
            r"typeof|size|"
            r"simplify|factor|expand|diff|integrate|solve|"
            r"plot|scatter|vector|bar|hist|"
            r"xlabel|ylabel|title|grid|hold)\b"
        )
        self._rules.append((re.compile(builtins), _fmt("#89b4fa")))

        # Assignment operator
        self._rules.append((re.compile(r"(?<!=)=(?!=)"), _fmt("#f5c2e7", bold=True)))

        # Operators
        self._rules.append((re.compile(r"[+\-*/%^]|==|!=|<=|>=|<|>"), _fmt("#89dceb")))

        # Brackets
        self._rules.append((re.compile(r"[(){}\[\]]"), _fmt("#f5e0dc")))

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)
