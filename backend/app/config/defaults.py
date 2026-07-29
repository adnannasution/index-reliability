"""
Parameter default aplikasi: port lengkap dari `configDefaults()` pada
CDU_PdM_Balongan.m (v3.0).

Setiap nilai di sini adalah *parameter metode*, bukan data. Semua daftar tag,
jumlah baris, kelas, dan rentang tanggal DITURUNKAN dari file Excel yang
di-upload (lihat core/data_loader.py): tidak ada yang di-hard-code di sini.

Referensi umum:
  - ISO 14224:2016: taksonomi, MTBF/MTTR/MDT, availability, kekritisan.
  - OREDA: nilai MTTR acuan per kelas peralatan.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

BetaSource = Literal["equipment", "mle", "workbook"]
WindowEnd = Literal["cutoff", "lastevent"]
WeibullEstimator = Literal["mrr", "mle", "crow", "class"]


# --------------------------------------------------------------------------
# MTTR inheren per kelas peralatan (jam): sumber OREDA (cfg.mttr di MATLAB).
# Dipakai untuk ketersediaan INHEREN: A_inh = MTBF / (MTBF + MTTR).
# Ref: ISO 14224:2016 §3; Blanchard & Fabrycky, Systems Engineering & Analysis.
# --------------------------------------------------------------------------
MTTR_BY_CLASS: Dict[str, float] = {
    "heater": 72.0,
    "vessel": 24.0,
    "exchanger": 24.0,
    "pump": 12.0,
    "column": 48.0,
    "injection": 8.0,
    "other": 24.0,
}

#: MDT dipakai bila tag tidak ada di tabel MDT (cfg.mdtDefault).
MDT_DEFAULT: float = 48.0

#: Kelas peralatan yang dianalisis (cfg.classes). `other` sengaja di luar daftar
#: ini: sama seperti MATLAB: tetapi tetap punya MTTR untuk fallback.
CLASSES: List[str] = ["heater", "vessel", "exchanger", "pump", "column", "injection"]

#: Bobot kekritisan SAP (cfg.critW). Huruf pertama kolom `Criticality`.
CRIT_WEIGHT: Dict[str, float] = {
    "H": 1.00,
    "M": 0.70,
    "L": 0.45,
    "I": 0.60,
    "Z": 0.35,
    "default": 0.60,
}


class Config(BaseModel):
    """Seluruh parameter metode; dapat diubah dari UI (§4.9)."""

    # ---- Pembacaan data -------------------------------------------------
    unit: str = Field(
        default="11-",
        description="Prefix Functional Loc. untuk unit yang dianalisis (Unit 11 = CDU).",
    )
    fail_types: List[str] = Field(
        default=["M1", "M2"],
        description="Jenis notifikasi yang dihitung sebagai kegagalan korektif.",
    )
    pm_type: str = Field(default="M3", description="Jenis notifikasi preventif.")
    window_end: WindowEnd = Field(
        default="cutoff",
        description=(
            "Akhir jendela pengamatan. 'cutoff' = tanggal ekspor SAP (tanggal "
            "terakhir di SELURUH file) -> T_obs 17.064 j, identik laporan. "
            "'lastevent' = notifikasi Unit-11 terakhir -> T_obs 16.992 j."
        ),
    )

    # ---- Weibull / estimator --------------------------------------------
    beta_source: BetaSource = Field(
        default="equipment",
        description=(
            "Sumber beta untuk RBD. 'equipment' = beta per-tag (modul C3, "
            "DIREKOMENDASIKAN); 'mle' = beta MLE per kelas (modul C); "
            "'workbook' = konstanta per kelas agar identik laporan lama."
        ),
    )
    beta_kmin: int = Field(
        default=3,
        ge=1,
        description="Minimum jumlah kegagalan agar tag memakai shape sendiri (cfg.betaKmin).",
    )
    cred_m0: float = Field(
        default=3.0,
        gt=0,
        description="Kekuatan prior kredibilitas Buhlmann: w = m / (m + M0).",
    )
    boot_b: int = Field(default=400, ge=50, description="Iterasi bootstrap CI beta.")

    # ---- RBD / horizon misi ---------------------------------------------
    missions: List[float] = Field(default=[24, 168, 720, 2160, 8760])
    mission_labels: List[str] = Field(
        default=["1 hari", "1 minggu", "1 bulan", "3 bulan", "1 tahun"]
    )
    rel_horizons: List[float] = Field(
        default=[1, 3, 7, 14, 30, 60, 90, 180, 365],
        description="Horizon misi modul E3 (hari).",
    )
    rel_levels: List[float] = Field(
        default=[0.99, 0.95, 0.90, 0.80, 0.50],
        description="Tingkat keandalan yang dicari untuk umur keandalan (modul E4).",
    )
    rel_bar_horizons: List[float] = Field(default=[1, 7, 30, 90])

    # ---- Monte Carlo (modul F) ------------------------------------------
    mc_reps: int = Field(default=400, ge=10, le=20000)
    mc_horizon: float = Field(default=8760.0, description="Horizon simulasi (jam).")
    mc_dt: float = Field(default=1.0, description="Resolusi grid simulasi (jam).")
    mc_seed: int = Field(default=7, description="Seed agar hasil reprodusibel.")

    # ---- Biaya PM (modul G) ---------------------------------------------
    cp: float = Field(
        default=1.0,
        gt=0,
        description="Biaya pemeliharaan preventif. Di-override data Order bila tersedia.",
    )
    cf: float = Field(
        default=10.0,
        gt=0,
        description="Biaya kegagalan korektif. Di-override data Order bila tersedia.",
    )

    # ---- Modul J: mesin rekomendasi strategi -----------------------------
    red_credit: float = Field(
        default=0.55,
        ge=0,
        le=1,
        description="Pengurangan konsekuensi bila tersedia unit cadangan paralel.",
    )
    beta_dfr: float = Field(default=0.90, description="Di bawah ini: pola kegagalan dini.")
    beta_wear: float = Field(default=1.20, description="Di atas ini: mekanisme aus.")
    ca_ifr: float = Field(default=1.20, description="beta Crow-AMSAA di atas ini: intensitas naik.")
    ca_dfr: float = Field(default=0.80, description="beta Crow-AMSAA di bawah ini: intensitas turun.")
    pm_min_saving: float = Field(default=10.0, description="Penghematan minimum (%) agar TBM dipilih.")
    risk_cbm: float = Field(default=6.0, description="Skor risiko minimum agar CBM dipilih.")
    risk_rtf: float = Field(default=5.0, description="Skor risiko maksimum agar RTF dipilih.")
    cbm_freq: str = Field(default="mingguan")
    eff_rca: float = Field(default=0.40)
    eff_tbm_cap: float = Field(default=0.60)
    eff_cbm: float = Field(default=0.30)
    eff_insp: float = Field(default=0.15)
    eff_trend_bonus: float = Field(default=0.05)
    svc_level: float = Field(default=0.95, gt=0, lt=1, description="Tingkat layanan stok suku cadang.")
    lead_months: float = Field(default=3.0, description="Waktu tunggu pengadaan (bulan).")
    spare_min_rate: float = Field(default=0.5, description="Ambang tampil tabel suku cadang (gagal/thn).")
    rec_top_n: int = Field(default=10, description="Jumlah rekomendasi naratif.")
    iso_downtime: float = Field(default=200.0, description="Garis iso-downtime jack-knife (jam/thn).")

    # ---- Modul optimasi biaya NSGA-II (§7) ------------------------------
    ga_pop_size: int = Field(default=60, ge=8, le=500)
    ga_generations: int = Field(default=60, ge=5, le=1000)
    ga_crossover_prob: float = Field(default=0.9, ge=0, le=1)
    ga_mutation_eta: float = Field(default=20.0, gt=0)
    ga_seed: int = Field(default=7)
    ga_horizon_days: float = Field(
        default=30.0, description="Horizon target keandalan pada objektif ke-2."
    )
    ga_tau_min_days: float = Field(default=7.0, gt=0)
    ga_tau_max_days: float = Field(default=730.0, gt=0)

    model_config = {"extra": "forbid"}


DEFAULT_CONFIG = Config()


def config_from_overrides(overrides: Dict[str, Any] | None) -> Config:
    """Bangun Config dari default + override parsial yang dikirim UI.

    Nilai tak dikenal atau tak valid ditolak oleh Pydantic sehingga error
    muncul sebagai pesan 422 yang informatif, bukan crash.
    """
    if not overrides:
        return DEFAULT_CONFIG.model_copy(deep=True)
    base = DEFAULT_CONFIG.model_dump()
    base.update({k: v for k, v in overrides.items() if v is not None})
    return Config(**base)
