"""
VALIDASI NUMERIK terhadap laporan MATLAB (§10).

Uji ini menjalankan berkas notifikasi nyata dan membandingkan keluaran kunci
dengan angka pada "Laporan Hasil Simulasi MATLAB" serta konstanta di
CDU_PdM_Balongan.m. Bila berkas contoh tidak ada, uji di-skip (bukan gagal),
sehingga suite tetap dapat dijalankan di mesin lain.

Letakkan berkas notifikasi di salah satu lokasi berikut (atau set variabel
lingkungan CDU_NOTIF_XLSX):
    <repo>/data/20260531_Notification_RU_Balongan.xlsx
    <repo>/20260531_Notification_RU_Balongan.xlsx

--------------------------------------------------------------------------
CATATAN PENYIMPANGAN YANG DIKETAHUI (dilaporkan, bukan disembunyikan)
--------------------------------------------------------------------------
1. R(30 hari) FS-3 : aplikasi 0,36646 vs laporan 0,368  (selisih 0,4%).
   Sebab: laporan memakai beta kelas `vessel` = 0,79042 sedangkan MLE yang
   benar adalah 0,78725. Nilai negatif log-likelihood di 0,78725 LEBIH KECIL
   (138,53437 vs 138,53457), jadi 0,78725 memang optimum yang lebih tepat.
   Penyimpangan berasal dari toleransi bawaan `fminbnd` MATLAB (TolX = 1e-4)
   pada permukaan likelihood yang sangat datar. Tiga metode independen
   (MLE profil, scipy.stats.weibull_min.fit, dan akar persamaan likelihood)
   sepakat pada 0,78725 dalam 1,2e-08.

2. beta kelas `pump` Crow-AMSAA : aplikasi 1,27484 vs betaWorkbook 1,28281.
   Kelas heater/vessel/exchanger cocok sampai ~3e-15, sehingga selisih pada
   pump menunjuk perbedaan vintage data pompa pada workbook, bukan rumus.

3. Monte Carlo : selisih <= 1,1% terhadap laporan. Wajar karena aliran bilangan
   acak numpy (PCG64) berbeda dari Mersenne Twister MATLAB; nilai analitik
   A_op yang menjadi acuan silang cocok tepat.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pytest

from app.config.defaults import DEFAULT_CONFIG
from app.core.analysis import run_analysis
from app.core.data_loader import detect_kind, load_notifications, read_all_sheets
from app.core.montecarlo import mc_system
from app.core.pm_optimization import bad_actor_per_fs, optimize_module_g
from app.core.reliability import crow_amsaa

_CANDIDATES = [
    os.getenv("CDU_NOTIF_XLSX", ""),
    "data/20260531_Notification_RU_Balongan.xlsx",
    "20260531_Notification_RU_Balongan.xlsx",
    "../data/20260531_Notification_RU_Balongan.xlsx",
    "../20260531_Notification_RU_Balongan.xlsx",
]


def _find_file() -> Path | None:
    root = Path(__file__).resolve().parents[2]
    for c in _CANDIDATES:
        if not c:
            continue
        for base in (Path.cwd(), Path(__file__).resolve().parent, root, root / "backend"):
            p = (base / c).resolve()
            if p.is_file():
                return p
    return None


@pytest.fixture(scope="module")
def hasil():
    path = _find_file()
    if path is None:
        pytest.skip(
            "Berkas 20260531_Notification_RU_Balongan.xlsx tidak ditemukan; "
            "letakkan di folder data/ atau set CDU_NOTIF_XLSX."
        )
    sheets = read_all_sheets(path)
    pick = detect_kind(sheets)
    assert pick.kind == "notification", "Berkas harus berjenis notifikasi."
    nd = load_notifications(sheets, pick.sheet_name)
    return nd, run_analysis(nd, DEFAULT_CONFIG), sheets


# ==========================================================================
# Modul A — jendela pengamatan
# ==========================================================================
def test_t_obs_cutoff_17064_jam(hasil) -> None:
    """T_obs mode 'cutoff' = 17.064 jam (711 hari) — angka laporan."""
    nd, _, _ = hasil
    assert nd.t_obs_hours == pytest.approx(17064.0, abs=1e-6)
    assert round((nd.t_end - nd.t_start).days) == 711


def test_t_obs_lastevent_16992_jam(hasil) -> None:
    """Mode 'lastevent' = 16.992 jam — nilai yang disebut komentar MATLAB."""
    _, _, sheets = hasil
    pick = detect_kind(sheets)
    nd2 = load_notifications(sheets, pick.sheet_name, window_end="lastevent")
    assert nd2.t_obs_hours == pytest.approx(16992.0, abs=1e-6)


def test_rekap_notifikasi(hasil) -> None:
    _, res, _ = hasil
    dq: Dict[str, object] = {r["metrik"]: r["nilai"] for r in res.data_quality}
    assert dq["Jumlah tag unik"] == 67
    assert dq["Tag tanpa mapping FS"] == 0
    assert dq["Tanggal kosong (dibuang)"] == 0
    assert res.meta["total_cm"] == 142                 # M1 + M2
    assert dq["Kegagalan korektif M1"] == 26
    assert dq["Kegagalan korektif M2"] == 116


# ==========================================================================
# Modul B2 — pembagian beban antar FS
# ==========================================================================
def test_fs_share_dan_mtbf(hasil) -> None:
    """FS-1 menanggung 69 dari 142 kegagalan atau 48,6 persen (laporan)."""
    _, res, _ = hasil
    fs = {r["sistem"]: r for r in res.functional_system}
    assert fs["FS-1"]["n_cm"] == 69
    assert fs["FS-1"]["share_cm_pct"] == pytest.approx(48.6, abs=0.05)
    assert fs["FS-2"]["n_cm"] == 42
    assert fs["FS-3"]["n_cm"] == 28
    assert fs["FS-1"]["n_tag"] == 23
    assert fs["FS-2"]["n_tag"] == 19
    assert fs["FS-3"]["n_tag"] == 21
    # MTBF_seri = T_obs / n_CM
    assert fs["FS-1"]["mtbf_seri_hari"] == pytest.approx(17064 / 69 / 24, rel=1e-9)


def test_mtbf_f101_1551_jam(hasil) -> None:
    """F-101: MTBF = 17.064 / 11 = 1.551 jam = 64,6 hari (laporan)."""
    _, res, _ = hasil
    f101 = next(r for r in res.equipment if r["tag"] == "11-F-101")
    assert f101["n_cm"] == 11
    assert f101["mtbf_jam"] == pytest.approx(1551.27, abs=0.1)
    assert f101["mtbf_hari"] == pytest.approx(64.6, abs=0.05)


# ==========================================================================
# Modul C3 — beta per equipment
# ==========================================================================
def test_beta_mrr_e114_dan_p102a(hasil) -> None:
    """Laporan: E-114 beta 0,52 ; P-102A beta 1,53 (nilai MRR)."""
    _, res, _ = hasil
    eq = {r["tag"]: r for r in res.weibull_equipment}
    assert eq["11-E-114"]["beta_mrr"] == pytest.approx(0.52, abs=0.005)
    assert eq["11-P-102A"]["beta_mrr"] == pytest.approx(1.53, abs=0.005)


def test_beta_final_tabel_71(hasil) -> None:
    """Laporan Tabel 7.1: P-102B 0,91 ; F-101 1,05 ; E-114 0,70 (beta final)."""
    _, res, _ = hasil
    eq = {r["tag"]: r for r in res.weibull_equipment}
    assert eq["11-P-102B"]["beta_final"] == pytest.approx(0.91, abs=0.005)
    assert eq["11-F-101"]["beta_final"] == pytest.approx(1.05, abs=0.005)
    assert eq["11-E-114"]["beta_final"] == pytest.approx(0.70, abs=0.005)


def test_kredibilitas_buhlmann(hasil) -> None:
    """w = m/(m+M0) dengan M0 = 3; F-101 punya m = 9 TBF -> w = 0,75."""
    _, res, _ = hasil
    f = next(r for r in res.weibull_equipment if r["tag"] == "11-F-101")
    assert f["n_tbf"] == 9
    assert f["bobot_w"] == pytest.approx(9 / (9 + 3), abs=1e-6)
    # beta_final = w*beta_MRR + (1-w)*prior
    expect = f["bobot_w"] * f["beta_mrr"] + (1 - f["bobot_w"]) * f["prior_kelas"]
    assert f["beta_final"] == pytest.approx(expect, rel=1e-6)


def test_crow_amsaa_mereproduksi_beta_workbook(hasil) -> None:
    """betaWorkbook() = Crow-AMSAA pada data kelas yang digabung.

    heater/vessel/exchanger cocok sampai presisi mesin (~3e-15). Ini
    memvalidasi T_obs, waktu kalender kegagalan, filter unit, penggolongan
    M1/M2, mapping tag->kelas, dan rumus Crow-AMSAA sekaligus.
    """
    import numpy as np

    nd, res, _ = hasil
    fail = nd.df[nd.df["is_fail"]]
    t0 = nd.t_start.to_datetime64()
    target = {
        "heater": 2.46877143309813,
        "vessel": 1.58547404451843,
        "exchanger": 1.31895915990839,
    }
    for kelas, expected in target.items():
        cal = []
        for t in res.tags:
            if res.kelas[t] != kelas:
                continue
            d = fail.loc[fail["tag"] == t, "date"].values
            cal.extend(((d - t0) / np.timedelta64(1, "h")).tolist())
        beta, _ = crow_amsaa(cal, nd.t_obs_hours)
        assert beta == pytest.approx(expected, abs=1e-12), f"kelas {kelas}"


# ==========================================================================
# Modul E — ketersediaan & keandalan sistem (Tabel 6.1 dan 6.2 laporan)
# ==========================================================================
def test_tabel_61_ketersediaan(hasil) -> None:
    """Tabel 6.1: A_inh dan A_op tiap sistem serta gabungan."""
    _, res, _ = hasil
    a = {r["sistem"]: r for r in res.availability}
    assert a["FS-1"]["a_inh"] == pytest.approx(0.966, abs=0.001)
    assert a["FS-1"]["a_op"] == pytest.approx(0.801, abs=0.001)
    assert a["FS-2"]["a_inh"] == pytest.approx(0.949, abs=0.001)
    assert a["FS-2"]["a_op"] == pytest.approx(0.888, abs=0.001)
    assert a["FS-3"]["a_inh"] == pytest.approx(0.979, abs=0.001)
    assert a["FS-3"]["a_op"] == pytest.approx(0.924, abs=0.001)
    assert a["CDU"]["a_inh"] == pytest.approx(0.897, abs=0.001)
    assert a["CDU"]["a_op"] == pytest.approx(0.658, abs=0.001)


#: Toleransi pembandingan R(t) terhadap laporan.
#: Seluruh selisih yang tersisa berasal dari beta prior kelas yang dihitung
#: MATLAB dengan `fminbnd` bertoleransi bawaan TolX = 1e-4 pada permukaan
#: likelihood yang hampir datar (lihat catatan penyimpangan 1 di atas).
#: Selisih terbesar yang teramati adalah 0,0015 pada FS-3.
TOL_R = 0.002


def test_tabel_62_keandalan_misi(hasil) -> None:
    """Tabel 6.2: keandalan pada 1, 7, 30, dan 90 hari."""
    _, res, _ = hasil
    h = {r["hari"]: r for r in res.reliability_horizons}
    expected = {
        1: (0.870, 0.983, 0.923, 0.790),
        7: (0.573, 0.881, 0.714, 0.360),
        30: (0.193, 0.564, 0.368, 0.040),
        90: (0.017, 0.167, 0.102, 0.0003),
    }
    for hari, (e1, e2, e3, eg) in expected.items():
        assert h[hari]["r_fs1"] == pytest.approx(e1, abs=TOL_R), f"FS-1 @{hari}h"
        assert h[hari]["r_fs2"] == pytest.approx(e2, abs=TOL_R), f"FS-2 @{hari}h"
        assert h[hari]["r_fs3"] == pytest.approx(e3, abs=TOL_R), f"FS-3 @{hari}h"
        assert h[hari]["r_gabungan"] == pytest.approx(eg, abs=TOL_R), f"gab @{hari}h"


def test_penyimpangan_terhadap_laporan_terdokumentasi(hasil) -> None:
    """Kunci selisih maksimum terhadap laporan agar regresi terdeteksi (§10).

    Uji ini GAGAL bila selisih membesar melampaui yang sudah dijelaskan,
    sehingga perubahan rumus yang tidak disengaja langsung tertangkap.
    """
    _, res, _ = hasil
    h = {r["hari"]: r for r in res.reliability_horizons}
    laporan = {
        (1, "r_fs1"): 0.870, (1, "r_fs2"): 0.983, (1, "r_fs3"): 0.923,
        (7, "r_fs1"): 0.573, (7, "r_fs2"): 0.881, (7, "r_fs3"): 0.714,
        (30, "r_fs1"): 0.193, (30, "r_fs2"): 0.564, (30, "r_fs3"): 0.368,
        (90, "r_fs2"): 0.167, (90, "r_fs3"): 0.102,
    }
    devs = {k: abs(h[k[0]][k[1]] - v) for k, v in laporan.items()}
    worst_key = max(devs, key=devs.get)
    assert devs[worst_key] <= TOL_R, (
        f"Selisih terbesar {worst_key} = {devs[worst_key]:.5f} melampaui {TOL_R}"
    )
    # Mayoritas nilai harus cocok jauh lebih rapat daripada batas.
    assert sum(1 for d in devs.values() if d <= 0.0005) >= 5


def test_gabungan_adalah_perkalian_tiga_fs(hasil) -> None:
    """R_gabungan = R_FS1 x R_FS2 x R_FS3 (tiga FS tersusun seri)."""
    _, res, _ = hasil
    for r in res.reliability_horizons:
        assert r["r_gabungan"] == pytest.approx(
            r["r_fs1"] * r["r_fs2"] * r["r_fs3"], rel=1e-9
        )


def test_stage_f101_r_satu_bulan(hasil) -> None:
    """Laporan: keandalan dapur pemanas F-101 satu bulan sekitar 0,646."""
    _, res, _ = hasil
    st = next(s for s in res.rbd_stages if s["stage"].startswith("Crude Charge Heater"))
    assert st["r_1bln"] == pytest.approx(0.646, abs=0.002)


def test_beta_source_workbook_mereproduksi_pembanding(hasil) -> None:
    """Perbandingan MATLAB beta kelas vs beta per-equipment (misi 1 bulan)."""
    nd, res, _ = hasil
    cmp_ = {r["sistem"]: r for r in res.beta_comparison}
    assert cmp_["FS-1"]["r30_equip"] == pytest.approx(0.193, abs=0.001)
    assert cmp_["FS-1"]["r30_kelas"] == pytest.approx(0.582, abs=0.002)
    # A_op tidak bergantung pada beta (hanya MTBF & MDT) -> harus identik.
    for k in ("FS-1", "FS-2", "FS-3"):
        assert cmp_[k]["aop_kelas"] == pytest.approx(cmp_[k]["aop_equip"], rel=1e-12)


# ==========================================================================
# Modul G — Tabel 7.1 interval optimal
# ==========================================================================
def test_bad_actor_per_fs(hasil) -> None:
    """Bad actor: P-102B (FS-1), F-101 (FS-2), E-114 (FS-3) — sesuai laporan."""
    _, res, _ = hasil
    ba = bad_actor_per_fs(res.tags, res.n_cm, res.fs_of_tag)
    assert ba[1] == "11-P-102B"
    assert ba[2] == "11-F-101"
    assert ba[3] == "11-E-114"


def test_tabel_71_interval_optimal(hasil) -> None:
    """Tabel 7.1: tau* = 255, 198, dan 211 hari, penghematan nol persen."""
    _, res, _ = hasil
    g = optimize_module_g(
        res.eq_params, res.tags, res.n_cm, res.fs_of_tag,
        cp=DEFAULT_CONFIG.cp, cf=DEFAULT_CONFIG.cf,
    )
    tau = {r["bad_actor"]: r["tau_opt_hari"] for r in g["tabel"]}
    assert tau["11-P-102B"] == pytest.approx(255, abs=1)
    assert tau["11-F-101"] == pytest.approx(198, abs=1)
    assert tau["11-E-114"] == pytest.approx(211, abs=1)
    # Penghematan efektif nol untuk ketiganya (beta di sekitar/di bawah satu).
    for r in g["tabel"]:
        assert r["penghematan_efektif_pct"] == pytest.approx(0.0, abs=0.05)


# ==========================================================================
# Modul F — Monte Carlo (stokastik: toleransi lebih longgar)
# ==========================================================================
def test_tabel_63_monte_carlo(hasil) -> None:
    """Tabel 6.3 (400 putaran). Toleransi 0,02 karena aliran acak berbeda."""
    _, res, _ = hasil
    a_op = {r["sistem"]: r["a_op"] for r in res.availability}
    mc = mc_system(
        res.eq_params, reps=DEFAULT_CONFIG.mc_reps, horizon=DEFAULT_CONFIG.mc_horizon,
        dt=DEFAULT_CONFIG.mc_dt, seed=DEFAULT_CONFIG.mc_seed, a_op_analytic=a_op,
    )
    t = {r["sistem"]: r for r in mc.table}
    assert t["FS-1"]["a_mean"] == pytest.approx(0.784, abs=0.02)
    assert t["FS-2"]["a_mean"] == pytest.approx(0.889, abs=0.02)
    assert t["FS-3"]["a_mean"] == pytest.approx(0.914, abs=0.02)
    assert t["CDU total"]["a_mean"] == pytest.approx(0.638, abs=0.02)
    assert t["FS-1"]["a_p10"] == pytest.approx(0.679, abs=0.02)
    assert t["CDU total"]["a_p10"] == pytest.approx(0.529, abs=0.02)
    # Urutan persentil harus konsisten.
    for r in mc.table:
        assert r["a_p10"] <= r["a_p50"] <= r["a_p90"]


def test_monte_carlo_reprodusibel(hasil) -> None:
    """Seed sama -> hasil identik bit demi bit (§10 reprodusibilitas)."""
    _, res, _ = hasil
    kw = dict(reps=60, horizon=8760.0, dt=1.0, seed=7)
    a = mc_system(res.eq_params, **kw).table
    b = mc_system(res.eq_params, **kw).table
    assert [r["a_mean"] for r in a] == [r["a_mean"] for r in b]


def test_monte_carlo_mendekati_analitik(hasil) -> None:
    """Rerata simulasi harus dekat dengan A_op analitik (pemeriksaan silang)."""
    _, res, _ = hasil
    a_op = {r["sistem"]: r["a_op"] for r in res.availability}
    mc = mc_system(res.eq_params, reps=200, horizon=8760.0, dt=1.0, seed=7)
    t = {r["sistem"]: r for r in mc.table}
    for k in ("FS-1", "FS-2", "FS-3"):
        assert t[k]["a_mean"] == pytest.approx(a_op[k], abs=0.05), k
