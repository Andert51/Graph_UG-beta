"""Autocomplete popup for the GraphUG code editor.

Provides an inline suggestion list that appears as the user types,
offering all built-in functions, constants, and plot commands.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QStringListModel, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QCompleter,
    QListView,
    QPlainTextEdit,
)

# All completable tokens — functions, constants, commands, keywords
COMPLETIONS: list[str] = sorted({
    # Trig
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "sec", "csc", "cot", "sinc", "deg2rad", "rad2deg",
    # Transcendentals / math
    "sqrt", "cbrt", "exp", "exp2", "expm1",
    "log", "log2", "log10", "log1p",
    "abs", "ceil", "floor", "round",
    "sign", "clip", "mod", "gcd", "lcm",
    "factorial", "comb", "perm", "hypot",
    # Array constructors
    "linspace", "arange", "logspace",
    "zeros", "ones", "eye", "diag", "full",
    "rand", "randn", "randint",
    "meshgrid", "flatten", "sort", "unique", "reverse",
    "concat", "stack", "tile", "repeat",
    # Linear algebra
    "dot", "cross", "norm", "det", "inv", "transpose",
    "trace", "rank", "eig", "eigvals", "svd", "pinv",
    "solve_linear", "lu", "qr", "cholesky",
    "cond", "outer", "inner", "kron", "matmul",
    # Stats
    "sum", "mean", "min", "max", "std", "var", "len", "reshape",
    "median", "percentile", "cumsum", "cumprod", "prod",
    "argmin", "argmax", "histogram", "corrcoef", "cov",
    # Introspection
    "typeof", "size", "ndim", "isnan", "isinf",
    # Utility / numerical
    "where", "interp", "gradient", "diff_array", "trapz",
    "polyfit", "polyval", "roots", "convolve",
    "fft", "ifft", "fftfreq",
    # Vector calculus (numeric)
    "magnitude", "normalize", "angle", "proj", "reject",
    # Symbolic algebra
    "simplify", "factor", "expand", "diff", "integrate", "solve",
    # Symbolic calculus
    "limit", "series", "partial", "taylor", "defint",
    "summation", "product", "nsolve",
    # Symbolic vector calculus
    "divergence", "curl", "laplacian",
    # Transforms
    "laplace", "invlaplace",
    # Symbolic linear algebra
    "rref", "nullspace", "colspace",
    # Basic plot
    "plot", "scatter", "vector", "bar", "hist",
    # Advanced plot
    "fplot", "polar", "parametric", "parametric3d",
    "surface", "wireframe",
    "plotderiv", "plotintegral", "tangentline",
    "implicit", "contour", "slopefield",
    # Phase 7 — new plot commands
    "heatmap", "vectorfield", "stem", "step", "pie", "errorbar",
    "scatter3d", "surfparam", "bar3d",
    "logplot", "semilogx", "semilogy", "area",
    # Phase 7 — complex numbers
    "complex", "real", "imag", "conj", "phase",
    # Phase 7 — special matrices
    "vander", "toeplitz", "hilbert", "companion", "triu", "tril", "block_diag",
    # Phase 7 — extended signal processing
    "fftshift", "rfft", "fft2", "hamming", "hanning", "blackman", "kaiser",
    # Phase 7 — set operations
    "union", "intersect", "setdiff", "in1d",
    # Phase 7 — cumulative / moving
    "cummax", "cummin", "movmean",
    # Phase 7 — bitwise
    "bitand", "bitor", "bitxor", "bitnot", "shl", "shr",
    # Phase 7 — functional / regression
    "map_arr", "linreg", "spline_interp",
    # Phase 7 — GPU
    "gpuinfo",
    # Canvas
    "xlabel", "ylabel", "title", "grid", "hold", "help",
    # Constants
    "pi", "e", "inf", "nan", "true", "false",
    "phi", "tau", "euler_gamma",
    # Keywords
    "and", "or", "not",
})

_POPUP_STYLE = """
QListView {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 2px;
    font-family: "Cascadia Code", "Fira Code", monospace;
    font-size: 12px;
    outline: none;
}
QListView::item {
    padding: 3px 8px;
    border-radius: 3px;
}
QListView::item:selected {
    background-color: #313244;
    color: #89b4fa;
}
QListView::item:hover {
    background-color: #11111b;
}
"""


def attach_completer(editor: QPlainTextEdit) -> QCompleter:
    """Create and attach an autocomplete ``QCompleter`` to *editor*.

    Returns the completer instance (kept alive by Qt parent ownership).
    """
    model = QStringListModel(COMPLETIONS, editor)

    completer = QCompleter(model, editor)
    completer.setWidget(editor)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    completer.setMaxVisibleItems(10)

    # Style the popup list
    popup: QListView = completer.popup()  # type: ignore[assignment]
    popup.setStyleSheet(_POPUP_STYLE)
    font = QFont("Cascadia Code", 12)
    font.setStyleHint(QFont.StyleHint.Monospace)
    popup.setFont(font)

    # Wire insertion
    completer.activated.connect(lambda text: _insert_completion(editor, completer, text))

    return completer


def update_completions(editor: QPlainTextEdit, completer: QCompleter) -> None:
    """Recompute the prefix under the cursor and show/hide the popup."""
    prefix = _current_word(editor)
    if len(prefix) < 2:
        completer.popup().hide()
        return

    completer.setCompletionPrefix(prefix)
    if completer.completionCount() == 0:
        completer.popup().hide()
        return

    # If the only match IS the prefix itself, hide
    if (
        completer.completionCount() == 1
        and completer.currentCompletion() == prefix
    ):
        completer.popup().hide()
        return

    # Position popup under the cursor
    cr = editor.cursorRect()
    cr.setWidth(
        min(300, completer.popup().sizeHintForColumn(0) + 30)
    )
    completer.complete(cr)


def _current_word(editor: QPlainTextEdit) -> str:
    """Extract the identifier fragment immediately before the cursor."""
    cursor = editor.textCursor()
    pos = cursor.positionInBlock()
    text = cursor.block().text()
    start = pos
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
        start -= 1
    return text[start:pos]


def _insert_completion(editor: QPlainTextEdit, completer: QCompleter, text: str) -> None:
    """Replace the current partial word with the selected completion."""
    cursor = editor.textCursor()
    prefix_len = len(completer.completionPrefix())
    # Remove the already-typed prefix, then insert full text
    for _ in range(prefix_len):
        cursor.deletePreviousChar()
    cursor.insertText(text)
    editor.setTextCursor(cursor)
