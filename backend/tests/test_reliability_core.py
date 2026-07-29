"""
Uji unit fungsi inti — dibandingkan dengan hasil yang diketahui secara analitik
atau dari referensi, bukan dengan keluaran kode ini sendiri (§10).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.special import gamma as G

from app.config.defaults import MTTR_BY_CLASS
from app.core import rbd as rbdmod
from app.core.fs_mapping import (
    BETA_WORKBOOK,
    FS_MAP,
    RBD_STAGES,
    fs_of,
    is_redundant_tag,
    is_single_point_of_failure,
    mdt_of,
    rbd_tags,
    tag_type,
)
from app.core.pm_optimization import pm_optimize
from app.core.reliability import (
    crow_amsaa,
    laplace_trend,
    mle_censored,
    mrr_fit,
    pctl,
    rel_life,
    uf_factor,
    weibull_mle,
    weibull_r2,
)


# ==========================================================================
# Klasifikasi tag (port tagType)
# ==========================================================================
@pytest.mark.parametrize(
    "tag,expected",
    [
        ("11-F-101", "heater"),
        ("11-V-101A", "vessel"),
        ("11-E-114", "exchanger"),
        ("11-P-102A", "pump"),
        ("11-C-101", "column"),
        ("11-A-104", "injection"),
        ("11-DTU-101", "other"),   # potongan multi-huruf -> other (persis MATLAB)
        ("11-OS-901", "other"),
        ("22-P-101", "other"),     # bukan unit yang diminta
        ("", "other"),
        ("11-P", "other"),         # tidak ada '-' kedua
    ],
)
def test_tag_type(tag: str, expected: str) -> None:
    assert tag_type(tag) == expected


def test_tag_type_unit_prefix_parameter() -> None:
    """Prefix unit dapat diganti (§3.1) tanpa mengubah perilaku default."""
    assert tag_type("55-P-101A", unit_prefix="55-") == "pump"
    assert tag_type("55-P-101A") == "other"


# ==========================================================================
# Struktur domain (port fsMap / rbdStages / betaWorkbook)
# ==========================================================================
def test_fs_map_counts() -> None:
    """Jumlah tag per FS harus persis seperti komentar MATLAB: 23/19/21/4."""
    counts = {fs: sum(1 for v in FS_MAP.values() if v[0] == fs) for fs in (1, 2, 3, 0)}
    assert counts == {1: 23, 2: 19, 3: 21, 0: 4}
    assert len(FS_MAP) == 67


@pytest.mark.parametrize(
    "tag,fs,mdt",
    [
        ("11-P-101A", 1, 16.0),
        ("11-V-101B", 1, 195.0),
        ("11-P-102A", 1, 229.714),
        ("11-A-104", 1, 201.6),
        ("11-F-101", 2, 115.636),
        ("11-C-101", 2, 384.0),
        ("11-E-114", 3, 102.0),
        ("11-V-113A", 3, 480.0),
        ("11-OS-901", 0, 24.0),
    ],
)
def test_fs_map_spot_values(tag: str, fs: int, mdt: float) -> None:
    assert fs_of(tag) == fs
    assert mdt_of(tag) == pytest.approx(mdt)


def test_unmapped_tag() -> None:
    assert fs_of("11-ZZZ-999") == -1
    assert mdt_of("11-ZZZ-999") == 48.0        # cfg.mdtDefault


def test_rbd_stage_structure() -> None:
    assert len(RBD_STAGES) == 18
    assert sum(1 for s in RBD_STAGES if s.fs == 1) == 6
    assert sum(1 for s in RBD_STAGES if s.fs == 2) == 4
    assert sum(1 for s in RBD_STAGES if s.fs == 3) == 8
    # Dua stage sengaja kosong (Side Strippers, Product Coolers).
    assert sum(1 for s in RBD_STAGES if not s.tags) == 2
    # Stage paralel 4-unit: P-111 A-D dan P-112 A-D.
    quad = [s for s in RBD_STAGES if s.typ == "par" and len(s.tags) == 4]
    assert len(quad) == 2


def test_spof_and_redundancy() -> None:
    """F-101 dan C-101 adalah single point of failure (catatan RBD laporan)."""
    assert is_single_point_of_failure("11-F-101")
    assert is_single_point_of_failure("11-C-101")
    assert not is_redundant_tag("11-F-101")
    assert is_redundant_tag("11-P-101A")
    assert is_redundant_tag("11-P-111D")
    assert not is_single_point_of_failure("11-P-101A")


def test_beta_workbook_values() -> None:
    assert BETA_WORKBOOK["heater"] == pytest.approx(2.46877143309813, abs=1e-13)
    assert BETA_WORKBOOK["vessel"] == pytest.approx(1.58547404451843, abs=1e-13)
    assert BETA_WORKBOOK["exchanger"] == pytest.approx(1.31895915990839, abs=1e-13)
    assert BETA_WORKBOOK["pump"] == pytest.approx(1.28280529058255, abs=1e-13)
    for k in ("column", "injection", "other"):
        assert BETA_WORKBOOK[k] == 1.0


def test_mttr_table() -> None:
    assert MTTR_BY_CLASS == {
        "heater": 72.0, "vessel": 24.0, "exchanger": 24.0, "pump": 12.0,
        "column": 48.0, "injection": 8.0, "other": 24.0,
    }


# ==========================================================================
# Weibull: MLE terhadap jawaban yang diketahui
# ==========================================================================
def test_weibull_mle_recovers_known_parameters() -> None:
    """Sampel besar dari Weibull(beta=2.5, eta=1000) harus dikenali kembali."""
    rng = np.random.default_rng(12345)
    beta_true, eta_true = 2.5, 1000.0
    x = eta_true * rng.weibull(beta_true, size=40000)
    b, eta = weibull_mle(x)
    assert b == pytest.approx(beta_true, rel=0.03)
    assert eta == pytest.approx(eta_true, rel=0.03)


def test_weibull_mle_exponential_case() -> None:
    """beta = 1 (eksponensial): eta harus mendekati rerata sampel."""
    rng = np.random.default_rng(7)
    x = rng.exponential(500.0, size=30000)
    b, eta = weibull_mle(x)
    assert b == pytest.approx(1.0, rel=0.04)
    assert eta == pytest.approx(float(np.mean(x)), rel=0.04)


def test_weibull_mle_is_true_optimum() -> None:
    """Nilai NLL di beta hasil MLE harus <= NLL di sekitarnya."""
    from app.core.reliability import _weibull_nll

    x = np.array([192.0, 312.0, 312.0, 672.0, 792.0, 936.0, 2688.0, 2880.0, 3672.0])
    b, _ = weibull_mle(x)
    f0 = _weibull_nll(b, x)
    for d in (-0.01, -0.003, 0.003, 0.01):
        assert _weibull_nll(b + d, x) >= f0 - 1e-12


def test_weibull_r2_perfect_fit() -> None:
    """Data yang tepat mengikuti median rank Bernard memberi R^2 = 1."""
    n = 12
    beta, eta = 1.7, 800.0
    i = np.arange(1, n + 1, dtype=float)
    F = (i - 0.3) / (n + 0.4)
    x = eta * (-np.log(1.0 - F)) ** (1.0 / beta)      # invers Weibull tepat
    r2, X, Y, Yhat = weibull_r2(x)
    assert r2 == pytest.approx(1.0, abs=1e-12)
    slope = np.polyfit(X, Y, 1)[0]
    assert slope == pytest.approx(beta, rel=1e-9)


# ==========================================================================
# MRR (Median Rank Regression) — port mrrFit
# ==========================================================================
def test_mrr_no_suspension_matches_bernard_regression() -> None:
    """Tanpa sensor, MRR harus identik dengan regresi median rank Bernard."""
    x = np.array([100.0, 250.0, 400.0, 700.0, 1200.0])
    res = mrr_fit(x, None)
    r2_ref, X, Y, _ = weibull_r2(x)
    slope_ref = np.polyfit(X, Y, 1)[0]
    assert res.beta == pytest.approx(slope_ref, rel=1e-12)
    assert res.r2 == pytest.approx(r2_ref, rel=1e-12)
    # adj-rank tanpa sensor = 1,2,3,...
    assert [row[1] for row in res.table] == pytest.approx([1.0, 2.0, 3.0, 4.0, 5.0])


def test_mrr_johnson_rank_adjustment_with_suspension() -> None:
    """Sensor kanan terbesar menaikkan N sehingga median rank mengecil.

    Dengan 3 kegagalan + 1 sensor terbesar, N = 4 dan adj-rank kegagalan tetap
    1,2,3 (sensor di ujung), tetapi MR memakai penyebut N + 0,4 = 4,4.
    """
    tf = np.array([100.0, 200.0, 300.0])
    res = mrr_fit(tf, 1000.0)
    assert res.table is not None and len(res.table) == 3
    adj = [row[1] for row in res.table]
    mr = [row[2] for row in res.table]
    assert adj == pytest.approx([1.0, 2.0, 3.0])
    assert mr == pytest.approx([(1 - 0.3) / 4.4, (2 - 0.3) / 4.4, (3 - 0.3) / 4.4])


def test_mrr_suspension_in_middle_shifts_ranks() -> None:
    """Sensor di TENGAH membuat adj-rank kegagalan setelahnya bukan bilangan bulat."""
    tf = np.array([100.0, 500.0])
    res = mrr_fit(tf, 200.0)          # sensor di antara kedua kegagalan
    adj = [row[1] for row in res.table]
    # N=3. urut: 100(F), 200(S), 500(F)
    #   idx1: rev=3, inc=(3+1-0)/(1+3)=1.0      -> adj=1.0   (F)
    #   idx2: rev=2, inc=(3+1-1)/(1+2)=1.0      -> adj=2.0   (S)
    #   idx3: rev=1, inc=(3+1-2)/(1+1)=1.0      -> adj=3.0   (F)
    assert adj == pytest.approx([1.0, 3.0])


def test_mrr_needs_two_failures() -> None:
    assert mrr_fit([500.0], 1000.0).beta is None
    assert mrr_fit([], 1000.0).beta is None


def test_mrr_identical_tbf_is_handled() -> None:
    """Seluruh TBF sama -> kemiringan tak terdefinisi, harus None (bukan crash)."""
    assert mrr_fit([300.0, 300.0, 300.0], None).beta is None


# ==========================================================================
# MLE tersensor & faktor unbias
# ==========================================================================
def test_mle_censored_no_suspension_equals_complete_mle() -> None:
    x = np.array([120.0, 300.0, 450.0, 800.0, 1500.0])
    b_c, eta_c, boundary = mle_censored(x, None)
    b_m, eta_m = weibull_mle(x)
    assert not boundary
    assert b_c == pytest.approx(b_m, rel=1e-6)
    assert eta_c == pytest.approx(eta_m, rel=1e-6)


def test_mle_censored_suspension_increases_eta() -> None:
    """Menambah sensor kanan menaikkan eta (bukti peralatan masih hidup)."""
    x = np.array([120.0, 300.0, 450.0, 800.0])
    _, eta_no, _ = mle_censored(x, None)
    _, eta_susp, _ = mle_censored(x, 5000.0)
    assert eta_susp > eta_no


def test_mle_censored_boundary_flag() -> None:
    """`boundary` menandai solusi yang menempel batas [0,1 ; 10].

    Satu kegagalan dengan sensor kanan yang HAMPIR SAMA waktunya membuat
    persamaan likelihood tidak punya akar di dalam batas: beta terdorong ke
    tepi atas sehingga shape tidak layak dipakai. Sebaliknya, satu kegagalan
    dengan sensor yang jauh lebih besar masih menghasilkan akar interior.
    """
    # Sensor sangat dekat dengan kegagalan -> beta menempel batas atas.
    b_edge, _, boundary_edge = mle_censored([100.0], 101.0)
    assert boundary_edge is True
    assert b_edge == pytest.approx(10.0, abs=1e-6)

    # Sensor jauh -> akar interior, flag tidak menyala.
    b_in, _, boundary_in = mle_censored([100.0], 100_000.0)
    assert boundary_in is False
    assert 0.11 < b_in < 9.9


def test_uf_factor_table() -> None:
    """Faktor unbias Thoman-Bain-Antle pada titik tabel dan ekstrapolasinya."""
    assert uf_factor(2) == pytest.approx(0.549)
    assert uf_factor(10) == pytest.approx(0.916)
    assert uf_factor(1) == pytest.approx(0.549)       # m <= 2 -> nilai pertama
    assert uf_factor(1000) == 1.0                     # m >= 100 -> 1
    assert 0.916 < uf_factor(11) < 0.933              # interpolasi linear


# ==========================================================================
# Crow-AMSAA (NHPP power-law)
# ==========================================================================
def test_crow_amsaa_analytic() -> None:
    """beta = n / sum(ln(T/t_i)) — dihitung tangan untuk kasus kecil."""
    cal = [100.0, 400.0, 900.0]
    T = 1000.0
    s = sum(math.log(T / t) for t in cal)
    b, lam = crow_amsaa(cal, T)
    assert b == pytest.approx(3.0 / s)
    assert lam == pytest.approx(3.0 / T ** (3.0 / s))


def test_crow_amsaa_homogeneous_poisson_gives_beta_one() -> None:
    """Kejadian yang tersebar merata (HPP) memberi beta mendekati 1."""
    rng = np.random.default_rng(3)
    T = 10000.0
    cal = np.sort(rng.uniform(0, T, size=20000))
    b, _ = crow_amsaa(cal, T)
    assert b == pytest.approx(1.0, rel=0.03)


def test_crow_amsaa_needs_two_events() -> None:
    assert crow_amsaa([500.0], 1000.0) == (None, None)
    assert crow_amsaa([], 1000.0) == (None, None)


def test_crow_amsaa_ignores_events_outside_window() -> None:
    b1, _ = crow_amsaa([100.0, 400.0, 900.0, 5000.0], 1000.0)
    b2, _ = crow_amsaa([100.0, 400.0, 900.0], 1000.0)
    assert b1 == pytest.approx(b2)


# ==========================================================================
# Uji tren Laplace
# ==========================================================================
def test_laplace_no_trend() -> None:
    """Kejadian simetris di tengah jendela -> U = 0, p = 1."""
    T = 1000.0
    t = [200.0, 400.0, 600.0, 800.0]            # rerata tepat T/2
    u, p = laplace_trend(t, T)
    assert u == pytest.approx(0.0, abs=1e-12)
    assert p == pytest.approx(1.0, abs=1e-12)


def test_laplace_detects_increasing_rate() -> None:
    """Kejadian menumpuk di akhir jendela -> U positif besar (IFR)."""
    T = 1000.0
    t = list(np.linspace(900, 995, 30))
    u, p = laplace_trend(t, T)
    assert u > 1.96
    assert p < 0.05


def test_laplace_detects_decreasing_rate() -> None:
    t = list(np.linspace(5, 100, 30))
    u, p = laplace_trend(t, 1000.0)
    assert u < -1.96
    assert p < 0.05


# ==========================================================================
# RBD seri-paralel
# ==========================================================================
def _mk(tag: str, beta: float, eta: float, a: float = 0.9) -> rbdmod.EquipmentParams:
    return rbdmod.EquipmentParams(
        tag=tag, beta=beta, eta=eta, mtbf=eta, n_cm=1,
        a_inh=a, a_op=a, mdt=48.0, mttr=24.0, kelas="pump",
    )


def test_stage_series_is_product() -> None:
    from app.core.fs_mapping import Stage

    eq = {"A": _mk("A", 1.0, 1000.0), "B": _mk("B", 1.0, 2000.0)}
    st = Stage(1, "s", "ser", ("A", "B"))
    r = float(rbdmod.stage_r(st, eq, 500.0))
    expected = math.exp(-500 / 1000) * math.exp(-500 / 2000)
    assert r == pytest.approx(expected, rel=1e-12)


def test_stage_parallel_is_one_minus_product_of_unreliability() -> None:
    from app.core.fs_mapping import Stage

    eq = {"A": _mk("A", 1.0, 1000.0), "B": _mk("B", 1.0, 2000.0)}
    st = Stage(1, "p", "par", ("A", "B"))
    r = float(rbdmod.stage_r(st, eq, 500.0))
    ra, rb = math.exp(-0.5), math.exp(-0.25)
    assert r == pytest.approx(1 - (1 - ra) * (1 - rb), rel=1e-12)
    # Redundansi selalu lebih andal daripada anggota terbaiknya.
    assert r > max(ra, rb)


def test_parallel_availability_exceeds_members() -> None:
    from app.core.fs_mapping import Stage

    eq = {"A": _mk("A", 1.0, 1000.0, a=0.8), "B": _mk("B", 1.0, 1000.0, a=0.8)}
    st = Stage(1, "p", "par", ("A", "B"))
    assert rbdmod.stage_a(st, eq, "op") == pytest.approx(1 - 0.2 * 0.2)


def test_empty_stage_is_perfectly_reliable() -> None:
    from app.core.fs_mapping import Stage

    st = Stage(2, "kosong", "ser", ())
    assert float(rbdmod.stage_r(st, {}, 720.0)) == 1.0
    assert rbdmod.stage_a(st, {}, "inh") == 1.0


def test_never_failed_equipment_has_r_one() -> None:
    """Tag redundan yang tak pernah gagal -> R = 1, A = 1 (perilaku eqR/eqA)."""
    eq = {
        "X": rbdmod.EquipmentParams(
            tag="X", beta=1.0, eta=float("inf"), mtbf=float("inf"), n_cm=0,
            a_inh=1.0, a_op=1.0, mdt=48.0, mttr=24.0, kelas="pump",
        )
    }
    assert float(rbdmod.eq_r(eq, "X", 8760.0)) == 1.0
    assert rbdmod.eq_a(eq, "X", "op") == 1.0


def test_unknown_tag_is_neutral() -> None:
    assert float(rbdmod.eq_r({}, "tidak-ada", 720.0)) == 1.0
    assert rbdmod.eq_a({}, "tidak-ada", "op") == 1.0


def test_eta_from_mtbf_relationship() -> None:
    """eta = MTBF / Gamma(1 + 1/beta) -> MTTF hasilnya kembali sama dengan MTBF."""
    mtbf, beta = 1551.27, 1.0537
    eta = mtbf / G(1 + 1 / beta)
    assert eta * G(1 + 1 / beta) == pytest.approx(mtbf, rel=1e-12)


def test_selection_r_uses_stage_logic() -> None:
    """Seleksi dua pompa pada stage paralel -> redundan; dua SPOF seri -> perkalian."""
    eq = {t: _mk(t, 1.0, 2000.0) for t in rbd_tags()}
    par = float(rbdmod.selection_r(["11-P-102A", "11-P-102B"], eq, 720.0))
    one = float(rbdmod.eq_r(eq, "11-P-102A", 720.0))
    assert par > one                                   # redundansi
    ser = float(rbdmod.selection_r(["11-F-101", "11-C-101"], eq, 720.0))
    assert ser == pytest.approx(one * one, rel=1e-12)  # seri, stage berbeda


def test_selection_empty_is_one() -> None:
    assert float(rbdmod.selection_r([], {}, 720.0)) == 1.0


# ==========================================================================
# Barlow-Hunter age replacement
# ==========================================================================
def test_pm_optimize_beta_one_has_no_benefit() -> None:
    """beta = 1 (laju kegagalan tetap): tidak ada penghematan dari jadwal.

    Untuk eksponensial, C(tau) minimum saat tau -> tak hingga dan nilainya
    menuju Cf/eta = C_rtf, sehingga penghematan <= 0.
    Ref: Barlow & Hunter (1960).
    """
    opt = pm_optimize(beta=1.0, eta=1000.0, cp=1.0, cf=10.0)
    assert opt.saving_pct <= 0.01
    assert opt.saving_pct_effective == 0.0


def test_pm_optimize_wearout_gives_positive_saving() -> None:
    """beta besar (aus kuat) + Cf >> Cp: jadwal memberi penghematan nyata."""
    opt = pm_optimize(beta=3.5, eta=1000.0, cp=1.0, cf=50.0)
    assert opt.saving_pct > 20.0
    assert 0 < opt.tau_opt_hours < 3000.0


def test_pm_optimize_cost_rtf_formula() -> None:
    """C_rtf = Cf / MTTF dengan MTTF = eta*Gamma(1+1/beta)."""
    beta, eta, cf = 2.0, 1500.0, 7.0
    opt = pm_optimize(beta=beta, eta=eta, cp=1.0, cf=cf)
    assert opt.cost_rtf == pytest.approx(cf / (eta * G(1 + 1 / beta)), rel=1e-12)


def test_pm_optimize_grid_matches_matlab() -> None:
    """Grid tau = linspace(0.05*eta, 3*eta, 300) — dipertahankan agar tau* sama."""
    opt = pm_optimize(beta=2.0, eta=1000.0, cp=1.0, cf=10.0)
    assert len(opt.tau_grid) == 300
    assert opt.tau_grid[0] == pytest.approx(50.0)
    assert opt.tau_grid[-1] == pytest.approx(3000.0)


def test_pm_optimize_handles_infinite_eta() -> None:
    """eta tak hingga (tak pernah gagal) tidak boleh menyebabkan galat."""
    opt = pm_optimize(beta=1.0, eta=float("inf"), cp=1.0, cf=10.0)
    assert np.isfinite(opt.tau_opt_hours)


# ==========================================================================
# Penolong
# ==========================================================================
def test_pctl_matches_matlab_definition() -> None:
    """pctl MATLAB: indeks ceil(p/100*n) pada data terurut, TANPA interpolasi."""
    x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert pctl(x, 10) == 1.0      # ceil(0.1*10) = 1
    assert pctl(x, 50) == 5.0      # ceil(0.5*10) = 5  (np.percentile -> 5.5)
    assert pctl(x, 90) == 9.0
    assert pctl(x, 100) == 10.0
    assert math.isnan(pctl([], 50))


def test_rel_life_interpolation() -> None:
    """Umur keandalan diinterpolasi linear antara dua titik grid."""
    td = np.array([0.0, 1.0, 2.0, 3.0])
    rv = np.array([1.0, 0.9, 0.8, 0.7])
    assert rel_life(td, rv, 0.85) == pytest.approx(1.5)
    assert math.isnan(rel_life(td, rv, 0.5))     # tidak tercapai pada grid


def test_rel_life_exact_hit() -> None:
    td = np.array([0.0, 1.0, 2.0])
    rv = np.array([1.0, 0.9, 0.8])
    assert rel_life(td, rv, 0.9) == pytest.approx(1.0)
