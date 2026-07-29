"""
Analisis interval pemeliharaan terhadap waktu: biaya, keandalan, dan titik optimal.

Modul ini melengkapi `pm_optimization.py` (yang mereproduksi modul G MATLAB apa
adanya) dengan tiga kemampuan tambahan yang diminta:

  1. kurva untuk SETIAP tag peralatan yang dipilih pengguna, bukan hanya bad
     actor tiap Functional System;
  2. analisis pada dua lingkup: satu tag peralatan, atau satu Functional System
     dengan interval bersama (block replacement);
  3. grafik titik optimal bersumbu-y ganda: laju biaya dan keandalan terhadap
     waktu, beserta rekomendasi bernalar.

LANDASAN RUMUS
--------------
Laju biaya jangka panjang kebijakan age replacement (Barlow & Hunter, 1960):

                 Cp * R(tau) + Cf * [1 - R(tau)]
    C(tau)  =  ------------------------------------ ,    L(tau) = integral_0^tau R(t) dt
                            L(tau)

Pembilang adalah ekspektasi biaya satu siklus: bila peralatan bertahan sampai
umur tau maka terjadi penggantian terjadwal berbiaya Cp, bila tidak maka terjadi
kegagalan berbiaya Cf. Penyebut adalah ekspektasi panjang siklus.

Keandalan pada saat penggantian, yaitu peluang peralatan mencapai umur tau tanpa
gagal (Rausand & Hoyland, System Reliability Theory):

    R(tau) = exp( -(tau/eta)^beta )

Laju kegagalan efektif di bawah kebijakan tersebut, dari teorema pembaharuan
(renewal reward theorem; Barlow & Proschan, Mathematical Theory of Reliability):

    lambda_eff(tau) = [1 - R(tau)] / L(tau)
    MTBF_eff(tau)   = 1 / lambda_eff(tau)
    A_op(tau)       = MTBF_eff / (MTBF_eff + MDT)          (ISO 14224:2016)

Saat tau menuju tak hingga, lambda_eff menuju 1/MTTF sehingga kebijakan kembali
menjadi run to failure. Sifat ini dipakai sebagai pemeriksaan batas.

Interval berbasis TARGET KEANDALAN, yaitu umur ketika keandalan turun ke tingkat
minimum yang masih diterima (Ebeling, An Introduction to Reliability and
Maintainability Engineering; logika ambang kegagalan yang dapat diterima juga
menjadi dasar pemilihan tugas pada SAE JA1012):

    tau_R = eta * ( -ln R_target )^(1/beta)

Untuk tingkat SISTEM, satu interval yang sama diterapkan pada seluruh peralatan
di dalamnya. Kebijakan ini adalah block replacement dengan siklus bersama
(Barlow & Proschan; tinjauan kebijakan pengelompokan pada Dekker, Applications
of maintenance optimization models). Pilihan ini bukan sekadar penyederhanaan:
pada kilang, satu jendela berhenti memang dipakai bersama oleh seluruh peralatan
dalam satu Functional System, sehingga interval bersama adalah keputusan yang
benar-benar diambil. Penggabungan keandalan antar peralatan memakai logika
seri-paralel RBD (Rausand & Hoyland).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy.special import gamma as gamma_fn

from app.config.defaults import Config
from app.core.fs_mapping import RBD_STAGES, fs_name, stages_of_fs
from app.core.rbd import EquipmentParams
from app.core.reliability import MATLAB_EPS, ifr_region

#: Jumlah titik pada grid interval. Cukup halus untuk membaca titik minimum.
N_GRID = 260

#: Jumlah titik integrasi L(tau). Nilai 150 sama dengan modul G MATLAB.
N_QUAD = 150


# ==========================================================================
# 1. Besaran kebijakan pada satu deret interval
# ==========================================================================
def _cycle_length(beta: float, eta: float, tau: np.ndarray) -> np.ndarray:
    """L(tau) = integral_0^tau exp(-(t/eta)^beta) dt, tervektorisasi atas tau."""
    u = np.linspace(0.0, 1.0, N_QUAD)
    t = tau[:, None] * u[None, :]
    with np.errstate(over="ignore", under="ignore"):
        r = np.exp(-((t / eta) ** beta))
    return np.trapezoid(r, t, axis=1)


@dataclass
class KurvaPeralatan:
    """Besaran kebijakan satu peralatan pada seluruh grid interval."""

    tag: str
    beta: float
    eta: float
    mdt: float
    cp: float
    cf: float
    tau_hours: np.ndarray
    r_tau: np.ndarray            # keandalan saat penggantian
    cost_rate: np.ndarray        # biaya per jam
    lambda_eff: np.ndarray       # kegagalan per jam
    a_op: np.ndarray             # ketersediaan operasional
    cost_rtf: float              # laju biaya run to failure
    mttf: float


def kurva_peralatan(
    e: EquipmentParams, tau_hours: np.ndarray, cp: float, cf: float
) -> KurvaPeralatan:
    """Hitung C(tau), R(tau), lambda_eff(tau), dan A_op(tau) untuk satu peralatan."""
    tau = np.clip(np.asarray(tau_hours, dtype=float), 1e-6, None)
    beta, eta = float(e.beta), float(e.eta)

    L = np.maximum(_cycle_length(beta, eta, tau), MATLAB_EPS)
    with np.errstate(over="ignore", under="ignore"):
        r_tau = np.exp(-((tau / eta) ** beta))

    cost = (cp * r_tau + cf * (1.0 - r_tau)) / L
    lam = (1.0 - r_tau) / L
    mtbf_eff = np.where(lam > 0, 1.0 / np.maximum(lam, 1e-300), np.inf)
    a_op = np.where(np.isfinite(mtbf_eff), mtbf_eff / (mtbf_eff + e.mdt), 1.0)

    mttf = eta * float(gamma_fn(1.0 + 1.0 / beta))
    return KurvaPeralatan(
        tag=e.tag, beta=beta, eta=eta, mdt=float(e.mdt), cp=cp, cf=cf,
        tau_hours=tau, r_tau=r_tau, cost_rate=cost, lambda_eff=lam, a_op=a_op,
        cost_rtf=cf / mttf, mttf=mttf,
    )


def tau_untuk_target_keandalan(beta: float, eta: float, r_target: float) -> float:
    """Interval yang menghasilkan R(tau) tepat sama dengan `r_target`.

    Dibalik secara analitik dari R(tau) = exp(-(tau/eta)^beta):
        tau_R = eta * (-ln R_target)^(1/beta)
    Ref: Ebeling, An Introduction to Reliability and Maintainability Engineering
    (pemilihan interval preventif berdasarkan tingkat keandalan minimum).
    """
    if not (0.0 < r_target < 1.0) or beta <= 0 or not np.isfinite(eta) or eta <= 0:
        return float("nan")
    return float(eta * (-math.log(r_target)) ** (1.0 / beta))


# ==========================================================================
# 2. Grid interval
# ==========================================================================
def _grid_matlab(etas: Sequence[float], pengali: float) -> np.ndarray:
    """Grid LINEAR 0,05 eta sampai `pengali` kali eta, seperti modul G MATLAB.

    Dipakai untuk kurva pada halaman interval pemeliharaan supaya tau* yang
    ditandai pada grafik sama dengan tabel modul G yang sudah tervalidasi
    terhadap laporan (255, 198, dan 211 hari).
    """
    finite = [e for e in etas if np.isfinite(e) and e > 0]
    if not finite:
        return np.linspace(24.0, 8760.0, N_GRID)
    lo = max(min(finite) * 0.05, 12.0)
    hi = max(max(finite) * float(pengali), lo * 4.0)
    return np.linspace(lo, hi, N_GRID)


def _grid_pencarian(etas: Sequence[float], pengali: float) -> np.ndarray:
    """Grid LOGARITMIK yang cukup lebar untuk memuat titik minimum sesungguhnya.

    Dipakai oleh alat pencari titik optimal. Grid linear 0,05 eta sampai 3 eta
    warisan MATLAB memadai ketika rasio Cf/Cp sekitar 10, tetapi tidak lagi
    memadai ketika biaya nyata dari SAP menghasilkan rasio yang jauh lebih
    besar: minimum bergeser ke interval yang sangat pendek dan terpotong batas
    bawah grid. Karena C(tau) menuju tak hingga saat tau menuju nol (penyebut
    L(tau) menuju tau sedangkan pembilang menuju Cp), minimum interior selalu
    ada untuk Cf > Cp, sehingga grid harus dibuat cukup lebar agar minimum itu
    benar-benar terjaring.

    Rentang 0,002 eta sampai `pengali` kali eta mencakup lebih dari tiga dekade.
    Penjarakan logaritmik dipilih karena daerah yang menarik dapat berada di
    ujung mana pun, dan karena kurva biaya memang wajar dibaca pada skala log.
    """
    finite = [e for e in etas if np.isfinite(e) and e > 0]
    if not finite:
        return np.geomspace(6.0, 8760.0, N_GRID)
    lo = max(min(finite) * 0.002, 2.0)          # minimal dua jam
    hi = max(max(finite) * float(pengali), lo * 100.0)
    return np.geomspace(lo, hi, N_GRID)


# ==========================================================================
# 3. Titik optimal dan rekomendasi
# ==========================================================================
@dataclass
class TitikOptimal:
    tau_hari: float
    biaya_tahunan: float
    r_pada_tau: float
    a_op: float
    gagal_per_thn: float
    downtime_hari_thn: float
    di_batas_grid: bool


@dataclass
class HasilInterval:
    lingkup: str                       # 'equipment' | 'fs'
    label: str
    n_peralatan: int
    kurva: Dict[str, Any]
    optimal_biaya: TitikOptimal
    optimal_keandalan: Optional[TitikOptimal]
    garis_dasar: Dict[str, Any]
    rekomendasi: Dict[str, Any]
    parameter: Dict[str, Any]
    peralatan: List[Dict[str, Any]] = field(default_factory=list)
    referensi: List[str] = field(default_factory=list)


def _titik(
    idx: int,
    tau_h: np.ndarray,
    cost: np.ndarray,
    r: np.ndarray,
    a_op: np.ndarray,
    lam: np.ndarray,
) -> TitikOptimal:
    return TitikOptimal(
        tau_hari=float(tau_h[idx] / 24.0),
        biaya_tahunan=float(cost[idx] * 8760.0),
        r_pada_tau=float(r[idx]),
        a_op=float(a_op[idx]),
        gagal_per_thn=float(lam[idx] * 8760.0),
        downtime_hari_thn=float((1.0 - a_op[idx]) * 365.0),
        di_batas_grid=bool(idx == 0 or idx == len(tau_h) - 1),
    )


REFERENSI = [
    "Barlow, R.E. & Hunter, L.C. (1960), Optimum Preventive Maintenance Policies, "
    "Operations Research 8(1), 90-100: model biaya age replacement C(tau).",
    "Barlow, R.E. & Proschan, F., Mathematical Theory of Reliability: teorema "
    "pembaharuan untuk laju kegagalan efektif dan kebijakan block replacement.",
    "Jardine, A.K.S. & Tsang, A.H.C., Maintenance, Replacement, and Reliability: "
    "pembacaan kurva laju biaya terhadap interval dan penentuan tau optimal.",
    "Rausand, M. & Hoyland, A., System Reliability Theory: R(t) Weibull dan "
    "penggabungan keandalan seri-paralel pada RBD.",
    "Ebeling, C.E., An Introduction to Reliability and Maintainability "
    "Engineering: penentuan interval preventif dari tingkat keandalan minimum.",
    "ISO 14224:2016: definisi MDT dan ketersediaan operasional.",
    "SAE JA1011 / JA1012: logika pemilihan tugas pemeliharaan berbasis "
    "konsekuensi dan ambang kegagalan yang dapat diterima.",
    "Dekker, R. (1996), Applications of maintenance optimisation models, "
    "Reliability Engineering & System Safety 51(3): tinjauan kebijakan "
    "pengelompokan interval pada tingkat sistem.",
]


def _rekomendasi(
    lingkup: str,
    label: str,
    beta_wakil: float,
    opt_biaya: TitikOptimal,
    opt_keandalan: Optional[TitikOptimal],
    dasar: Dict[str, Any],
    r_target: float,
    cfg: Config,
    sumber_biaya: str,
    *,
    r_maksimum: Optional[float] = None,
    aop_naik_dengan_tau: bool = False,
    rasio_cf_cp: Optional[float] = None,
) -> Dict[str, Any]:
    """Susun keputusan interval beserta alasan bernalar.

    URUTAN PENALARAN mengikuti SAE JA1011/JA1012: uji KELAYAKAN tugas lebih
    dahulu, baru optimasi. Menukar urutan ini menghasilkan rekomendasi yang
    tampak canggih tetapi salah secara teknis.

      Langkah 1. Apakah penggantian terjadwal BERLAKU untuk pola kegagalan ini?
        beta < beta_dfr   pola kegagalan dini. Penggantian mengembalikan
                          komponen ke daerah kegagalan dini, sehingga menaikkan
                          laju kegagalan. Tugas TIDAK berlaku.
        beta di sekitar 1 laju kegagalan konstan. Komponen baru secara statistik
                          identik dengan komponen terpakai, sehingga penggantian
                          tidak mengubah laju kegagalan sedikit pun. Tugas TIDAK
                          berlaku. Ini juga sebabnya optimum Barlow-Hunter untuk
                          beta <= 1 berada di tak hingga.
        beta >= beta_wear ada umur aus yang dapat dikenali. Tugas BERLAKU.

      Langkah 2. Bila berlaku, periksa apakah manfaat ekonominya cukup besar.

      Langkah 3. Bandingkan interval ekonomis tau* dengan interval target
        keandalan tau_R, lalu ambil yang lebih pendek.

    Untuk lingkup SISTEM, target keandalan hanya bersifat INFORMASI, bukan
    pengikat keputusan. R sistem pada interval bersama adalah peluang seluruh
    peralatan lolos tanpa SATU PUN kegagalan; pada sistem dengan banyak
    komponen seri, menuntut nilai itu tinggi memaksa interval menjadi sangat
    pendek dan justru MENURUNKAN ketersediaan karena unit terlalu sering
    dihentikan. Untuk horizon panjang, indikator yang tepat adalah ketersediaan
    dan ekspektasi jumlah kegagalan, bukan keandalan (lihat catatan modul E dan
    Rausand & Hoyland mengenai pemilihan ukuran kinerja).
    """
    alasan: List[str] = []
    wilayah = ifr_region(beta_wakil)
    hemat = dasar.get("penghematan_pct", 0.0)

    aus = beta_wakil >= cfg.beta_wear
    dini = beta_wakil < cfg.beta_dfr

    # ---- 1. bukti mekanisme kegagalan --------------------------------------
    if dini:
        alasan.append(
            f"Parameter bentuk beta {beta_wakil:.2f} berada di bawah {cfg.beta_dfr:.2f}, "
            f"yang menandakan pola kegagalan dini ({wilayah}). Laju kegagalan justru "
            "menurun seiring umur, sehingga mengganti komponen yang masih laik pakai "
            "akan mengembalikannya ke daerah kegagalan dini dan memperburuk keandalan."
        )
    elif not aus:
        alasan.append(
            f"Parameter bentuk beta {beta_wakil:.2f} berada di sekitar satu ({wilayah}), "
            "artinya kegagalan bersifat acak dan tidak bergantung pada umur. Pada kondisi "
            "ini penggantian berkala tidak menurunkan laju kegagalan karena komponen baru "
            "memiliki peluang gagal yang sama dengan komponen yang dipakai."
        )
    else:
        alasan.append(
            f"Parameter bentuk beta {beta_wakil:.2f} berada di atas {cfg.beta_wear:.2f} "
            f"({wilayah}), yang membuktikan adanya mekanisme aus. Laju kegagalan meningkat "
            "seiring umur, sehingga penggantian sebelum aus mencapai batas memang menekan "
            "jumlah kegagalan."
        )

    # Konsekuensi arah kurva ketersediaan. Untuk beta < 1 laju kegagalan efektif
    # justru MENURUN ketika interval diperpanjang, sehingga penggantian berkala
    # menurunkan ketersediaan. Ini bukti kuantitatif paling langsung bahwa
    # menjadwalkan penggantian pada pola kegagalan dini merugikan.
    if aop_naik_dengan_tau:
        alasan.append(
            "Kurva ketersediaan pada grafik NAIK ketika interval diperpanjang. Artinya "
            "menjadwalkan penggantian justru menurunkan ketersediaan, karena komponen yang "
            "sudah melewati masa kegagalan dini digantikan komponen baru yang laju "
            "kegagalannya lebih tinggi. Pada kondisi seperti ini jadwal penggantian merugikan "
            "dua kali: menambah biaya sekaligus menurunkan ketersediaan."
        )

    # ---- 2. bentuk kurva biaya --------------------------------------------
    if opt_biaya.di_batas_grid:
        alasan.append(
            "Kurva laju biaya tidak memiliki titik minimum di dalam rentang interval yang "
            "ditinjau; biaya masih menurun sampai ujung rentang. Secara ekonomi berarti "
            "menunda penggantian selalu lebih murah, sehingga run to failure terkendali "
            "lebih hemat daripada jadwal apa pun."
        )
    elif hemat < cfg.pm_min_saving:
        alasan.append(
            f"Titik minimum kurva biaya ada, tetapi penghematannya hanya {hemat:.1f} persen "
            f"terhadap run to failure, di bawah ambang manfaat {cfg.pm_min_saving:.0f} persen. "
            "Kurva yang hampir datar berarti setiap pilihan interval menghasilkan biaya yang "
            "hampir sama, sehingga penjadwalan tidak memberi nilai tambah."
        )
    else:
        alasan.append(
            f"Kurva laju biaya memiliki lekukan yang jelas dengan minimum pada "
            f"{opt_biaya.tau_hari:.0f} hari dan penghematan {hemat:.1f} persen terhadap "
            "run to failure, sehingga pemilihan interval benar benar berpengaruh."
        )

    # ---- 3. keputusan: kelayakan tugas lebih dahulu, baru optimasi ---------
    keputusan_tau: Optional[float]
    dasar_keputusan: str
    tau_r = (
        opt_keandalan.tau_hari
        if opt_keandalan is not None and np.isfinite(opt_keandalan.tau_hari)
        else None
    )
    ada_manfaat_ekonomi = (not opt_biaya.di_batas_grid) and hemat >= cfg.pm_min_saving

    # Pada lingkup SISTEM, target keandalan tidak boleh mengikat keputusan.
    # R sistem pada interval bersama adalah peluang SELURUH peralatan lolos
    # tanpa satu pun kegagalan; menuntutnya tinggi memaksa interval sangat
    # pendek dan justru menurunkan ketersediaan karena unit terlalu sering
    # dihentikan. Nilainya tetap ditampilkan sebagai informasi.
    tau_r_mengikat = tau_r if lingkup == "equipment" else None
    if lingkup == "fs" and tau_r is not None:
        alasan.append(
            f"Pada interval {tau_r:.0f} hari keandalan sistem memang mencapai {r_target:.2f}, "
            "tetapi angka ini hanya informasi dan TIDAK dipakai sebagai jadwal. Keandalan sistem "
            "pada interval bersama adalah peluang seluruh peralatan lolos tanpa satu pun "
            "kegagalan, sehingga untuk sistem dengan banyak komponen seri nilainya hanya bisa "
            "tinggi bila interval dibuat sangat pendek. Akibatnya unit terlalu sering dihentikan "
            "dan ketersediaan justru turun. Untuk horizon panjang, ukuran yang tepat adalah "
            "ketersediaan operasional dan ekspektasi jumlah kegagalan, bukan keandalan."
        )

    # Target keandalan yang tidak terjangkau tetap dilaporkan sebagai temuan.
    if tau_r is None and r_maksimum is not None:
        alasan.append(
            f"Target keandalan {r_target:.2f} TIDAK dapat dicapai pada interval mana pun. "
            f"Keandalan tertinggi yang mungkin diperoleh hanya {r_maksimum:.4f}, yaitu pada "
            "interval terpendek yang ditinjau. Penyebabnya bukan pemilihan interval, melainkan "
            "banyaknya peralatan yang tersusun seri sehingga keandalan gabungan adalah hasil "
            "kali seluruh komponennya. Perbaikan hanya mungkin melalui penambahan redundansi, "
            "pengurangan titik lemah seri, atau perbaikan keandalan komponen, bukan melalui "
            "percepatan jadwal."
        )

    if not aus:
        # LANGKAH 1 GAGAL: tugas penggantian terjadwal tidak berlaku. Ini
        # keputusan yang mengikat dan tidak boleh ditimpa oleh target keandalan,
        # karena penggantian tidak mengubah laju kegagalan pada pola dini
        # maupun acak (SAE JA1011: tugas restorasi hanya berlaku bila ada umur
        # aus yang dapat dikenali).
        keputusan_tau = None
        dasar_keputusan = "tidak berlaku"
        if tau_r is not None:
            alasan.append(
                f"Grafik memang menunjukkan bahwa keandalan {r_target:.2f} tercapai pada interval "
                f"{tau_r:.0f} hari, tetapi angka itu TIDAK boleh dijadikan jadwal penggantian. "
                "Pada pola kegagalan ini penggantian tidak menurunkan laju kegagalan, sehingga "
                f"memaksakan interval {tau_r:.0f} hari hanya menaikkan biaya menjadi sekitar "
                f"{opt_keandalan.biaya_tahunan:,.0f} per tahun, dari "
                f"{dasar['biaya_tahunan']:,.0f} pada run to failure, tanpa perbaikan yang setara. "
                "Nilai tau tersebut berguna sebagai interval INSPEKSI atau ambang pemantauan "
                "kondisi, bukan sebagai interval penggantian."
            )
    elif not ada_manfaat_ekonomi:
        # Aus terbukti, tetapi manfaat ekonominya tidak cukup.
        keputusan_tau = tau_r_mengikat
        dasar_keputusan = "keandalan" if keputusan_tau is not None else "tanpa jadwal"
        if keputusan_tau is not None:
            alasan.append(
                f"Mekanisme aus terbukti, tetapi tidak ada minimum biaya yang bermakna di dalam "
                f"rentang. Karena itu interval ditentukan oleh persyaratan keandalan, yaitu "
                f"{tau_r:.0f} hari agar keandalan saat penggantian tidak turun di bawah "
                f"{r_target:.2f}."
            )
    elif tau_r_mengikat is None or opt_biaya.tau_hari <= tau_r_mengikat:
        keputusan_tau = opt_biaya.tau_hari
        dasar_keputusan = "biaya"
        if tau_r is not None:
            alasan.append(
                f"Interval ekonomis {opt_biaya.tau_hari:.0f} hari sudah lebih pendek daripada "
                f"interval target keandalan {tau_r:.0f} hari, sehingga keduanya sejalan. Memilih "
                f"titik biaya minimum otomatis memenuhi target {r_target:.2f} dengan keandalan "
                f"sebenarnya {opt_biaya.r_pada_tau:.3f}."
            )
    else:
        keputusan_tau = tau_r_mengikat
        dasar_keputusan = "keandalan"
        selisih = opt_keandalan.biaya_tahunan - opt_biaya.biaya_tahunan
        alasan.append(
            f"Interval ekonomis {opt_biaya.tau_hari:.0f} hari hanya menyisakan keandalan "
            f"{opt_biaya.r_pada_tau:.3f}, di bawah target {r_target:.2f}. Keandalan adalah "
            "batasan, bukan besaran yang boleh ditukar dengan biaya, sehingga interval "
            f"dipendekkan menjadi {tau_r:.0f} hari dengan tambahan biaya sekitar "
            f"{abs(selisih):,.0f} per tahun."
        )

    # Peringatan rasio biaya yang bersandar pada sedikit order.
    if rasio_cf_cp is not None and rasio_cf_cp > 50 and keputusan_tau is not None:
        alasan.append(
            f"Rasio biaya Cf berbanding Cp mencapai {rasio_cf_cp:.0f}, jauh di atas rasio yang "
            "lazim. Rasio setinggi itu mendorong interval menjadi sangat pendek, sehingga "
            "sebaiknya biaya aktual pada order SAP ditinjau ulang sebelum angka interval ini "
            "dipakai sebagai dasar keputusan."
        )

    # ---- 4. konsekuensi angka --------------------------------------------
    dipakai = opt_keandalan if dasar_keputusan == "keandalan" and opt_keandalan else opt_biaya
    if keputusan_tau is None:
        if dasar_keputusan == "tidak berlaku":
            tindakan = (
                "Jangan menjadwalkan penggantian berkala karena tugas tersebut tidak berlaku pada "
                "pola kegagalan ini. Alihkan sumber daya ke pemantauan kondisi untuk menangkap "
                "gejala sebelum kegagalan, dan ke penelusuran akar masalah untuk pola kegagalan "
                "dini. Pastikan suku cadang tersedia agar perbaikan korektif tetap terencana."
            )
            ringkas = "Tanpa jadwal penggantian, tugas tidak berlaku"
        else:
            tindakan = (
                "Jangan menjadwalkan penggantian berkala karena manfaatnya tidak sebanding. "
                "Pilih pemantauan kondisi atau inspeksi berkala, dan tinjau ulang bila tren laju "
                "kegagalan berubah."
            )
            ringkas = "Tanpa jadwal penggantian"
    else:
        tindakan = (
            f"Jadwalkan penggantian atau restorasi setiap {keputusan_tau:.0f} hari. Pada interval "
            f"tersebut keandalan saat penggantian {dipakai.r_pada_tau:.3f}, ekspektasi kegagalan "
            f"{dipakai.gagal_per_thn:.2f} kejadian per tahun, ketersediaan operasional "
            f"{dipakai.a_op:.4f}, dan waktu henti sekitar {dipakai.downtime_hari_thn:.1f} hari per tahun."
        )
        ringkas = f"Interval {keputusan_tau:.0f} hari"

    catatan_biaya = (
        "Cp dan Cf memakai biaya aktual dari berkas order SAP."
        if sumber_biaya.startswith("order")
        else f"Cp dan Cf memakai rasio bawaan {cfg.cp:g} berbanding {cfg.cf:g} karena berkas order "
        "belum tersedia, sehingga nilai biaya bersifat relatif dan hanya bentuk kurvanya yang bermakna."
    )
    alasan.append(catatan_biaya)

    if lingkup == "fs":
        alasan.append(
            "Pada tingkat Functional System, satu interval yang sama diterapkan pada seluruh "
            "peralatan di dalamnya (kebijakan block replacement). Ini mencerminkan praktik "
            "nyata di kilang, yaitu satu jendela berhenti dipakai bersama oleh seluruh "
            "peralatan dalam sistem tersebut."
        )

    return {
        "ringkas": ringkas,
        "dasar_keputusan": dasar_keputusan,
        "interval_dianjurkan_hari": keputusan_tau,
        "alasan": alasan,
        "tindakan": tindakan,
        "target_keandalan": r_target,
        "wilayah_laju_kegagalan": wilayah,
    }


# ==========================================================================
# 4. Analisis satu peralatan
# ==========================================================================
def _biaya_tag(
    tag: str, cfg: Config, cost_by_tag: Optional[Mapping[str, Dict[str, float]]]
) -> Tuple[float, float, str]:
    if cost_by_tag and tag in cost_by_tag:
        c = cost_by_tag[tag]
        if c.get("cp", 0) > 0 and c.get("cf", 0) > 0:
            return float(c["cp"]), float(c["cf"]), "order"
    return float(cfg.cp), float(cfg.cf), "default"


def analisis_peralatan(
    eq: Mapping[str, EquipmentParams],
    tag: str,
    cfg: Config,
    *,
    r_target: float = 0.90,
    pengali_rentang: float = 3.0,
    cost_by_tag: Optional[Mapping[str, Dict[str, float]]] = None,
) -> HasilInterval:
    """Kurva biaya dan keandalan terhadap waktu untuk satu tag peralatan."""
    e = eq.get(tag)
    if e is None:
        raise ValueError(f"Tag '{tag}' tidak ada pada dataset ini.")
    if e.never_failed:
        raise ValueError(
            f"Tag '{tag}' tidak memiliki kegagalan korektif pada jendela pengamatan, "
            "sehingga parameter Weibull dan biaya kegagalannya tidak dapat diperkirakan. "
            "Pilih peralatan yang memiliki riwayat kegagalan."
        )

    cp, cf, sumber = _biaya_tag(tag, cfg, cost_by_tag)
    tau = _grid_pencarian([e.eta], pengali_rentang)
    k = kurva_peralatan(e, tau, cp, cf)

    idx_min = int(np.argmin(k.cost_rate))
    opt_biaya = _titik(idx_min, tau, k.cost_rate, k.r_tau, k.a_op, k.lambda_eff)

    tau_r = tau_untuk_target_keandalan(k.beta, k.eta, r_target)
    opt_rel: Optional[TitikOptimal] = None
    if np.isfinite(tau_r):
        j = int(np.argmin(np.abs(tau - tau_r)))
        opt_rel = _titik(j, tau, k.cost_rate, k.r_tau, k.a_op, k.lambda_eff)
        opt_rel.tau_hari = tau_r / 24.0     # pakai nilai analitik yang tepat

    biaya_rtf_thn = k.cost_rtf * 8760.0
    hemat = (1.0 - opt_biaya.biaya_tahunan / biaya_rtf_thn) * 100.0 if biaya_rtf_thn > 0 else 0.0
    dasar = {
        "kebijakan": "Run to failure",
        "biaya_tahunan": float(biaya_rtf_thn),
        "mttf_hari": float(k.mttf / 24.0),
        "a_op": float(e.a_op),
        "gagal_per_thn": float(8760.0 / e.mtbf) if np.isfinite(e.mtbf) else None,
        "penghematan_pct": float(hemat),
    }

    return HasilInterval(
        lingkup="equipment",
        label=tag,
        n_peralatan=1,
        kurva={
            "tau_hari": (tau / 24.0).tolist(),
            "biaya_tahunan": (k.cost_rate * 8760.0).tolist(),
            "keandalan": k.r_tau.tolist(),
            "a_op": k.a_op.tolist(),
            "gagal_per_thn": (k.lambda_eff * 8760.0).tolist(),
        },
        optimal_biaya=opt_biaya,
        optimal_keandalan=opt_rel,
        garis_dasar=dasar,
        rekomendasi=_rekomendasi(
            "equipment", tag, k.beta, opt_biaya, opt_rel, dasar, r_target, cfg, sumber,
            r_maksimum=float(k.r_tau[0]) if opt_rel is None else None,
            aop_naik_dengan_tau=bool(k.a_op[-1] > k.a_op[0] + 1e-9),
            rasio_cf_cp=cf / cp if cp > 0 else None,
        ),
        parameter={
            "beta": k.beta, "eta_jam": k.eta, "mdt_jam": k.mdt,
            "cp": cp, "cf": cf, "sumber_biaya": sumber,
            "rasio_cf_cp": cf / cp if cp > 0 else None,
            "pengali_rentang": pengali_rentang,
            "tau_min_hari": float(tau[0] / 24.0),
            "tau_max_hari": float(tau[-1] / 24.0),
        },
        peralatan=[
            {
                "tag": tag, "kelas": e.kelas, "beta": k.beta, "eta_jam": k.eta,
                "mdt_jam": k.mdt, "n_cm": e.n_cm,
                "mtbf_hari": float(e.mtbf / 24.0) if np.isfinite(e.mtbf) else None,
                "cp": cp, "cf": cf, "sumber_biaya": sumber,
            }
        ],
        referensi=REFERENSI,
    )


# ==========================================================================
# 5. Analisis satu Functional System (interval bersama)
# ==========================================================================
def analisis_fs(
    eq: Mapping[str, EquipmentParams],
    fs: int,
    cfg: Config,
    *,
    r_target: float = 0.90,
    pengali_rentang: float = 3.0,
    cost_by_tag: Optional[Mapping[str, Dict[str, float]]] = None,
) -> HasilInterval:
    """Kurva biaya dan keandalan sistem untuk satu interval bersama.

    Biaya sistem adalah jumlah laju biaya tiap peralatan pada interval yang sama.
    Keandalan sistem digabung mengikuti struktur RBD: stage seri memakai
    perkalian, stage paralel memakai 1 - prod(1 - Ri). Ketersediaan sistem juga
    digabung dengan cara yang sama memakai A_op efektif tiap peralatan.
    """
    stages = stages_of_fs(fs)
    if not stages:
        raise ValueError(f"Functional System {fs} tidak dikenal.")

    # Peralatan pada jalur RBD FS ini yang punya riwayat kegagalan.
    aktif = [t for st in stages for t in st.tags if t in eq and not eq[t].never_failed]
    if not aktif:
        raise ValueError(
            f"Tidak ada peralatan pada {fs_name(fs)} yang memiliki riwayat kegagalan, "
            "sehingga interval bersama tidak dapat dianalisis."
        )

    tau = _grid_pencarian([eq[t].eta for t in aktif], pengali_rentang)

    kurva_per_tag: Dict[str, KurvaPeralatan] = {}
    biaya_total = np.zeros_like(tau)
    rincian: List[Dict[str, Any]] = []
    for t in aktif:
        cp, cf, sumber = _biaya_tag(t, cfg, cost_by_tag)
        k = kurva_peralatan(eq[t], tau, cp, cf)
        kurva_per_tag[t] = k
        biaya_total += k.cost_rate
        rincian.append(
            {
                "tag": t, "kelas": eq[t].kelas, "beta": k.beta, "eta_jam": k.eta,
                "mdt_jam": k.mdt, "n_cm": eq[t].n_cm,
                "mtbf_hari": float(eq[t].mtbf / 24.0) if np.isfinite(eq[t].mtbf) else None,
                "cp": cp, "cf": cf, "sumber_biaya": sumber,
            }
        )

    # Peralatan jalur RBD yang tidak pernah gagal tetap ikut sebagai R = 1, A = 1.
    def _r_stage(st, i: int) -> float:
        if not st.tags:
            return 1.0
        nilai = [kurva_per_tag[t].r_tau[i] if t in kurva_per_tag else 1.0 for t in st.tags]
        if st.typ == "ser":
            return float(np.prod(nilai))
        return float(1.0 - np.prod([1.0 - v for v in nilai]))

    def _a_stage(st, i: int) -> float:
        if not st.tags:
            return 1.0
        nilai = [kurva_per_tag[t].a_op[i] if t in kurva_per_tag else 1.0 for t in st.tags]
        if st.typ == "ser":
            return float(np.prod(nilai))
        return float(1.0 - np.prod([1.0 - v for v in nilai]))

    n = tau.size
    r_sys = np.ones(n)
    a_sys = np.ones(n)
    for i in range(n):
        rr, aa = 1.0, 1.0
        for st in stages:
            rr *= _r_stage(st, i)
            aa *= _a_stage(st, i)
        r_sys[i] = rr
        a_sys[i] = aa

    # Ekspektasi kegagalan sistem per tahun: jumlah laju efektif seluruh peralatan
    # (peralatan seri maupun paralel sama sama menimbulkan pekerjaan korektif).
    lam_sys = np.zeros(n)
    for k in kurva_per_tag.values():
        lam_sys += k.lambda_eff

    idx_min = int(np.argmin(biaya_total))
    opt_biaya = _titik(idx_min, tau, biaya_total, r_sys, a_sys, lam_sys)

    # Interval target keandalan pada tingkat sistem dicari pada grid karena
    # penggabungan seri-paralel tidak dapat dibalik secara analitik.
    opt_rel: Optional[TitikOptimal] = None
    layak = np.flatnonzero(r_sys >= r_target)
    if layak.size:
        j = int(layak[-1])       # interval terpanjang yang masih memenuhi target
        opt_rel = _titik(j, tau, biaya_total, r_sys, a_sys, lam_sys)

    biaya_rtf_thn = float(sum(k.cost_rtf for k in kurva_per_tag.values()) * 8760.0)
    hemat = (1.0 - opt_biaya.biaya_tahunan / biaya_rtf_thn) * 100.0 if biaya_rtf_thn > 0 else 0.0

    # Beta wakil sistem: rata rata berbobot waktu henti tahunan, karena peralatan
    # yang paling menentukan perilaku sistem adalah penyumbang downtime terbesar.
    bobot = np.array([8760.0 / eq[t].mtbf * eq[t].mdt for t in aktif], dtype=float)
    betas = np.array([kurva_per_tag[t].beta for t in aktif], dtype=float)
    beta_wakil = float(np.average(betas, weights=bobot)) if bobot.sum() > 0 else float(betas.mean())

    dasar = {
        "kebijakan": "Run to failure",
        "biaya_tahunan": biaya_rtf_thn,
        "a_op": float(np.prod([_a_stage(st, n - 1) for st in stages])),
        "gagal_per_thn": float(sum(8760.0 / eq[t].mtbf for t in aktif)),
        "penghematan_pct": float(hemat),
    }

    return HasilInterval(
        lingkup="fs",
        label=fs_name(fs),
        n_peralatan=len(aktif),
        kurva={
            "tau_hari": (tau / 24.0).tolist(),
            "biaya_tahunan": (biaya_total * 8760.0).tolist(),
            "keandalan": r_sys.tolist(),
            "a_op": a_sys.tolist(),
            "gagal_per_thn": (lam_sys * 8760.0).tolist(),
        },
        optimal_biaya=opt_biaya,
        optimal_keandalan=opt_rel,
        garis_dasar=dasar,
        rekomendasi=_rekomendasi(
            "fs", fs_name(fs), beta_wakil, opt_biaya, opt_rel, dasar, r_target, cfg,
            "order" if any(r["sumber_biaya"] == "order" for r in rincian) else "default",
            r_maksimum=float(r_sys[0]) if opt_rel is None else None,
            aop_naik_dengan_tau=bool(a_sys[-1] > a_sys[0] + 1e-9),
        ),
        parameter={
            "beta_wakil": beta_wakil,
            "pengali_rentang": pengali_rentang,
            "tau_min_hari": float(tau[0] / 24.0),
            "tau_max_hari": float(tau[-1] / 24.0),
            "kebijakan": "block replacement dengan interval bersama",
            "n_stage": len(stages),
        },
        peralatan=rincian,
        referensi=REFERENSI,
    )


# ==========================================================================
# 6. Kurva banyak peralatan sekaligus (untuk halaman interval pemeliharaan)
# ==========================================================================
def kurva_banyak_peralatan(
    eq: Mapping[str, EquipmentParams],
    tags: Sequence[str],
    cfg: Config,
    *,
    pengali_rentang: float = 3.0,
    cost_by_tag: Optional[Mapping[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Kurva laju biaya terhadap interval untuk beberapa tag yang dipilih pengguna.

    Setiap tag memakai grid intervalnya sendiri (0,05 eta sampai pengali kali
    eta) supaya bentuk kurvanya terbaca jelas, sama seperti modul G.
    """
    hasil: List[Dict[str, Any]] = []
    dilewati: List[Dict[str, str]] = []

    for tag in tags:
        e = eq.get(tag)
        if e is None:
            dilewati.append({"tag": tag, "alasan": "tidak ada pada dataset ini"})
            continue
        if e.never_failed:
            dilewati.append(
                {"tag": tag, "alasan": "tidak ada kegagalan korektif pada jendela pengamatan"}
            )
            continue

        cp, cf, sumber = _biaya_tag(tag, cfg, cost_by_tag)
        tau = _grid_matlab([e.eta], pengali_rentang)
        k = kurva_peralatan(e, tau, cp, cf)
        idx = int(np.argmin(k.cost_rate))
        biaya_rtf = k.cost_rtf
        hemat = (1.0 - k.cost_rate[idx] / biaya_rtf) * 100.0 if biaya_rtf > 0 else 0.0

        hasil.append(
            {
                "tag": tag,
                "kelas": e.kelas,
                "n_cm": e.n_cm,
                "beta": k.beta,
                "eta_jam": k.eta,
                "mdt_jam": k.mdt,
                "mtbf_hari": float(e.mtbf / 24.0) if np.isfinite(e.mtbf) else None,
                "wilayah": ifr_region(k.beta),
                "cp": cp,
                "cf": cf,
                "sumber_biaya": sumber,
                "tau_hari": (tau / 24.0).tolist(),
                "biaya_tahunan": (k.cost_rate * 8760.0).tolist(),
                "keandalan": k.r_tau.tolist(),
                "tau_opt_hari": float(tau[idx] / 24.0),
                "biaya_opt_tahunan": float(k.cost_rate[idx] * 8760.0),
                "biaya_rtf_tahunan": float(biaya_rtf * 8760.0),
                "r_pada_tau_opt": float(k.r_tau[idx]),
                "penghematan_pct": float(hemat),
                "penghematan_efektif_pct": float(max(0.0, hemat)),
                "optimum_di_batas": bool(idx == 0 or idx == tau.size - 1),
                "verdict": (
                    "PM berkala efektif" if k.beta > 1.1 else "beta sekitar satu, PM berkala kurang berguna"
                ),
            }
        )

    return {
        "kurva": hasil,
        "dilewati": dilewati,
        "catatan": (
            "Sumbu mendatar adalah pilihan interval penggantian, sumbu tegak adalah laju biaya "
            "tahunan menurut model age replacement Barlow dan Hunter (1960). Titik menandai "
            "biaya terendah. Kurva yang hampir datar berarti pemilihan interval tidak "
            "berpengaruh, sedangkan lekukan yang dalam berarti interval sangat menentukan."
        ),
        "referensi": REFERENSI[:3],
    }
