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
            re.compile(r"\b(pi|e|inf|nan|true|false|phi|tau|euler_gamma)\b"),
            _fmt("#f9e2af"),
        ))

        # Built-in functions
        builtins = (
            r"\b(sin|cos|tan|asin|acos|atan|atan2|sinh|cosh|tanh|"
            r"asinh|acosh|atanh|sec|csc|cot|sinc|deg2rad|rad2deg|"
            r"sqrt|cbrt|exp|exp2|expm1|log|log2|log10|log1p|abs|ceil|floor|round|"
            r"sign|clip|mod|gcd|lcm|factorial|comb|perm|hypot|"
            r"linspace|arange|logspace|zeros|ones|eye|diag|full|"
            r"rand|randn|randint|meshgrid|flatten|sort|unique|reverse|"
            r"concat|stack|tile|repeat|"
            r"dot|cross|norm|det|inv|transpose|trace|rank|"
            r"eig|eigvals|svd|pinv|solve_linear|lu|qr|cholesky|"
            r"cond|outer|inner|kron|matmul|"
            r"sum|mean|min|max|std|var|len|reshape|"
            r"median|percentile|cumsum|cumprod|prod|argmin|argmax|"
            r"histogram|corrcoef|cov|"
            r"typeof|size|ndim|isnan|isinf|"
            r"where|interp|gradient|diff_array|trapz|"
            r"polyfit|polyval|roots|convolve|fft|ifft|fftfreq|"
            r"magnitude|normalize|angle|proj|reject|"
            r"simplify|factor|expand|diff|integrate|solve|"
            r"limit|series|partial|taylor|defint|"
            r"summation|product|nsolve|"
            r"gradient|divergence|curl|laplacian|"
            r"laplace|invlaplace|"
            r"rref|nullspace|colspace|"
            r"plot|scatter|vector|bar|hist|"
            r"fplot|polar|parametric|parametric3d|"
            r"surface|wireframe|"
            r"plotderiv|plotintegral|tangentline|"
            r"implicit|contour|slopefield|"
            r"heatmap|vectorfield|stem|step|pie|errorbar|"
            r"scatter3d|surfparam|bar3d|"
            r"logplot|semilogx|semilogy|area|"
            r"complex|real|imag|conj|phase|"
            r"vander|toeplitz|hilbert|companion|triu|tril|block_diag|"
            r"fftshift|rfft|fft2|hamming|hanning|blackman|kaiser|"
            r"union|intersect|setdiff|in1d|"
            r"cummax|cummin|movmean|"
            r"bitand|bitor|bitxor|bitnot|shl|shr|"
            r"map_arr|linreg|spline_interp|"
            r"gpuinfo|"
            r"xlabel|ylabel|title|grid|hold|help)\b"
        )
        self._rules.append((re.compile(builtins), _fmt("#89b4fa")))

        # Assignment operator
        self._rules.append((re.compile(r"(?<!=)=(?!=)"), _fmt("#f5c2e7", bold=True)))

        # Operators
        self._rules.append((re.compile(r"[+\-*/%^]|==|!=|<=|>=|<|>|\|>|\?|:"), _fmt("#89dceb")))

        # Brackets
        self._rules.append((re.compile(r"[(){}\[\]]"), _fmt("#f5e0dc")))

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)
