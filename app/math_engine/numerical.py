"""Numerical computation helpers built on top of NumPy.

These functions are exposed to the GraphUG language as named built-ins
(seeded into ``MathEvaluator._BUILTINS``).  Place any higher-level
convenience wrappers here; keep raw NumPy calls in the evaluator.
"""

from __future__ import annotations

import numpy as np


def linspace(start: float, stop: float, num: float = 50) -> np.ndarray:
    """Return *num* evenly spaced values over [*start*, *stop*].

    Accepts ``float`` for *num* and silently truncates to ``int``, matching
    MATLAB's implicit coercion behaviour.
    """
    return np.linspace(start, stop, int(num))


def arange(start: float, stop: float, step: float = 1.0) -> np.ndarray:
    """Return values in [*start*, *stop*) spaced by *step*."""
    return np.arange(start, stop, step)


def norm(v: np.ndarray, order: float | None = None) -> float:
    """Return the vector norm of *v* (defaults to Euclidean / L2)."""
    return float(np.linalg.norm(v, ord=order))


def dot(a: np.ndarray, b: np.ndarray) -> float | np.ndarray:
    """Return the dot product of *a* and *b*."""
    return np.dot(a, b)


def cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Return the cross product of 3-D vectors *a* and *b*."""
    return np.cross(a, b)
