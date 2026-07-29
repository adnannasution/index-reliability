"""
Uji analisis interval pemeliharaan: kurva biaya, keandalan, titik optimal, dan
logika rekomendasi.

Pengujian di sini bersifat SIFAT (property based) terhadap teori, bukan
membandingkan dengan keluaran kode ini sendiri:

  * batas tau menuju nol   C(tau) menuju tak hingga, sehingga minimum interior
                           selalu ada untuk Cf > Cp;
  * batas tau menuju besar lambda_eff menuju 1/MTTF, yaitu kembali ke run to
                           failure;
  * arah A_op(tau)         menurun untuk beta > 1 dan MENAIK untuk beta < 1;
  * tau_R analitik         R(tau_R) harus tepat sama dengan target;
  * kelayakan tugas        beta di sekitar atau di bawah satu tidak boleh
                           menghasilkan rekomendasi penggantian terjadwal.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.special import gamma as G

from app.config.defaults import DEFAULT_CONFIG
from app.core.interval_analysis import (
    _grid_matlab,
    _grid_pencarian,
    analisis_fs,
    analisis_peralatan,
    kurva_banyak_peralatan,
    kurva_peralatan,
    tau_untuk_target_keandalan,
)
from app.core.rbd import EquipmentParams


def _eq(tag: str, beta: float, eta: float, mdt: float = 48.0, n_cm: int = 5) -> EquipmentParams:
    mtbf = eta * float(G(1.0 + 1.0 / beta))
    return EquipmentParams(
        tag=tag, beta=beta, eta=eta, mtbf=mtbf, n_cm=n_cm,
        a_inh=mtbf / (mtbf + 24.0), a_op=mtbf / (mtbf + mdt),
        mdt=mdt, mttr=24.0, kelas="pump",
    )


# ==========================================================================
# tau_R analitik
# ==========================================================================
@pytest.mark.parametrize("beta", [0.6, 1.0, 1.5, 2.5, 4.0])
@pytest.mark.parametrize("r_target", [0.5, 0.8, 0.9, 0.99])
def test_tau_target_keandalan_tepat(beta: float, r_target: float) -> None:
    """tau_R = eta*(-ln R)^(1/beta) harus mengembalikan R(tau_R) = R tepat."""
    eta = 1500.0
    tau_r = tau_untuk_target_keandalan(beta, eta, r_target)
    r_balik = math.exp(-((tau_r / eta) ** beta))
    assert r_balik == pytest.approx(r_target, abs=1e-12)


def test_tau_target_menolak_masukan_tak_sah() -> None:
    assert math.isnan(tau_untuk_target_keandalan(1.5, 1000.0, 0.0))
    assert math.isnan(tau_untuk_target_keandalan(1.5, 1000.0, 1.0))
    assert math.isnan(tau_untuk_target_keandalan(1.5, float("inf"), 0.9))


def test_tau_target_menurun_dengan_target_lebih_ketat() -> None:
    """Target keandalan lebih tinggi menuntut interval lebih pendek."""
    t = [tau_untuk_target_keandalan(2.0, 1000.0, r) for r in (0.5, 0.8, 0.9, 0.99)]
    assert t == sorted(t, reverse=True)


# ==========================================================================
# Sifat kurva
# ==========================================================================
def test_biaya_menuju_tak_hingga_saat_interval_menuju_nol() -> None:
    """C(tau) -> Cp/tau -> tak hingga, sehingga minimum interior selalu ada."""
    e = _eq("X", beta=2.0, eta=1000.0)
    tau = np.array([0.01, 0.1, 1.0, 10.0])
    k = kurva_peralatan(e, tau, cp=1.0, cf=10.0)
    assert np.all(np.diff(k.cost_rate) < 0), "biaya harus menurun tajam dari tau sangat kecil"
    assert k.cost_rate[0] > 50.0 * k.cost_rate[-1]


def test_laju_kegagalan_efektif_kembali_ke_run_to_failure() -> None:
    """Saat tau membesar, lambda_eff -> 1/MTTF (kebijakan menjadi run to failure)."""
    for beta in (0.7, 1.0, 1.8, 3.0):
        e = _eq("X", beta=beta, eta=1200.0)
        tau = np.geomspace(10.0, 1200.0 * 40, 200)
        k = kurva_peralatan(e, tau, cp=1.0, cf=10.0)
        assert k.lambda_eff[-1] == pytest.approx(1.0 / k.mttf, rel=0.02), f"beta={beta}"


def test_keandalan_menurun_monoton_terhadap_interval() -> None:
    e = _eq("X", beta=1.6, eta=900.0)
    tau = np.geomspace(1.0, 5000.0, 150)
    k = kurva_peralatan(e, tau, cp=1.0, cf=10.0)
    assert np.all(np.diff(k.r_tau) <= 1e-15)


@pytest.mark.parametrize("beta,harus_naik", [(0.6, True), (0.85, True), (1.4, False), (3.0, False)])
def test_arah_ketersediaan_bergantung_pada_beta(beta: float, harus_naik: bool) -> None:
    """A_op(tau) MENAIK untuk beta < 1 dan menurun untuk beta > 1.

    Ini konsekuensi langsung dari lambda_eff(tau) = [1-R(tau)]/L(tau): untuk
    beta < 1 nilainya menurun menuju 1/MTTF, sehingga memperpanjang interval
    justru menaikkan ketersediaan. Karena itu penggantian terjadwal pada pola
    kegagalan dini merugikan, bukan hanya tidak bermanfaat.
    """
    e = _eq("X", beta=beta, eta=1000.0, mdt=100.0)
    tau = np.geomspace(5.0, 20000.0, 200)
    k = kurva_peralatan(e, tau, cp=1.0, cf=10.0)
    # bool() perlu karena perbandingan numpy menghasilkan np.bool_, bukan bool.
    naik = bool(k.a_op[-1] > k.a_op[0])
    assert naik is harus_naik, f"beta={beta}: A_op naik={naik}"


# ==========================================================================
# Grid
# ==========================================================================
def test_grid_matlab_menyamai_rentang_modul_g() -> None:
    """Grid linear 0,05 eta sampai 3 eta, sama dengan pmOptimize MATLAB."""
    g = _grid_matlab([1000.0], 3.0)
    assert g[0] == pytest.approx(50.0)
    assert g[-1] == pytest.approx(3000.0)
    # jarak antar titik seragam (linear)
    d = np.diff(g)
    assert np.allclose(d, d[0])


def test_grid_pencarian_jauh_lebih_lebar_dan_logaritmik() -> None:
    """Grid pencarian harus menjangkau interval yang jauh lebih pendek."""
    g = _grid_pencarian([1000.0], 3.0)
    assert g[0] < _grid_matlab([1000.0], 3.0)[0] / 10
    # penjarakan logaritmik: rasio antar titik seragam
    rasio = g[1:] / g[:-1]
    assert np.allclose(rasio, rasio[0], rtol=1e-9)


# ==========================================================================
# Kelayakan tugas: beta menentukan apakah jadwal boleh direkomendasikan
# ==========================================================================
def test_beta_sekitar_satu_tidak_boleh_dijadwalkan() -> None:
    """Laju kegagalan konstan: penggantian tidak mengubah apa pun.

    Walaupun target keandalan menghasilkan tau_R yang pendek, rekomendasi tidak
    boleh berupa penggantian terjadwal, karena komponen baru secara statistik
    identik dengan komponen terpakai (SAE JA1011: tugas restorasi hanya berlaku
    bila ada umur aus yang dapat dikenali).
    """
    eq = {"X": _eq("X", beta=1.02, eta=1500.0)}
    h = analisis_peralatan(eq, "X", DEFAULT_CONFIG, r_target=0.9)
    assert h.rekomendasi["dasar_keputusan"] == "tidak berlaku"
    assert h.rekomendasi["interval_dianjurkan_hari"] is None
    # tau_R tetap dihitung dan ditampilkan sebagai informasi
    assert h.optimal_keandalan is not None
    assert any("INSPEKSI" in a or "inspeksi" in a for a in h.rekomendasi["alasan"])


def test_beta_kegagalan_dini_tidak_boleh_dijadwalkan() -> None:
    eq = {"X": _eq("X", beta=0.65, eta=1500.0)}
    h = analisis_peralatan(eq, "X", DEFAULT_CONFIG, r_target=0.9)
    assert h.rekomendasi["interval_dianjurkan_hari"] is None
    assert h.rekomendasi["dasar_keputusan"] == "tidak berlaku"
    # harus menyebut bahwa ketersediaan justru naik bila interval diperpanjang
    assert any("NAIK" in a for a in h.rekomendasi["alasan"])


def test_beta_aus_dengan_manfaat_menghasilkan_interval() -> None:
    """beta jelas di atas ambang aus dan Cf jauh di atas Cp: jadwal berlaku."""
    eq = {"X": _eq("X", beta=3.0, eta=1500.0)}
    h = analisis_peralatan(eq, "X", DEFAULT_CONFIG, r_target=0.5)
    assert h.rekomendasi["interval_dianjurkan_hari"] is not None
    assert h.rekomendasi["dasar_keputusan"] in {"biaya", "keandalan"}
    assert not h.optimal_biaya.di_batas_grid, "minimum harus interior untuk beta besar"


def test_target_keandalan_mengikat_bila_lebih_ketat_daripada_ekonomi() -> None:
    """Bila tau* melebihi tau_R, interval harus dipendekkan ke tau_R."""
    eq = {"X": _eq("X", beta=2.4, eta=2000.0)}
    h = analisis_peralatan(eq, "X", DEFAULT_CONFIG, r_target=0.99)
    if h.rekomendasi["interval_dianjurkan_hari"] is not None:
        assert h.rekomendasi["interval_dianjurkan_hari"] <= h.optimal_biaya.tau_hari + 1e-9


def test_peralatan_tanpa_kegagalan_ditolak_dengan_pesan_jelas() -> None:
    eq = {
        "X": EquipmentParams(
            tag="X", beta=1.0, eta=float("inf"), mtbf=float("inf"), n_cm=0,
            a_inh=1.0, a_op=1.0, mdt=48.0, mttr=24.0, kelas="pump",
        )
    }
    with pytest.raises(ValueError, match="tidak memiliki kegagalan korektif"):
        analisis_peralatan(eq, "X", DEFAULT_CONFIG)


def test_tag_tidak_dikenal_ditolak() -> None:
    with pytest.raises(ValueError, match="tidak ada pada dataset"):
        analisis_peralatan({}, "11-ZZZ-999", DEFAULT_CONFIG)


# ==========================================================================
# Kurva banyak peralatan
# ==========================================================================
def test_kurva_banyak_peralatan_melewati_yang_tak_layak() -> None:
    eq = {
        "A": _eq("A", beta=2.0, eta=1000.0),
        "B": EquipmentParams(
            tag="B", beta=1.0, eta=float("inf"), mtbf=float("inf"), n_cm=0,
            a_inh=1.0, a_op=1.0, mdt=48.0, mttr=24.0, kelas="pump",
        ),
    }
    out = kurva_banyak_peralatan(eq, ["A", "B", "TIDAK-ADA"], DEFAULT_CONFIG)
    assert [c["tag"] for c in out["kurva"]] == ["A"]
    dilewati = {d["tag"] for d in out["dilewati"]}
    assert dilewati == {"B", "TIDAK-ADA"}


def test_kurva_banyak_peralatan_memakai_grid_modul_g() -> None:
    """Rentang harus 0,05 eta sampai 3 eta agar tau* sebanding tabel modul G."""
    eq = {"A": _eq("A", beta=2.0, eta=1000.0)}
    out = kurva_banyak_peralatan(eq, ["A"], DEFAULT_CONFIG)
    c = out["kurva"][0]
    assert c["tau_hari"][0] == pytest.approx(50.0 / 24.0)
    assert c["tau_hari"][-1] == pytest.approx(3000.0 / 24.0)


def test_kurva_banyak_peralatan_penghematan_efektif_tak_negatif() -> None:
    eq = {"A": _eq("A", beta=0.8, eta=1000.0)}
    out = kurva_banyak_peralatan(eq, ["A"], DEFAULT_CONFIG)
    c = out["kurva"][0]
    assert c["penghematan_efektif_pct"] >= 0.0
    assert c["penghematan_efektif_pct"] == max(0.0, c["penghematan_pct"])
