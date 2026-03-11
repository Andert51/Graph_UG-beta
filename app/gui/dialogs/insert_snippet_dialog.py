"""Insert Snippet dialog — quick-insertion for common math patterns.

Provides a filterable list of ready-to-use code snippets that the user
can insert into the editor with one click.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

_SNIPPETS: list[tuple[str, str]] = [
    # ── Linear algebra ──
    ("Identity matrix 3×3", "eye(3)"),
    ("Zeros matrix 3×3", "zeros(3, 3)"),
    ("Ones matrix 2×4", "ones(2, 4)"),
    ("Diagonal matrix", "diag([1, 2, 3])"),
    ("Random 3×3 matrix", "rand(3, 3)"),
    ("Determinant", "det([1,2;3,4])"),
    ("Inverse", "inv([1,2;3,4])"),
    ("Eigenvalues", "eigvals([2,1;1,2])"),
    ("Solve Ax = b", "solve_linear([1,2;3,4], [5, 6])"),
    ("Matrix multiply", "matmul([1,2;3,4], [5;6])"),
    ("SVD decomposition", "svd([1,2;3,4])"),
    ("QR decomposition", "qr([1,2;3,4])"),
    ("RREF (symbolic)", 'rref("[1,2,3;4,5,6]")'),
    ("Vandermonde matrix", "vander([1, 2, 3, 4])"),
    ("Toeplitz matrix", "toeplitz([1, 2, 3, 4])"),
    ("Hilbert matrix 4×4", "hilbert(4)"),
    ("Upper triangular", "triu([1,2;3,4])"),
    ("Lower triangular", "tril([1,2;3,4])"),
    # ── Calculus ──
    ("Derivative of x³", 'diff("x^3", "x")'),
    ("Second derivative", 'diff("sin(x)", "x", 2)'),
    ("Integral of x²", 'integrate("x^2", "x")'),
    ("Definite integral ∫₀¹ x² dx", 'defint("x^2", "x", 0, 1)'),
    ("Limit sin(x)/x as x→0", 'limit("sin(x)/x", "x", 0)'),
    ("Taylor sin(x) order 7", 'taylor("sin(x)", "x", 0, 7)'),
    ("Series expansion eˣ", 'series("exp(x)", "x", 0, 6)'),
    ("Partial ∂/∂x of x²y", 'partial("x^2*y", "x")'),
    ("Summation Σ k² (1..10)", 'summation("k^2", "k", 1, 10)'),
    ("Product Π k (1..5)", 'product("k", "k", 1, 5)'),
    # ── Vector calculus ──
    ("Gradient ∇(x²+y²+z²)", 'gradient("x^2+y^2+z^2", "x,y,z")'),
    ("Divergence ∇·F", 'divergence("x^2, y^2, z^2", "x,y,z")'),
    ("Curl ∇×F", 'curl("-y, x, 0", "x,y,z")'),
    ("Laplacian ∇²f", 'laplacian("x^2+y^2", "x,y")'),
    # ── Transforms ──
    ("Laplace transform", 'laplace("exp(-a*t)", "t", "s")'),
    ("Inverse Laplace", 'invlaplace("1/(s+a)", "s", "t")'),
    # ── Statistics ──
    ("Mean of data", "mean([1, 2, 3, 4, 5])"),
    ("Standard deviation", "std([1, 2, 3, 4, 5])"),
    ("Median", "median([3, 1, 4, 1, 5])"),
    ("Correlation matrix", "corrcoef([1,2,3;4,5,6])"),
    ("Histogram", "histogram([1, 1, 2, 3, 3, 3], 3)"),
    # ── Signal processing ──
    ("FFT", "fft([1, 0, -1, 0])"),
    ("Inverse FFT", "ifft(fft([1, 0, -1, 0]))"),
    ("FFT shift", "fftshift(fft([1, 0, -1, 0]))"),
    ("Real FFT", "rfft([1, 0, -1, 0])"),
    ("Convolution", "convolve([1, 2, 3], [0, 1, 0.5])"),
    ("Hamming window", "hamming(64)"),
    ("Hanning window", "hanning(64)"),
    ("Blackman window", "blackman(64)"),
    # ── Polynomial ──
    ("Polynomial fit (degree 2)", "polyfit([0,1,2,3], [0,1,4,9], 2)"),
    ("Polynomial evaluation", "polyval([1, 0, -1], 2)"),
    ("Polynomial roots", "roots([1, 0, -1])"),
    # ── Complex numbers ──
    ("Complex number", "complex(3, 4)"),
    ("Real part", "real(complex(3, 4))"),
    ("Imaginary part", "imag(complex(3, 4))"),
    ("Conjugate", "conj(complex(3, 4))"),
    ("Phase angle", "phase(complex(3, 4))"),
    # ── Bitwise operations ──
    ("Bitwise AND", "bitand(12, 10)"),
    ("Bitwise OR", "bitor(12, 10)"),
    ("Bitwise XOR", "bitxor(12, 10)"),
    ("Left shift", "shl(1, 4)"),
    # ── Set operations ──
    ("Union", "union([1,2,3], [3,4,5])"),
    ("Intersection", "intersect([1,2,3], [2,3,4])"),
    ("Set difference", "setdiff([1,2,3], [2,3,4])"),
    # ── Plotting quick-starts ──
    ("Plot sin(x)", 'fplot("sin(x)")'),
    ("Polar rose r = cos(3t)", 'polar("cos(3*t)")'),
    ("3D surface sin·cos", 'surface("sin(x)*cos(y)")'),
    ("Slope field dy/dx = y − x", 'slopefield("y - x")'),
    ("Parametric circle", 'parametric("cos(t)", "sin(t)")'),
    # ── Phase 7 plot commands ──
    ("Heatmap", "Z = rand(10, 10); heatmap(Z)"),
    ("Stem plot", "x = linspace(0, 10, 20); stem(x, sin(x))"),
    ("Step plot", "x = linspace(0, 10, 20); step(x, sin(x))"),
    ("Error bars", "x = [1,2,3,4,5]; errorbar(x, x^2, [1,2,1,2,1])"),
    ("Scatter 3D", "scatter3d(rand(50), rand(50), rand(50))"),
    ("3D parametric surface", 'surfparam("cos(u)*sin(v)", "sin(u)*sin(v)", "cos(v)")'),
    ("Log-log plot", "x = logspace(0, 3, 50); logplot(x, x^2)"),
    ("Area plot", "x = linspace(0, 10, 50); area(x, sin(x))"),
    ("GPU info", "gpuinfo()"),
    # ── Solve ──
    ("Solve x² − 4 = 0", 'solve("x^2 - 4", "x")'),
    ("Numerical solve cos(x) = x", 'nsolve("cos(x) - x", "x", 1)'),
    ("Simplify expression", 'simplify("(x^2 - 1)/(x - 1)")'),
    ("Factor expression", 'factor("x^2 - 5*x + 6")'),
    ("Linear regression", "linreg([1,2,3,4,5], [2.1, 3.9, 6.2, 7.8, 10.1])"),
]


class InsertSnippetDialog(QDialog):
    """Dialog with a filterable list of ready-to-use code snippets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Snippet")
        self.setFixedSize(480, 420)
        self.command: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Search / filter
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter snippets…")
        self._filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        # Snippet list
        self._list = QListWidget()
        for label, code in _SNIPPETS:
            item = QListWidgetItem(f"{label}  →  {code}")
            item.setData(Qt.ItemDataRole.UserRole, code)
            self._list.addItem(item)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list)

        # Preview
        self._preview = QLabel()
        self._preview.setStyleSheet(
            "background:#11111b; color:#89b4fa; padding:6px; "
            "border:1px solid #313244; border-radius:4px; font-family:monospace;"
        )
        self._preview.setWordWrap(True)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._preview)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_filter(self, text: str) -> None:
        text_lower = text.lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None:
                item.setHidden(text_lower not in item.text().lower())

    def _on_selection_changed(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if current:
            self._preview.setText(current.data(Qt.ItemDataRole.UserRole))
        else:
            self._preview.setText("")

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self.command = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _on_accept(self) -> None:
        current = self._list.currentItem()
        if current:
            self.command = current.data(Qt.ItemDataRole.UserRole)
        self.accept()
