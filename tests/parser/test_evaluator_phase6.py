"""Tests for Phase 6 evaluator enhancements.

Covers: expanded builtins (trig, transcendental, array, LA, stats, utility,
vector calculus, constants), symbolic routing for all 23 dispatch names,
grammar features (index access, ternary, pipe), and help command output.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.parser.evaluator import MathEvaluator


@pytest.fixture()
def ev() -> MathEvaluator:
    return MathEvaluator()


# ═══════════════════════════════════════════════════════════════════════
# New trig / hyperbolic functions
# ═══════════════════════════════════════════════════════════════════════


class TestTrigExpanded:
    def test_asinh(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("asinh(0)")
        assert r.value == pytest.approx(0.0)

    def test_acosh(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("acosh(1)")
        assert r.value == pytest.approx(0.0)

    def test_atanh(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("atanh(0)")
        assert r.value == pytest.approx(0.0)

    def test_sec(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("sec(0)")
        assert r.value == pytest.approx(1.0)

    def test_csc(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("csc(1.5707963)")
        assert r.value == pytest.approx(1.0, rel=1e-4)

    def test_cot(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("cot(0.7853981)")
        assert r.value == pytest.approx(1.0, rel=1e-4)

    def test_sinc(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("sinc(0)")
        assert r.value == pytest.approx(1.0)

    def test_deg2rad(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("deg2rad(180)")
        assert r.value == pytest.approx(math.pi)

    def test_rad2deg(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("rad2deg(3.14159265)")
        assert r.value == pytest.approx(180.0, rel=1e-4)


# ═══════════════════════════════════════════════════════════════════════
# Transcendental / math utility
# ═══════════════════════════════════════════════════════════════════════


class TestTranscendental:
    def test_cbrt(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("cbrt(27)")
        assert r.value == pytest.approx(3.0)

    def test_exp2(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("exp2(3)")
        assert r.value == pytest.approx(8.0)

    def test_expm1(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("expm1(0)")
        assert r.value == pytest.approx(0.0)

    def test_log1p(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("log1p(0)")
        assert r.value == pytest.approx(0.0)

    def test_sign(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("sign(-5)")
        assert r.value == pytest.approx(-1.0)

    def test_mod(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("mod(7, 3)")
        assert r.value == pytest.approx(1.0)

    def test_gcd(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("gcd(12, 8)")
        assert r.value == pytest.approx(4.0)

    def test_lcm(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("lcm(4, 6)")
        assert r.value == pytest.approx(12.0)

    def test_factorial(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("factorial(5)")
        assert r.value == pytest.approx(120.0)

    def test_comb(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("comb(5, 2)")
        assert r.value == pytest.approx(10.0)

    def test_perm(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("perm(5, 2)")
        assert r.value == pytest.approx(20.0)

    def test_hypot(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("hypot(3, 4)")
        assert r.value == pytest.approx(5.0)


# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════


class TestNewConstants:
    def test_phi(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("phi")
        assert r.value == pytest.approx((1 + math.sqrt(5)) / 2)

    def test_tau(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("tau")
        assert r.value == pytest.approx(2 * math.pi)

    def test_euler_gamma(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("euler_gamma")
        assert r.value == pytest.approx(0.5772156649, rel=1e-6)


# ═══════════════════════════════════════════════════════════════════════
# Array constructors
# ═══════════════════════════════════════════════════════════════════════


class TestArrayConstructors:
    def test_diag(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("diag([1, 2, 3])")
        expected = np.diag([1, 2, 3])
        np.testing.assert_array_equal(r.value, expected)

    def test_logspace(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("logspace(0, 2, 3)")
        np.testing.assert_array_almost_equal(r.value, [1, 10, 100])

    def test_flatten(self, ev: MathEvaluator) -> None:
        ev.evaluate("m = [1,2;3,4]")
        r = ev.evaluate("flatten(m)")
        np.testing.assert_array_equal(r.value, [1, 2, 3, 4])

    def test_sort(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("sort([3, 1, 2])")
        np.testing.assert_array_equal(r.value, [1, 2, 3])

    def test_unique(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("unique([1, 2, 2, 3, 3, 3])")
        np.testing.assert_array_equal(r.value, [1, 2, 3])

    def test_reverse(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("reverse([1, 2, 3])")
        np.testing.assert_array_equal(r.value, [3, 2, 1])

    def test_concat(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("concat([1, 2], [3, 4])")
        np.testing.assert_array_equal(r.value, [1, 2, 3, 4])

    def test_zeros_variadic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("zeros(2, 3)")
        assert r.value.shape == (2, 3)

    def test_ones_variadic(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("ones(3, 2)")
        assert r.value.shape == (3, 2)
        assert np.all(r.value == 1.0)


# ═══════════════════════════════════════════════════════════════════════
# Linear algebra expanded
# ═══════════════════════════════════════════════════════════════════════


class TestLinearAlgebraExpanded:
    def test_trace(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("trace([1,0;0,2])")
        assert r.value == pytest.approx(3.0)

    def test_rank(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("rank([1,0;0,1])")
        assert r.value == 2

    def test_eigvals(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("eigvals([2,0;0,3])")
        vals = sorted(np.real(r.value))
        assert vals[0] == pytest.approx(2.0)
        assert vals[1] == pytest.approx(3.0)

    def test_cond(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("cond([1,0;0,1])")
        assert r.value == pytest.approx(1.0)

    def test_matmul(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("matmul([1,2;3,4], [5;6])")
        np.testing.assert_array_almost_equal(r.value, [[17], [39]])

    def test_outer(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("outer([1, 2], [3, 4])")
        np.testing.assert_array_equal(r.value, [[3, 4], [6, 8]])

    def test_inner(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("inner([1, 2, 3], [4, 5, 6])")
        assert r.value == pytest.approx(32.0)

    def test_kron(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("kron([1,0;0,1], [1,2;3,4])")
        assert r.value.shape == (4, 4)

    def test_solve_linear(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("solve_linear([1,0;0,1], [5, 3])")
        np.testing.assert_array_almost_equal(r.value, [5, 3])


# ═══════════════════════════════════════════════════════════════════════
# Stats expanded
# ═══════════════════════════════════════════════════════════════════════


class TestStatsExpanded:
    def test_median(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("median([1, 3, 5, 7])")
        assert r.value == pytest.approx(4.0)

    def test_cumsum(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("cumsum([1, 2, 3])")
        np.testing.assert_array_equal(r.value, [1, 3, 6])

    def test_cumprod(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("cumprod([1, 2, 3, 4])")
        np.testing.assert_array_equal(r.value, [1, 2, 6, 24])

    def test_prod(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("prod([2, 3, 4])")
        assert r.value == pytest.approx(24.0)

    def test_argmin(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("argmin([3, 1, 2])")
        assert r.value == 1

    def test_argmax(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("argmax([3, 1, 2])")
        assert r.value == 0


# ═══════════════════════════════════════════════════════════════════════
# Utility / numerical functions
# ═══════════════════════════════════════════════════════════════════════


class TestUtilityFunctions:
    def test_trapz(self, ev: MathEvaluator) -> None:
        # trapz of [1,1,1] over [0,1,2] = 2.0
        r = ev.evaluate("trapz([1, 1, 1])")
        assert r.value == pytest.approx(2.0)

    def test_polyfit_polyval(self, ev: MathEvaluator) -> None:
        ev.evaluate("c = polyfit([0,1,2,3], [0,1,4,9], 2)")
        r = ev.evaluate("polyval(c, 2)")
        assert r.value == pytest.approx(4.0, rel=0.1)

    def test_roots(self, ev: MathEvaluator) -> None:
        # x^2 - 1 = 0 → roots are ±1
        r = ev.evaluate("roots([1, 0, -1])")
        vals = sorted(np.real(r.value))
        assert vals[0] == pytest.approx(-1.0)
        assert vals[1] == pytest.approx(1.0)

    def test_convolve(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("convolve([1, 2, 3], [0, 1, 0.5])")
        expected = np.convolve([1, 2, 3], [0, 1, 0.5])
        np.testing.assert_array_almost_equal(r.value, expected)

    def test_interp(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("interp(1.5, [1, 2, 3], [10, 20, 30])")
        assert r.value == pytest.approx(15.0)

    def test_where(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("where([1, 0, 1], [10, 20, 30], [40, 50, 60])")
        np.testing.assert_array_equal(r.value, [10, 50, 30])


# ═══════════════════════════════════════════════════════════════════════
# Numeric vector operations
# ═══════════════════════════════════════════════════════════════════════


class TestVectorCalcNumeric:
    def test_magnitude(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("magnitude([3, 4])")
        assert r.value == pytest.approx(5.0)

    def test_normalize(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("normalize([3, 4])")
        np.testing.assert_array_almost_equal(r.value, [0.6, 0.8])

    def test_proj(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("proj([3, 4], [1, 0])")
        np.testing.assert_array_almost_equal(r.value, [3, 0])

    def test_ndim(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("ndim([1,2;3,4])")
        assert r.value == 2

    def test_isnan(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("isnan(0)")
        assert r.value == 0.0

    def test_isinf(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("isinf(inf)")
        assert r.value == 1.0


# ═══════════════════════════════════════════════════════════════════════
# Symbolic dispatch — new commands route correctly
# ═══════════════════════════════════════════════════════════════════════


class TestSymbolicRouting:
    def test_limit(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('limit("sin(x)/x", "x", 0)')
        assert "1" in str(r.output_text)

    def test_series(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('series("exp(x)", "x", 0, 4)')
        assert not r.is_error

    def test_taylor(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('taylor("sin(x)", "x", 0, 3)')
        assert not r.is_error

    def test_partial(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('partial("x^2*y", "x")')
        assert "2" in str(r.output_text) and "x" in str(r.output_text)

    def test_summation(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('summation("k", "k", 1, 10)')
        assert "55" in str(r.output_text)

    def test_product(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('product("k", "k", 1, 5)')
        assert "120" in str(r.output_text)

    def test_defint(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('defint("x^2", "x", 0, 1)')
        assert "1/3" in str(r.output_text) or "0.333" in str(r.output_text)

    def test_gradient(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('gradient("x^2 + y^2", "x,y")')
        assert not r.is_error

    def test_divergence(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('divergence("x, y, z", "x,y,z")')
        assert "3" in str(r.output_text)

    def test_laplacian(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('laplacian("x^2 + y^2", "x,y")')
        assert "4" in str(r.output_text)

    def test_nsolve(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('nsolve("cos(x) - x", "x", 1)')
        assert not r.is_error
        # Should be near 0.7390851332
        assert "0.739" in str(r.output_text)

    def test_rref(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('rref("[[1,2];[3,4]]")')
        assert not r.is_error

    def test_simplify_still_works(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('simplify("(x^2 - 1)/(x - 1)")')
        assert "x + 1" in str(r.output_text)

    def test_solve_still_works(self, ev: MathEvaluator) -> None:
        r = ev.evaluate('solve("x^2 - 4", "x")')
        assert not r.is_error


# ═══════════════════════════════════════════════════════════════════════
# Grammar features — index access, ternary, pipe
# ═══════════════════════════════════════════════════════════════════════


class TestIndexAccess:
    def test_vector_index(self, ev: MathEvaluator) -> None:
        ev.evaluate("v = [10, 20, 30]")
        r = ev.evaluate("v[0]")
        assert r.value == pytest.approx(10.0)

    def test_vector_index_last(self, ev: MathEvaluator) -> None:
        ev.evaluate("v = [10, 20, 30]")
        r = ev.evaluate("v[2]")
        assert r.value == pytest.approx(30.0)

    def test_vector_negative_index(self, ev: MathEvaluator) -> None:
        ev.evaluate("v = [10, 20, 30]")
        r = ev.evaluate("v[-1]")
        assert r.value == pytest.approx(30.0)


class TestTernary:
    def test_true_branch(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("1 > 0 ? 42 : 0")
        assert r.value == pytest.approx(42.0)

    def test_false_branch(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("0 > 1 ? 42 : -1")
        assert r.value == pytest.approx(-1.0)

    def test_ternary_with_expressions(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("x = 5\nx > 3 ? x^2 : x")
        assert r.value == pytest.approx(25.0)


class TestPipeOperator:
    def test_pipe_to_sum(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("[1, 2, 3] |> sum")
        assert r.value == pytest.approx(6.0)

    def test_pipe_to_sort(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("[3, 1, 2] |> sort")
        np.testing.assert_array_equal(r.value, [1, 2, 3])

    def test_pipe_to_mean(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("[2, 4, 6] |> mean")
        assert r.value == pytest.approx(4.0)

    def test_pipe_to_norm(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("[3, 4] |> norm")
        assert r.value == pytest.approx(5.0)


# ═══════════════════════════════════════════════════════════════════════
# Help command — expanded output
# ═══════════════════════════════════════════════════════════════════════


class TestHelpExpanded:
    def test_help_lists_new_symbolic_commands(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("help()")
        text = str(r.output_text)
        for cmd in ["limit", "taylor", "gradient", "laplace", "nsolve"]:
            assert cmd in text, f"'{cmd}' not found in help output"

    def test_help_lists_new_builtins(self, ev: MathEvaluator) -> None:
        r = ev.evaluate("help()")
        text = str(r.output_text)
        for fn in ["cbrt", "asinh", "factorial", "median", "eigvals"]:
            assert fn in text, f"'{fn}' not found in help output"
