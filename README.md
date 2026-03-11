# GraphUG — Interactive Mathematical Environment

A desktop application that works as an **interactive mathematical environment and graphing calculator** — a simplified, modern, open-source alternative inspired by MATLAB.

Built with **PySide6** (GUI), **PyQtGraph** (plotting), **Lark** (LALR parser), **NumPy** (numerical), and **SymPy** (symbolic algebra).

---

## Features

| Category | Capabilities |
|---|---|
| **Arithmetic** | `+`, `-`, `*`, `/`, `%`, `^` (right-associative), unary `-`/`+`, parentheses |
| **Comparisons** | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| **Variables** | `x = 42`, `y = x^2 + 1` — persistent across evaluations |
| **Vectors** | `[1, 2, 3]` — NumPy array literals |
| **Matrices** | `[1, 2; 3, 4]` — semicolons separate rows |
| **Functions** | 40+ builtins — trig, hyperbolic, rounding, linear algebra, statistics |
| **Plotting** | `plot()`, `scatter()`, `vector()`, `bar()`, `hist()` |
| **Symbolic** | `simplify()`, `factor()`, `expand()`, `diff()`, `integrate()`, `solve()` |
| **Strings** | `"expr"` / `'expr'` — used as arguments for symbolic functions |
| **Multi-statement** | Semicolons separate statements: `a = 1; b = 2; a + b` |
| **Comments** | Lines starting with `#` are skipped |

### Built-in Functions

```
# Trigonometric
sin  cos  tan  asin  acos  atan  atan2

# Hyperbolic
sinh  cosh  tanh

# Power / Log
sqrt  exp  log  log2  log10  abs

# Rounding
ceil  floor  round

# Array constructors
linspace(start, end, n)    arange(start, end, step)
zeros(n)    ones(n)    eye(n)

# Linear algebra
dot  cross  norm  det  inv  transpose

# Statistics
sum  mean  min  max  std  var  len  reshape

# Constants
pi  e  inf  nan  true  false
```

### Symbolic Algebra (SymPy)

Functions accept string expressions using Python math syntax:

```
simplify("sin(x)**2 + cos(x)**2")   →  1
factor("x**2 - 1")                  →  (x - 1)*(x + 1)
expand("(x + 1)**2")                →  x**2 + 2*x + 1
diff("x**3", "x")                   →  3*x**2
integrate("x**2", "x")              →  x**3/3
solve("x**2 - 4", "x")             →  -2, 2
```

### Plotting

```
x = linspace(0, 2*pi, 200)
plot(x, sin(x))           # Line plot
scatter([1,2,3], [4,5,6]) # Scatter plot
vector(3, 4)               # 2D vector from origin
vector(1, 1, 3, 4)         # 2D vector from (1,1)
bar([5, 10, 15])           # Bar chart
hist([1, 2, 2, 3, 3, 3])  # Histogram
```

---

## Architecture

Strict **MVC / Clean Architecture** with dependency injection:

```
app/
├── core/              # Domain layer (no external imports)
│   ├── interfaces/    #   ABC: IEvaluator, IRenderer, IController
│   ├── models/        #   DTOs: MathResult, PlotCommand, Expression
│   └── exceptions/    #   Custom errors (ParseError, EvaluationError …)
├── parser/            # Infrastructure: Lark grammar + MathEvaluator
│   ├── grammar/       #   math_grammar.lark (LALR)
│   ├── ast_nodes.py   #   Typed AST node dataclasses
│   └── evaluator.py   #   Concrete IEvaluator implementation
├── renderer/          # Infrastructure: PyQtGraph renderer
├── math_engine/       # Helpers: numerical.py, symbolic.py
├── gui/               # View layer: PySide6 widgets
│   ├── main_window.py #   Application shell
│   ├── widgets/       #   EditorPanel, CanvasPanel
│   ├── dialogs/       #   InsertVector, InsertMatrix, About
│   └── styles/        #   Dark theme (Catppuccin Mocha)
├── controllers/       # Application layer: MainController
└── utils/             # Logger (rotating file + stderr)
main.py                # Entry point — DI wiring
```

**Data flow:** `EditorPanel.input_submitted` → `MainController.handle_input` → `MathEvaluator.evaluate()` → `PyQtGraphRenderer.render()` → signals back to `MainWindow`.

---

## Installation

```bash
# Clone
git clone https://github.com/Andert51/Graph_UG-beta.git
cd Graph_UG-beta

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

**Keyboard shortcuts:**

| Shortcut | Action |
|---|---|
| `Shift+Enter` | Evaluate editor content |
| `Ctrl+Up` / `Ctrl+Down` | Navigate command history |
| `Ctrl+N` | New session |
| `Ctrl+E` | Export canvas to PNG |
| `Ctrl+L` | Clear output console |
| `Ctrl+Shift+L` | Clear canvas |
| `Ctrl+1` / `Ctrl+2` | Toggle editor / canvas |
| `Ctrl+Shift+V` | Insert Vector dialog |
| `Ctrl+Shift+M` | Insert Matrix dialog |

## Running Tests

```bash
python -m pytest tests/ -v
```

126 tests covering: arithmetic, variables, builtins, vectors, matrices, comparisons, modulo, semicolons, strings, symbolic algebra, plot commands, models, numerical helpers.

---

## Stack

- **Python** 3.12+
- **PySide6** — Qt6 GUI framework
- **PyQtGraph** — high-performance plotting
- **Lark** — LALR(1) parser generator
- **NumPy** — numerical computation
- **SymPy** — symbolic algebra
- **pytest** — test framework

## License

MIT
