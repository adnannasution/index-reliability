"""
Kekritisan & mesin rekomendasi strategi pemeliharaan (modul J).

Alur keputusan mengikuti praktik baku:
  * SAE JA1011 / JA1012: logika pemilihan strategi Reliability-Centered
    Maintenance (RCM): apakah kegagalan dapat dicegah jadwal, dideteksi
    kondisi, atau lebih baik dibiarkan sampai gagal secara terkendali.
  * ISO 14224:2016     : taksonomi, definisi downtime, kekritisan.
  * API 580 / API 581  : Risk-Based Inspection: Risk = PoF x CoF, dinyatakan
    sebagai matriks indeks frekuensi x indeks konsekuensi 5x5.
  * Knights, P.F. (2001): diagram jack-knife (kronis vs akut), Journal of
    Quality in Maintenance Engineering 7(4).
  * Barlow & Hunter (1960): interval optimal age replacement.
  * Teori Poisson/renewal: kebutuhan stok suku cadang pada tingkat layanan.

Port dari MATLAB: critWeight, likeIndex, consIndex, riskBand, poissQuantile,
chooseStrategy, cbmParam, tbmHint, rcaHint, recParagraph (baris 2306-2508).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from app.config.defaults import CRIT_WEIGHT, Config
from app.core.fs_mapping import fs_name, is_redundant_tag
from app.core.pm_optimization import pm_optimize
from app.core.rbd import EquipmentParams
from app.core.reliability import ifr_region


# ==========================================================================
# Indeks risiko
# ==========================================================================
def crit_weight(c: Optional[str], cfg: Config) -> float:
    """Bobot konsekuensi dari kolom Criticality SAP: port `critWeight()`.

    Hanya HURUF PERTAMA yang dipakai (H/M/L/I/Z), sesuai MATLAB.
    """
    if not c:
        return CRIT_WEIGHT["default"]
    return CRIT_WEIGHT.get(str(c).strip()[:1].upper(), CRIT_WEIGHT["default"])


def like_index(f_per_year: float) -> int:
    """Indeks frekuensi 1..5 dari kegagalan per tahun: port `likeIndex()`."""
    if f_per_year >= 6.0:
        return 5
    if f_per_year >= 3.0:
        return 4
    if f_per_year >= 1.5:
        return 3
    if f_per_year >= 0.7:
        return 2
    return 1


def cons_index(h: float) -> int:
    """Indeks konsekuensi 1..5 dari jam henti ekuivalen: port `consIndex()`."""
    if h >= 72:
        return 5
    if h >= 36:
        return 4
    if h >= 16:
        return 3
    if h >= 6:
        return 2
    return 1


def risk_band(li: int, ci: int) -> Tuple[int, str]:
    """Skor & pita risiko pada matriks 5x5: port `riskBand()`.

    Risk = PoF x CoF (API 580/581), dipetakan ke empat pita.
    """
    s = int(li) * int(ci)
    if s >= 15:
        band = "Ekstrem"
    elif s >= 9:
        band = "Tinggi"
    elif s >= 4:
        band = "Sedang"
    else:
        band = "Rendah"
    return s, band


def poisson_quantile(p: float, lam: float) -> int:
    """Kuantil Poisson terkecil q dengan P(N <= q) >= p: port `poissQuantile()`.

    Dipakai untuk stok minimum suku cadang pada tingkat layanan `p`, dengan
    lambda = ekspektasi jumlah kegagalan pada horizon yang ditinjau.
    """
    if not np.isfinite(lam) or lam <= 0:
        return 0
    term = math.exp(-lam)
    if term == 0.0:  # pengaman lambda besar (underflow)
        return int(math.ceil(lam + 3.0 * math.sqrt(lam)))
    c = term
    q = 0
    while c < p and q < 500:
        q += 1
        term = term * lam / q
        c += term
    return q


# ==========================================================================
# Teks bantu strategi (per kelas peralatan)
# ==========================================================================
def cbm_param(kelas: str) -> str:
    """Parameter kondisi yang lazim dipantau: port `cbmParam()`."""
    return {
        "pump": "vibrasi (ISO 10816), suhu bearing, dan arus motor",
        "exchanger": "beda tekanan, pendekatan suhu, dan duty aktual",
        "heater": "suhu skin tube, kadar oksigen gas buang, dan efisiensi pembakaran",
        "vessel": "beda tekanan, level antarmuka, dan kadar air keluaran",
        "column": "profil suhu dan beda tekanan antar tray",
        "injection": "laju dosis, tekanan discharge, dan level tangki bahan kimia",
    }.get(str(kelas).lower(), "parameter proses utama dan kondisi mekanis")


def tbm_hint(kelas: str) -> str:
    """Port `tbmHint()`."""
    return {
        "pump": "penggantian bearing dan mechanical seal, pemeriksaan alignment, serta uji performa",
        "exchanger": "pembersihan bundle, pemeriksaan gasket, dan uji kebocoran",
        "heater": "inspeksi burner, pemeriksaan skin thermocouple, dan pembersihan ringan (decoking)",
        "vessel": "mud wash, pemeriksaan grid dan elektroda, serta kalibrasi instrumen level",
        "column": "inspeksi internal tray dan pembersihan distributor saat kesempatan berhenti",
        "injection": "kalibrasi pompa dosis, pembersihan strainer, dan penggantian diafragma",
    }.get(str(kelas).lower(), "restorasi komponen aus sesuai rekomendasi pabrikan")


def rca_hint(kelas: str) -> str:
    """Port `rcaHint()`."""
    return {
        "pump": ("periksa kelurusan kopling, kondisi pondasi, NPSH tersedia, dan kesesuaian "
                 "titik operasi terhadap kurva pompa"),
        "exchanger": "periksa laju aliran, potensi vibrasi induksi aliran, dan mutu air pendingin",
        "heater": "periksa distribusi api, keseragaman beban tube, dan kualitas bahan bakar",
        "vessel": "periksa mutu bahan kimia demulsifier, tegangan grid, dan variabilitas umpan crude",
    }.get(str(kelas).lower(),
          "lakukan analisis akar masalah terstruktur bersama tim operasi dan inspeksi")


# ==========================================================================
# Penilaian satu peralatan
# ==========================================================================
@dataclass
class Assessment:
    """Hasil penilaian kekritisan + strategi satu peralatan."""

    tag: str
    fs: str
    kelas: str
    crit: str
    n_cm: int
    f_per_year: float
    mdt: float
    downtime_year: float
    redundant: bool
    li: int
    ci: int
    risk: int
    band: str
    beta: float
    eta: float
    mtbf_days: float
    a_op: float
    trend: str
    tau_days: float
    saving_pct: float
    strategy: str = ""
    action: str = ""
    interval: str = ""
    justification: str = ""
    effectiveness: float = 0.0
    avoidable_hours: float = 0.0
    stock: int = 0
    reorder_point: int = 0
    kpi: str = ""


def _choose_strategy(a: Assessment, cfg: Config) -> None:
    """Logika pemilihan strategi bergaya RCM: port `chooseStrategy()` (baris 2420).

    Urutan pemeriksaan (SAE JA1011):
      1) pola kegagalan dini (beta < betaDFR) -> akar masalah, bukan PM berkala
      2) pola aus + PM hemat                  -> TBM dengan interval optimal
      3) degradasi terpantau + risiko cukup   -> CBM
      4) risiko rendah + ada cadangan         -> run to failure terkendali
      5) selain itu                           -> inspeksi berkala
    """
    detectable = str(a.kelas).lower() in {"pump", "exchanger", "heater", "vessel"}
    worsening = a.trend == "memburuk"

    if a.beta < cfg.beta_dfr:
        a.strategy = "Investigasi akar masalah (RCA)"
        a.action = (f"Telusuri mutu pemasangan, kesesuaian material, dan prosedur start-up; "
                    f"{rca_hint(a.kelas)}")
        a.interval = "Sekali, target tuntas 60 hari"
        a.justification = (f"beta {a.beta:.2f} di bawah {cfg.beta_dfr:.2f} menandakan kegagalan "
                           f"dini, sehingga penggantian berkala tidak menurunkan laju kegagalan")
        a.effectiveness = cfg.eff_rca

    elif a.beta >= cfg.beta_wear and a.saving_pct >= cfg.pm_min_saving:
        a.strategy = "Pemeliharaan berbasis waktu (TBM)"
        a.action = f"Restorasi berkala meliputi {tbm_hint(a.kelas)}"
        a.interval = f"{a.tau_days:.0f} hari"
        a.justification = (f"beta {a.beta:.2f} menunjukkan mekanisme aus dan interval optimal age "
                           f"replacement menekan biaya {a.saving_pct:.0f} persen terhadap run to failure")
        a.effectiveness = min(a.saving_pct / 100.0, cfg.eff_tbm_cap)

    elif detectable and a.risk >= cfg.risk_cbm:
        a.strategy = "Pemeliharaan berbasis kondisi (CBM)"
        a.action = (f"Pantau {cbm_param(a.kelas)}, tetapkan ambang peringatan, dan siapkan "
                    f"tindak lanjut terjadwal saat ambang terlampaui")
        a.interval = f"Pemantauan {cfg.cbm_freq}"
        a.justification = (f"beta {a.beta:.2f} mendekati satu sehingga interval tetap kurang "
                           f"efektif, sedangkan degradasi masih terbaca dari parameter proses")
        a.effectiveness = cfg.eff_cbm

    elif a.risk <= cfg.risk_rtf and a.redundant:
        a.strategy = "Run to failure terkendali"
        a.action = ("Tangani secara korektif terencana, pastikan unit cadangan siap pakai "
                    "dan suku cadang tersedia di gudang")
        a.interval = "Tidak terjadwal"
        a.justification = (f"skor risiko {a.risk} ({a.band}) dengan redundansi tersedia, sehingga "
                           f"biaya pemeliharaan terjadwal tidak sebanding manfaatnya")
        a.effectiveness = 0.0

    else:
        a.strategy = "Inspeksi berkala terjadwal"
        a.action = f"Inspeksi visual dan pengukuran dasar mencakup {cbm_param(a.kelas)}"
        a.interval = f"{max(30.0, min(180.0, a.tau_days)):.0f} hari"
        a.justification = (f"bukti aus belum kuat (beta {a.beta:.2f}) namun tingkat risiko "
                           f"{a.band.lower()} menuntut pemeriksaan rutin")
        a.effectiveness = cfg.eff_insp

    if worsening:
        a.action += (". Laju kegagalan sedang meningkat, sehingga frekuensi pemeriksaan perlu "
                     "dinaikkan dan hasilnya ditinjau setelah dua siklus")
        a.justification += ("; uji tren menunjukkan intensitas kegagalan meningkat menurut "
                            "waktu kalender")
        a.effectiveness = min(a.effectiveness + cfg.eff_trend_bonus, 0.65)
    if a.redundant and a.strategy != "Run to failure terkendali":
        a.action += (". Jalankan uji putar unit cadangan secara bergilir untuk mencegah "
                     "kegagalan common cause")


def assess_all(
    eq: Mapping[str, EquipmentParams],
    tags: Sequence[str],
    n_cm: Mapping[str, int],
    kelas: Mapping[str, str],
    crit: Mapping[str, str],
    fs_of_tag: Mapping[str, int],
    beta_crow: Mapping[str, float],
    p_class_laplace: Mapping[str, float],
    cfg: Config,
    *,
    cost_by_tag: Optional[Mapping[str, Dict[str, float]]] = None,
) -> List[Assessment]:
    """Nilai seluruh peralatan yang punya riwayat kegagalan: port modul J1/J2."""
    out: List[Assessment] = []
    for tg in tags:
        if int(n_cm.get(tg, 0)) == 0 or tg not in eq:
            continue
        e = eq[tg]
        f_yr = 8760.0 / e.mtbf if np.isfinite(e.mtbf) and e.mtbf > 0 else 0.0
        dt_yr = f_yr * e.mdt
        red = is_redundant_tag(tg)
        wc = crit_weight(crit.get(tg), cfg)
        # Konsekuensi ekuivalen: jam henti dibobot kekritisan SAP, dikurangi
        # bila tersedia redundansi paralel pada RBD (cfg.red_credit).
        c_eq = e.mdt * wc * (1.0 - cfg.red_credit * (1.0 if red else 0.0))
        li = like_index(f_yr)
        ci = cons_index(c_eq)
        risk, band = risk_band(li, ci)

        # Tren: Crow-AMSAA per tag lebih dahulu; bila kosong pakai Laplace kelas.
        trend = "stasioner"
        bca = beta_crow.get(tg)
        if bca is not None and np.isfinite(bca) and bca >= cfg.ca_ifr:
            trend = "memburuk"
        elif bca is not None and np.isfinite(bca) and bca <= cfg.ca_dfr:
            trend = "membaik"
        else:
            p = p_class_laplace.get(str(kelas.get(tg, "")).lower())
            if p is not None and p < 0.05:
                trend = "memburuk"

        c_p, c_f = cfg.cp, cfg.cf
        if cost_by_tag and tg in cost_by_tag:
            c = cost_by_tag[tg]
            if c.get("cp", 0) > 0 and c.get("cf", 0) > 0:
                c_p, c_f = float(c["cp"]), float(c["cf"])
        opt = pm_optimize(e.beta, e.eta, c_p, c_f)

        a = Assessment(
            tag=tg, fs=fs_name(fs_of_tag.get(tg, 0)), kelas=kelas.get(tg, "other"),
            crit=str(crit.get(tg, "")), n_cm=int(n_cm.get(tg, 0)),
            f_per_year=f_yr, mdt=e.mdt, downtime_year=dt_yr, redundant=red,
            li=li, ci=ci, risk=risk, band=band,
            beta=float(e.beta), eta=float(e.eta),
            mtbf_days=float(e.mtbf / 24.0) if np.isfinite(e.mtbf) else float("inf"),
            a_op=float(e.a_op), trend=trend,
            tau_days=opt.tau_opt_days, saving_pct=opt.saving_pct_effective,
        )
        _choose_strategy(a, cfg)
        a.avoidable_hours = a.downtime_year * a.effectiveness
        # Stok suku cadang: kuantil Poisson pada horizon 12 bulan dan lead time.
        a.stock = poisson_quantile(cfg.svc_level, a.f_per_year)
        a.reorder_point = poisson_quantile(cfg.svc_level, a.f_per_year * cfg.lead_months / 12.0)
        if a.effectiveness > 0:
            mtbf_target = a.mtbf_days / max(1.0 - a.effectiveness, 0.35)
            a_target = min(0.999, a.a_op + (1.0 - a.a_op) * a.effectiveness)
            a.kpi = (f"MTBF {a.mtbf_days:.0f} menjadi {mtbf_target:.0f} hari dan "
                     f"A_op {a.a_op:.3f} menjadi {a_target:.3f} dalam 12 bulan")
        else:
            a.kpi = (f"Pertahankan MTBF minimal {a.mtbf_days:.0f} hari dan tinjau ulang "
                     f"bila tren berubah")
        out.append(a)

    # Urut: risiko, lalu manfaat (port `[~,ord] = sort([J.risk] + [J.avoid]/1000, 'descend')`).
    out.sort(key=lambda x: -(x.risk + x.avoidable_hours / 1000.0))
    return out


def build_module_j(assessments: List[Assessment], cfg: Config) -> Dict[str, Any]:
    """Susun seluruh tabel & data grafik modul J untuk API."""
    j = assessments
    total_dt = float(sum(a.downtime_year for a in j))
    total_av = float(sum(a.avoidable_hours for a in j))

    kekritisan = [
        {
            "tag": a.tag, "fs": a.fs, "kelas": a.kelas, "kritikalitas": a.crit,
            "n_cm": a.n_cm, "gagal_per_thn": round(a.f_per_year, 1),
            "mdt_jam": round(a.mdt, 0), "downtime_jam_thn": round(a.downtime_year, 0),
            "redundan": "ya" if a.redundant else "tidak",
            "indeks_frekuensi": a.li, "indeks_konsekuensi": a.ci,
            "skor_risiko": a.risk, "pita_risiko": a.band,
        }
        for a in j
    ]
    strategi = [
        {
            "tag": a.tag, "fs": a.fs, "beta": round(a.beta, 2), "tren": a.trend,
            "risiko": a.band, "strategi": a.strategy, "interval": a.interval,
            "downtime_dihindarkan_jam_thn": round(a.avoidable_hours, 0),
            "dasar_keputusan": a.justification,
        }
        for a in j
    ]
    suku_cadang = [
        {
            "tag": a.tag, "fs": a.fs, "kelas": a.kelas,
            "ekspektasi_gagal_12bln": round(a.f_per_year, 1),
            "stok_minimum": a.stock, "titik_pesan_ulang": a.reorder_point,
            "tingkat_layanan": f"{cfg.svc_level*100:.0f}% dalam 12 bulan",
        }
        for a in j if a.f_per_year >= cfg.spare_min_rate
    ]
    tindakan = [
        {
            "prioritas": i + 1, "tag": a.tag, "fs": a.fs, "risiko": a.band,
            "strategi": a.strategy, "tindakan": a.action, "interval": a.interval,
            "kpi_target": a.kpi, "narasi": rec_paragraph(i + 1, a),
        }
        for i, a in enumerate(j[: cfg.rec_top_n])
    ]

    # Jack-knife (Knights 2001): frekuensi vs durasi, garis iso-downtime.
    jackknife = [
        {
            "tag": a.tag, "fs": a.fs,
            "gagal_per_thn": max(a.f_per_year, 0.05),
            "mdt_jam": max(a.mdt, 1.0),
            "downtime_jam_thn": a.downtime_year, "pita_risiko": a.band,
        }
        for a in j
    ]
    fx = [d["gagal_per_thn"] for d in jackknife]
    my = [d["mdt_jam"] for d in jackknife]

    strat_counts: Dict[str, int] = {}
    for a in j:
        strat_counts[a.strategy] = strat_counts.get(a.strategy, 0) + 1

    return {
        "kekritisan": kekritisan,
        "strategi": strategi,
        "suku_cadang": suku_cadang or [],
        "tindakan": tindakan,
        "jackknife": {
            "titik": jackknife,
            "median_frekuensi": float(np.median(fx)) if fx else 0.0,
            "median_durasi": float(np.median(my)) if my else 0.0,
            "iso_downtime": cfg.iso_downtime,
        },
        "matriks_risiko": [
            {"tag": a.tag, "li": a.li, "ci": a.ci, "risk": a.risk, "band": a.band}
            for a in j
        ],
        "ringkasan": {
            "total_downtime_jam_thn": round(total_dt, 0),
            "total_dihindarkan_jam_thn": round(total_av, 0),
            "persen_dihindarkan": round(100.0 * total_av / total_dt, 0) if total_dt > 0 else 0.0,
            "n_dinilai": len(j),
            "n_ekstrem": sum(1 for a in j if a.band == "Ekstrem"),
            "n_tinggi": sum(1 for a in j if a.band == "Tinggi"),
            "strategi_terpilih": strat_counts,
        },
    }


def rec_paragraph(rank: int, a: Assessment) -> str:
    """Kalimat rekomendasi bergaya laporan reliability engineer: port `recParagraph()`."""
    tren = ""
    if a.trend == "memburuk":
        tren = " Laju kegagalannya sedang meningkat."
    elif a.trend == "membaik":
        tren = " Laju kegagalannya menunjukkan perbaikan."
    red = " Peralatan ini memiliki unit cadangan paralel." if a.redundant else ""
    just = a.justification[:1].upper() + a.justification[1:] if a.justification else ""
    return (
        f"Prioritas {rank}. {a.tag} ({a.fs}, {a.kelas}, kritikalitas {a.crit})\n"
        f"  Kondisi  : {a.n_cm} kegagalan pada jendela pengamatan, setara "
        f"{a.f_per_year:.1f} kejadian per tahun dengan waktu henti {a.mdt:.0f} jam per "
        f"kejadian atau {a.downtime_year:.0f} jam per tahun. Skor risiko {a.risk} "
        f"({a.band}).{tren}{red}\n"
        f"  Bukti    : parameter bentuk Weibull {a.beta:.2f} ({ifr_region(a.beta)}), "
        f"MTBF {a.mtbf_days:.0f} hari, ketersediaan operasional {a.a_op:.3f}. {just}.\n"
        f"  Strategi : {a.strategy}, interval {a.interval}.\n"
        f"  Tindakan : {a.action}.\n"
        f"  Manfaat  : potensi pengurangan {a.avoidable_hours:.0f} jam henti per tahun "
        f"({a.avoidable_hours/24:.1f} hari).\n"
        f"  KPI target: {a.kpi}.\n"
    )
