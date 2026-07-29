"""
Uji end-to-end seluruh endpoint API memakai berkas Excel nyata.

Memakai `TestClient` sehingga tidak perlu server yang berjalan; seluruh uji ini
dapat dijalankan di CI. Di-skip bila berkas contoh tidak tersedia.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
NOTIF = ROOT / "data" / "20260531_Notification_RU_Balongan.xlsx"
ORDER = ROOT / "data" / "20260630_Order_RU_Balongan.xlsx"

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

#: Toleransi pembandingan R(t) terhadap laporan — lihat catatan penyimpangan
#: pada tests/test_validasi_laporan.py.
TOL_R = 0.002


def _resolve(p: Path, env: str) -> Path | None:
    override = os.getenv(env)
    if override and Path(override).is_file():
        return Path(override)
    return p if p.is_file() else None


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def ids(client: TestClient) -> Dict[str, str]:
    """Unggah kedua berkas sekali dan bagikan dataset_id ke seluruh uji."""
    notif = _resolve(NOTIF, "CDU_NOTIF_XLSX")
    if notif is None:
        pytest.skip("Berkas notifikasi contoh tidak ditemukan di data/.")
    with notif.open("rb") as f:
        r = client.post("/api/upload", files={"file": (notif.name, f, XLSX_MIME)})
    assert r.status_code == 200, r.text
    out = {"notif": r.json()["dataset_id"]}

    order = _resolve(ORDER, "CDU_ORDER_XLSX")
    if order is not None:
        with order.open("rb") as f:
            r2 = client.post("/api/upload", files={"file": (order.name, f, XLSX_MIME)})
        assert r2.status_code == 200, r2.text
        out["order"] = r2.json()["dataset_id"]
    return out


# ==========================================================================
# Sistem & metadata
# ==========================================================================
def test_health(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_meta_defaults(client: TestClient) -> None:
    d = client.get("/api/meta/defaults").json()
    assert d["config"]["window_end"] == "cutoff"
    assert d["config"]["beta_source"] == "equipment"
    assert d["config"]["cp"] == 1.0 and d["config"]["cf"] == 10.0
    assert d["config"]["mc_reps"] == 400
    assert d["beta_workbook"]["heater"] == pytest.approx(2.46877143309813, abs=1e-13)
    assert d["mttr_per_kelas"]["heater"] == 72.0
    assert d["mdt_default"] == 48.0


def test_meta_references_lengkap(client: TestClient) -> None:
    """Referensi wajib harus tersedia untuk halaman Metodologi.

    Enam belas rujukan pertama adalah daftar wajib awal; nomor 17 sampai 19
    ditambahkan bersama modul pencarian titik optimal (Ebeling untuk interval
    berbasis target keandalan, Barlow & Proschan untuk teorema pembaharuan, dan
    Dekker untuk kebijakan pengelompokan interval).
    """
    j = client.get("/api/meta/references").json()
    assert len(j["referensi"]) == 19
    assert {r["id"] for r in j["referensi"]} == set(range(1, 20))
    for r in j["referensi"]:
        assert r["kunci"] and r["dipakai_untuk"] and r["modul"]
    assert len(j["modul"]) >= 12
    # Rujukan baru harus benar benar tertaut ke modul titik optimal.
    titik = [r for r in j["referensi"] if "Titik optimal" in r["modul"]]
    assert len(titik) >= 3


def test_meta_domain(client: TestClient) -> None:
    j = client.get("/api/meta/domain").json()
    assert len(j["fs_map"]) == 67
    assert len(j["rbd_stages"]) == 18


# ==========================================================================
# Upload
# ==========================================================================
def test_upload_notifikasi(client: TestClient, ids) -> None:
    r = client.get(f"/api/datasets/{ids['notif']}/preview")
    assert r.status_code == 200
    j = r.json()
    assert j["kind"] == "notification"
    assert j["total_rows"] == 734


def test_upload_menolak_csv(client: TestClient) -> None:
    r = client.post("/api/upload", files={"file": ("a.csv", b"x,y\n1,2", "text/csv")})
    assert r.status_code == 400
    assert "tidak didukung" in r.json()["detail"]


def test_upload_menolak_xlsx_rusak(client: TestClient) -> None:
    r = client.post("/api/upload", files={"file": ("a.xlsx", b"bukan excel", XLSX_MIME)})
    assert r.status_code == 400
    assert "tidak dapat dibaca" in r.json()["detail"]


def test_upload_menolak_kosong(client: TestClient) -> None:
    r = client.post("/api/upload", files={"file": ("a.xlsx", b"", XLSX_MIME)})
    assert r.status_code == 400


# ==========================================================================
# Analisis
# ==========================================================================
def test_analyze_json_sah(client: TestClient, ids) -> None:
    """Tanggapan tidak boleh memuat NaN/Infinity (bukan JSON sah menurut RFC 8259)."""
    r = client.post("/api/analyze", json={"dataset_id": ids["notif"]})
    assert r.status_code == 200
    assert "NaN" not in r.text and "Infinity" not in r.text
    r.json()  # harus dapat diurai


def test_analyze_angka_kunci(client: TestClient, ids) -> None:
    a = client.post("/api/analyze", json={"dataset_id": ids["notif"]}).json()
    assert a["meta"]["t_obs_hours"] == pytest.approx(17064.0, abs=1e-6)
    assert a["meta"]["total_cm"] == 142
    assert len(a["equipment"]) == 67
    assert len(a["rbd_stages"]) == 18
    assert len(a["kpi"]) >= 6

    fs1 = next(x for x in a["rbd_system"] if x["sistem"] == "FS-1")
    assert fs1["a_op"] == pytest.approx(0.801, abs=0.001)
    assert fs1["a_inh"] == pytest.approx(0.966, abs=0.001)
    cdu = a["rbd_system"][-1]
    assert cdu["a_op"] == pytest.approx(0.658, abs=0.001)

    h30 = next(x for x in a["reliability_horizons"] if x["hari"] == 30)
    assert h30["r_fs1"] == pytest.approx(0.193, abs=TOL_R)
    assert h30["r_fs2"] == pytest.approx(0.564, abs=TOL_R)
    assert h30["r_fs3"] == pytest.approx(0.368, abs=TOL_R)
    assert h30["r_gabungan"] == pytest.approx(0.040, abs=TOL_R)


def test_analyze_menyediakan_data_seluruh_grafik(client: TestClient, ids) -> None:
    """Setiap grafik wajib (§8) harus punya data pendukungnya."""
    a = client.post("/api/analyze", json={"dataset_id": ids["notif"]}).json()
    assert a["pareto"]["equipment"]                     # grafik 1
    assert a["functional_system"]                        # grafik 2
    assert a["crosstab"]["values"]                       # grafik 3
    assert a["pareto"]["per_fs"]["FS-1"]                 # grafik 4
    assert any(r["plot_x"] for r in a["weibull_class"])  # grafik 5
    assert all(k in a["weibull_fs"][0] for k in ("beta_lo", "beta_hi"))  # grafik 6
    assert a["mrr_plots"] and a["mrr_plots"][0]["x"]     # grafik 7
    assert any(r["beta_crow_amsaa"] for r in a["weibull_equipment"])     # grafik 8
    assert len(a["reliability_curve"]["t_hari"]) == 400  # grafik 9
    assert a["availability"]                             # grafik 10
    assert a["reliability_horizons"]                      # grafik 11
    assert a["mrr_example"]["rows"]                       # contoh perhitungan
    assert a["reliability_life"] and a["laplace"]


def test_analyze_dataset_hilang(client: TestClient) -> None:
    r = client.post("/api/analyze", json={"dataset_id": "tidakada1234"})
    assert r.status_code == 404


def test_analyze_menolak_berkas_order(client: TestClient, ids) -> None:
    if "order" not in ids:
        pytest.skip("Berkas order contoh tidak tersedia.")
    r = client.post("/api/analyze", json={"dataset_id": ids["order"]})
    assert r.status_code == 400
    assert "ORDER" in r.json()["detail"]


def test_analyze_parameter_di_luar_batas(client: TestClient, ids) -> None:
    r = client.post("/api/analyze", json={"dataset_id": ids["notif"], "config": {"beta_kmin": 999}})
    assert r.status_code == 422


def test_analyze_unit_tidak_ada(client: TestClient, ids) -> None:
    """Prefix unit yang tidak ada harus memberi pesan informatif, bukan crash."""
    r = client.post("/api/analyze", json={"dataset_id": ids["notif"], "config": {"unit": "99-"}})
    assert r.status_code == 400
    assert "99-" in r.json()["detail"]


def test_perubahan_parameter_berpengaruh_dan_cache_tidak_bocor(client: TestClient, ids) -> None:
    nid = ids["notif"]
    a1 = client.post("/api/analyze", json={"dataset_id": nid, "config": {"window_end": "lastevent"}}).json()
    assert a1["meta"]["t_obs_hours"] == pytest.approx(16992.0, abs=1e-6)

    a2 = client.post("/api/analyze", json={"dataset_id": nid, "config": {"beta_source": "workbook"}}).json()
    fs1w = next(x for x in a2["rbd_system"] if x["sistem"] == "FS-1")
    assert fs1w["r_1bln"] == pytest.approx(0.582, abs=TOL_R)

    # Kembali ke default harus menghasilkan angka semula.
    a3 = client.post("/api/analyze", json={"dataset_id": nid}).json()
    fs1d = next(x for x in a3["rbd_system"] if x["sistem"] == "FS-1")
    assert fs1d["r_1bln"] == pytest.approx(0.193, abs=TOL_R)
    assert a3["meta"]["t_obs_hours"] == pytest.approx(17064.0, abs=1e-6)


# ==========================================================================
# RBD interaktif (§6)
# ==========================================================================
def test_rbd_diagram(client: TestClient, ids) -> None:
    d = client.post("/api/rbd/diagram", json={"dataset_id": ids["notif"], "tags": ["*"]}).json()
    assert len(d["fs"]) == 3
    assert len(d["fs"][0]["stages"]) == 6
    assert len(d["fs"][1]["stages"]) == 4
    assert len(d["fs"][2]["stages"]) == 8

    spof = {b["tag"] for f in d["fs"] for s in f["stages"] for b in s["blocks"] if b["spof"]}
    assert {"11-F-101", "11-C-101", "11-E-114", "11-C-106"} <= spof
    # Pompa pada stage paralel tidak boleh ditandai SPOF.
    assert "11-P-101A" not in spof

    notasi = [s["notasi"] for f in d["fs"] for s in f["stages"] if s["tipe"] == "par"]
    assert any("1-dari-4" in n for n in notasi)
    assert d["legend"]["kritikalitas"] and d["legend"]["konfigurasi"]


def test_rbd_equipment_detail(client: TestClient, ids) -> None:
    r = client.post("/api/rbd/equipment", json={"dataset_id": ids["notif"], "tags": ["11-F-101"]})
    assert r.status_code == 200
    j = r.json()
    assert j["detail"]["beta"] == pytest.approx(1.054, abs=0.005)
    assert j["detail"]["spof"] is True
    assert j["detail"]["n_cm"] == 11
    assert len(j["kurva"]["t_hari"]) == 200
    assert j["weibull"]["beta_crow_amsaa"] == pytest.approx(2.4688, abs=0.001)


def test_rbd_seleksi_paralel_menghasilkan_redundansi(client: TestClient, ids) -> None:
    """Dua pompa pada stage paralel yang sama -> R gabungan = nilai stage."""
    r = client.post(
        "/api/rbd/selection",
        json={"dataset_id": ids["notif"], "tags": ["11-P-102A", "11-P-102B"]},
    ).json()
    r30 = next(h["r"] for h in r["horizon"] if h["hari"] == 30)
    assert r30 == pytest.approx(0.944473, abs=1e-4)
    assert "paralel" in r["kelompok"][0]["digabung"]
    assert r["n_cm_total"] == 15
    assert r["a_op"] == pytest.approx(0.998337, abs=1e-5)


def test_rbd_seleksi_seri_adalah_perkalian(client: TestClient, ids) -> None:
    """Dua SPOF pada stage seri berbeda -> R gabungan = Ra x Rb."""
    r = client.post(
        "/api/rbd/selection",
        json={"dataset_id": ids["notif"], "tags": ["11-F-101", "11-C-101"]},
    ).json()
    r30 = next(h["r"] for h in r["horizon"] if h["hari"] == 30)
    assert r30 == pytest.approx(0.64674 * 0.91907, abs=1e-4)
    assert all("seri" in g["digabung"] for g in r["kelompok"])


def test_rbd_seleksi_tag_tidak_dikenal(client: TestClient, ids) -> None:
    r = client.post("/api/rbd/selection", json={"dataset_id": ids["notif"], "tags": ["11-XXX-999"]})
    assert r.status_code == 400


# ==========================================================================
# Monte Carlo, PM, kekritisan
# ==========================================================================
def test_montecarlo(client: TestClient, ids) -> None:
    m = client.post("/api/montecarlo", json={"dataset_id": ids["notif"]}).json()
    assert m["reps"] == 400
    assert len(m["tabel"]) == 4
    assert len(m["sampel"]["FS-1"]) == 400
    for row in m["tabel"]:
        assert row["a_p10"] <= row["a_p50"] <= row["a_p90"]


def test_montecarlo_reprodusibel(client: TestClient, ids) -> None:
    body = {"dataset_id": ids["notif"]}
    a = client.post("/api/montecarlo", json=body).json()["tabel"]
    b = client.post("/api/montecarlo", json=body).json()["tabel"]
    assert [r["a_mean"] for r in a] == [r["a_mean"] for r in b]


def test_pm_optimize_tabel_71(client: TestClient, ids) -> None:
    g = client.post("/api/pm-optimize", json={"dataset_id": ids["notif"]}).json()
    tau = {r["bad_actor"]: r["tau_opt_hari"] for r in g["tabel"]}
    assert tau["11-P-102B"] == pytest.approx(255, abs=1)
    assert tau["11-F-101"] == pytest.approx(198, abs=1)
    assert tau["11-E-114"] == pytest.approx(211, abs=1)
    assert len(g["kurva"]) == 3


def test_criticality(client: TestClient, ids) -> None:
    j = client.post("/api/criticality", json={"dataset_id": ids["notif"]}).json()
    n = j["ringkasan"]["n_dinilai"]
    assert n == 54                                   # tag dengan riwayat kegagalan
    assert len(j["kekritisan"]) == n
    assert len(j["jackknife"]["titik"]) == n
    assert len(j["matriks_risiko"]) == n
    assert j["tindakan"] and "Prioritas 1." in j["tindakan"][0]["narasi"]
    # Skor risiko = Li x Ci (API 580/581)
    for r in j["kekritisan"]:
        assert r["skor_risiko"] == r["indeks_frekuensi"] * r["indeks_konsekuensi"]


# ==========================================================================
# Biaya & NSGA-II (§7)
# ==========================================================================
def test_costs_tanpa_berkas_order(client: TestClient, ids) -> None:
    c = client.post("/api/costs", json={"dataset_id": ids["notif"]}).json()
    assert c["tersedia"] is False
    assert c["cp_default"] == 1.0 and c["cf_default"] == 10.0


def test_costs_dengan_berkas_order(client: TestClient, ids) -> None:
    if "order" not in ids:
        pytest.skip("Berkas order contoh tidak tersedia.")
    c = client.post(
        "/api/costs", json={"dataset_id": ids["notif"], "order_dataset_id": ids["order"]}
    ).json()
    assert c["tersedia"] is True
    assert c["n_order"] == 758
    assert c["n_tertaut_notifikasi"] == 593
    assert c["cp_global"] > 0 and c["cf_global"] > 0

    per_tag = {t["tag"]: t for t in c["per_tag"]}
    assert per_tag

    # Tag hasil IMPUTASI harus memakai rasio populasi, bukan mencampur skala.
    imputed = [t for t in c["per_tag"] if "imputasi" in t["asal"]]
    assert imputed, "harus ada tag yang biayanya diimputasi"
    ratios = {round(t["rasio"], 6) for t in imputed}
    assert len(ratios) == 1, "seluruh tag imputasi harus memakai satu rasio populasi"
    assert abs(next(iter(ratios)) - c["rasio_global"]) < 1e-6

    # Rasio ekstrem yang berasal dari data nyata WAJIB ditandai agar UI memperingatkan.
    for t in c["per_tag"]:
        if t["rasio"] > 50 and min(t["n_korektif"], t["n_preventif"]) < 5:
            assert t["rasio_ekstrem"] is True


def test_cost_optimize_pareto(client: TestClient, ids) -> None:
    body = {"dataset_id": ids["notif"]}
    if "order" in ids:
        body["order_dataset_id"] = ids["order"]
    # Konfigurasi kecil agar uji cepat namun tetap menghasilkan front.
    body["config"] = {"ga_pop_size": 24, "ga_generations": 15}
    o = client.post("/api/cost-optimize", json=body).json()

    assert o["variabel"], "harus ada variabel keputusan"
    assert len(o["pareto"]) >= 5
    assert o["garis_dasar"]["a_op_sistem"] == pytest.approx(0.658, abs=0.001)
    assert o["konfigurasi_ga"]["pop_size"] == 24
    assert len(o["tradeoff"]["tau_hari"]) == 160

    for p in o["pareto"]:
        assert len(p["interval"]) == len(o["variabel"])
        assert 0.0 < p["a_op_sistem"] <= 1.0
        assert p["biaya_tahunan"] > 0
    # Front harus terurut menaik menurut biaya (monoton) ...
    biaya = [p["biaya_tahunan"] for p in o["pareto"]]
    assert biaya == sorted(biaya)
    # ... dan non-dominated: ketersediaan juga menaik seiring biaya.
    aop = [p["a_op_sistem"] for p in o["pareto"]]
    assert aop == sorted(aop)


def test_cost_optimize_reprodusibel(client: TestClient, ids) -> None:
    body = {"dataset_id": ids["notif"], "config": {"ga_pop_size": 16, "ga_generations": 8, "ga_seed": 42}}
    a = client.post("/api/cost-optimize", json=body).json()["pareto"]
    b = client.post("/api/cost-optimize", json=body).json()["pareto"]
    assert [p["biaya_tahunan"] for p in a] == [p["biaya_tahunan"] for p in b]


# ==========================================================================
# Ekspor
# ==========================================================================
def test_export_excel(client: TestClient, ids) -> None:
    r = client.post("/api/export/excel", json={"dataset_id": ids["notif"]})
    assert r.status_code == 200
    assert r.content[:2] == b"PK"          # arsip zip = xlsx
    assert len(r.content) > 20_000
    assert "attachment" in r.headers.get("content-disposition", "")


def test_export_csv(client: TestClient, ids) -> None:
    r = client.post("/api/export/csv/B_Equipment", json={"dataset_id": ids["notif"]})
    assert r.status_code == 200
    assert r.text.startswith("tag;")


def test_export_csv_tabel_tidak_dikenal(client: TestClient, ids) -> None:
    r = client.post("/api/export/csv/TidakAda", json={"dataset_id": ids["notif"]})
    assert r.status_code == 404
