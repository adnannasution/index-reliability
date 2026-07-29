"""Skema Pydantic untuk permintaan & tanggapan API (§2: skema ketat)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.config.defaults import BetaSource, WeibullEstimator, WindowEnd


class ConfigOverrides(BaseModel):
    """Parameter yang dapat diubah dari panel pengaturan UI (§4.9).

    Semua bersifat opsional; yang tidak dikirim memakai nilai `defaults.py`.
    """

    unit: Optional[str] = None
    fail_types: Optional[List[str]] = None
    pm_type: Optional[str] = None
    window_end: Optional[WindowEnd] = None
    beta_source: Optional[BetaSource] = None
    beta_kmin: Optional[int] = Field(default=None, ge=1, le=50)
    cred_m0: Optional[float] = Field(default=None, gt=0, le=100)
    boot_b: Optional[int] = Field(default=None, ge=50, le=5000)
    cp: Optional[float] = Field(default=None, gt=0)
    cf: Optional[float] = Field(default=None, gt=0)
    mc_reps: Optional[int] = Field(default=None, ge=10, le=20000)
    mc_horizon: Optional[float] = Field(default=None, gt=0)
    mc_seed: Optional[int] = None
    red_credit: Optional[float] = Field(default=None, ge=0, le=1)
    beta_dfr: Optional[float] = Field(default=None, gt=0)
    beta_wear: Optional[float] = Field(default=None, gt=0)
    ca_ifr: Optional[float] = Field(default=None, gt=0)
    ca_dfr: Optional[float] = Field(default=None, gt=0)
    pm_min_saving: Optional[float] = Field(default=None, ge=0, le=100)
    risk_cbm: Optional[float] = Field(default=None, ge=0, le=25)
    risk_rtf: Optional[float] = Field(default=None, ge=0, le=25)
    svc_level: Optional[float] = Field(default=None, gt=0, lt=1)
    lead_months: Optional[float] = Field(default=None, gt=0, le=36)
    spare_min_rate: Optional[float] = Field(default=None, ge=0)
    rec_top_n: Optional[int] = Field(default=None, ge=1, le=100)
    iso_downtime: Optional[float] = Field(default=None, gt=0)
    ga_pop_size: Optional[int] = Field(default=None, ge=8, le=500)
    ga_generations: Optional[int] = Field(default=None, ge=5, le=1000)
    ga_crossover_prob: Optional[float] = Field(default=None, ge=0, le=1)
    ga_mutation_eta: Optional[float] = Field(default=None, gt=0)
    ga_seed: Optional[int] = None
    ga_tau_min_days: Optional[float] = Field(default=None, gt=0)
    ga_tau_max_days: Optional[float] = Field(default=None, gt=0)

    model_config = {"extra": "forbid"}


class AnalyzeRequest(BaseModel):
    dataset_id: str = Field(..., min_length=4)
    config: Optional[ConfigOverrides] = None
    #: Estimator yang ditonjolkan pada tampilan Weibull (tidak mengubah RBD;
    #: sumber beta RBD diatur oleh `config.beta_source`).
    weibull_estimator: Optional[WeibullEstimator] = None

    model_config = {"extra": "forbid"}


class SelectionRequest(BaseModel):
    """Permintaan perhitungan keandalan gabungan untuk seleksi blok RBD (§6)."""

    dataset_id: str = Field(..., min_length=4)
    tags: List[str] = Field(..., min_length=1, max_length=200)
    config: Optional[ConfigOverrides] = None
    horizon_days: float = Field(default=365.0, gt=0, le=3650)

    model_config = {"extra": "forbid"}


Lingkup = Literal["cdu", "fs", "equipment"]


class CostOptimizeRequest(BaseModel):
    dataset_id: str = Field(..., min_length=4, description="dataset NOTIFIKASI")
    order_dataset_id: Optional[str] = Field(
        default=None, description="dataset ORDER; bila kosong memakai rasio biaya default"
    )
    config: Optional[ConfigOverrides] = None

    #: Lingkup analisis: seluruh CDU, satu Functional System, atau tag pilihan.
    scope: Lingkup = "cdu"
    fs: Optional[int] = Field(default=None, ge=1, le=3, description="wajib bila scope='fs'")
    tags: Optional[List[str]] = Field(
        default=None, max_length=60, description="wajib bila scope='equipment'"
    )

    model_config = {"extra": "forbid"}


class IntervalCurvesRequest(BaseModel):
    """Kurva laju biaya terhadap interval untuk beberapa tag pilihan pengguna."""

    dataset_id: str = Field(..., min_length=4)
    tags: List[str] = Field(..., min_length=1, max_length=40)
    order_dataset_id: Optional[str] = None
    config: Optional[ConfigOverrides] = None
    #: Batas atas grid interval sebagai pengali eta. 3 menyamai modul G MATLAB.
    range_multiplier: float = Field(default=3.0, ge=1.0, le=12.0)

    model_config = {"extra": "forbid"}


class IntervalOptimumRequest(BaseModel):
    """Grafik titik optimal: laju biaya dan keandalan terhadap waktu."""

    dataset_id: str = Field(..., min_length=4)
    scope: Literal["equipment", "fs"] = "equipment"
    tag: Optional[str] = Field(default=None, description="wajib bila scope='equipment'")
    fs: Optional[int] = Field(default=None, ge=1, le=3, description="wajib bila scope='fs'")
    order_dataset_id: Optional[str] = None
    config: Optional[ConfigOverrides] = None
    #: Tingkat keandalan minimum yang masih diterima pada saat penggantian.
    r_target: float = Field(default=0.90, gt=0.0, lt=1.0)
    range_multiplier: float = Field(default=3.0, ge=1.0, le=12.0)

    model_config = {"extra": "forbid"}


class ApiError(BaseModel):
    detail: str
    kind: str = "error"
    hint: Optional[str] = None
