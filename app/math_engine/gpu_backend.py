"""GPU-accelerated numerical backend.

Uses CuPy when available (NVIDIA CUDA GPU), falls back to NumPy.
Large-array operations are transparently accelerated when a GPU is present.

Usage
-----
    from app.math_engine.gpu_backend import xp, to_gpu, to_cpu, gpu_available

    # Transparent — works with both numpy and cupy arrays:
    result = xp.fft.fft(data)

    # Explicit GPU transfer for large computations:
    d = to_gpu(large_array)
    result = to_cpu(xp.linalg.inv(d))
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Try to import CuPy (CUDA GPU acceleration)
# ---------------------------------------------------------------------------

try:
    import cupy as cp  # type: ignore[import-untyped]

    GPU_AVAILABLE: bool = True
except ImportError:
    cp = None  # type: ignore[assignment]
    GPU_AVAILABLE = False


def gpu_available() -> bool:
    """Return ``True`` if CuPy is installed and a CUDA GPU is accessible."""
    if not GPU_AVAILABLE:
        return False
    try:
        cp.cuda.runtime.getDeviceCount()
        return True
    except Exception:  # noqa: BLE001
        return False


# ``xp`` is the active array module — CuPy on GPU machines, NumPy otherwise.
xp = cp if gpu_available() else np


# ---------------------------------------------------------------------------
# Transfer helpers
# ---------------------------------------------------------------------------

_GPU_THRESHOLD: int = 5000  # auto-offload arrays larger than this


def to_gpu(a: np.ndarray) -> "np.ndarray | cp.ndarray":
    """Move *a* to GPU memory if available and array is large enough."""
    if gpu_available() and np.asarray(a).size >= _GPU_THRESHOLD:
        return cp.asarray(a)
    return np.asarray(a)


def to_cpu(a: "np.ndarray | cp.ndarray") -> np.ndarray:
    """Ensure *a* is a NumPy array on CPU memory."""
    if gpu_available() and hasattr(a, "get"):
        return a.get()
    return np.asarray(a)


def auto(a: np.ndarray) -> "np.ndarray | cp.ndarray":
    """Automatically decide whether to use GPU for *a*."""
    return to_gpu(a)


# ---------------------------------------------------------------------------
# GPU-accelerated wrappers for key operations
# ---------------------------------------------------------------------------

def gpu_fft(v: np.ndarray) -> np.ndarray:
    """FFT with GPU acceleration for large arrays."""
    d = to_gpu(v)
    module = cp if (gpu_available() and hasattr(d, "get")) else np
    result = module.abs(module.fft.fft(d))
    return to_cpu(result)


def gpu_matmul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Matrix multiply with GPU acceleration."""
    da, db = to_gpu(a), to_gpu(b)
    module = cp if (gpu_available() and hasattr(da, "get")) else np
    return to_cpu(module.matmul(da, db))


def gpu_det(m: np.ndarray) -> float:
    """Determinant with GPU acceleration."""
    d = to_gpu(m)
    module = cp if (gpu_available() and hasattr(d, "get")) else np
    return float(to_cpu(module.linalg.det(d)))


def gpu_inv(m: np.ndarray) -> np.ndarray:
    """Matrix inverse with GPU acceleration."""
    d = to_gpu(m)
    module = cp if (gpu_available() and hasattr(d, "get")) else np
    return to_cpu(module.linalg.inv(d))


def gpu_eig(m: np.ndarray) -> np.ndarray:
    """Eigenvalues with GPU acceleration."""
    d = to_gpu(m)
    module = cp if (gpu_available() and hasattr(d, "get")) else np
    return to_cpu(module.linalg.eigvals(d))


def gpu_svd(m: np.ndarray) -> np.ndarray:
    """SVD singular values with GPU acceleration."""
    d = to_gpu(m)
    module = cp if (gpu_available() and hasattr(d, "get")) else np
    return to_cpu(module.linalg.svd(d, compute_uv=False))


def gpu_solve(A: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Solve linear system with GPU acceleration."""
    dA, db = to_gpu(A), to_gpu(b)
    module = cp if (gpu_available() and hasattr(dA, "get")) else np
    return to_cpu(module.linalg.solve(dA, db))


# ---------------------------------------------------------------------------
# Info helper
# ---------------------------------------------------------------------------

def gpu_info() -> str:
    """Return a human-readable string about the GPU status."""
    if not GPU_AVAILABLE:
        return "GPU: Not available (CuPy not installed)\n  Install: pip install cupy-cuda12x"
    if not gpu_available():
        return "GPU: CuPy installed but no CUDA device found"
    dev = cp.cuda.Device()
    props = cp.cuda.runtime.getDeviceProperties(dev.id)
    name = props["name"].decode() if isinstance(props["name"], bytes) else props["name"]
    mem = props["totalGlobalMem"] / (1024**3)
    return f"GPU: {name}  ({mem:.1f} GB)  —  CUDA acceleration active"
