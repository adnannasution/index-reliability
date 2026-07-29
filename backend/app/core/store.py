"""
Penyimpanan sesi dalam memori + penolong serialisasi JSON.

Satu berkas yang di-upload menjadi satu `Dataset` beridentitas `dataset_id`.
Hasil analisis di-cache per (dataset, sidik-jari konfigurasi) sehingga
perubahan parameter di UI memicu perhitungan ulang, sementara membuka-tutup
halaman tidak.

Catatan penyebaran: penyimpanan ini sengaja dibuat in-memory (proses tunggal)
karena aplikasi dijalankan sebagai alat analisis satu pengguna. Untuk
penyebaran multi-worker, ganti `_DATASETS` dengan Redis atau basis data.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from app.config.defaults import Config
from app.core.analysis import AnalysisResult
from app.core.cost_optimization import CostModel
from app.core.data_loader import NotificationData, OrderData

#: Batas jumlah dataset yang disimpan agar memori tidak tumbuh tanpa batas.
MAX_DATASETS = 12


@dataclass
class Dataset:
    dataset_id: str
    kind: str                     # 'notification' | 'order'
    filename: str
    sheet_name: str
    uploaded_at: str
    notification: Optional[NotificationData] = None
    order: Optional[OrderData] = None
    preview: list = field(default_factory=list)
    columns: list = field(default_factory=list)
    sheets: Dict[str, list] = field(default_factory=dict)
    #: DataFrame mentah tiap sheet, disimpan agar perubahan parameter pembacaan
    #: (prefix unit, windowEnd, failTypes) dapat dihitung ulang tanpa upload lagi.
    raw_sheets: Optional[Dict[str, pd.DataFrame]] = None
    #: cache hasil analisis: kunci = sidik jari konfigurasi
    analyses: Dict[str, AnalysisResult] = field(default_factory=dict)
    cost_model: Optional[CostModel] = None
    #: cache hasil komputasi berat: kunci = nama modul + sidik jari
    heavy: Dict[str, Any] = field(default_factory=dict)


_DATASETS: Dict[str, Dataset] = {}
_LOCK = threading.Lock()


def new_dataset_id() -> str:
    return uuid.uuid4().hex[:12]


def put(ds: Dataset) -> None:
    with _LOCK:
        _DATASETS[ds.dataset_id] = ds
        # Buang dataset terlama bila melewati batas.
        if len(_DATASETS) > MAX_DATASETS:
            oldest = sorted(_DATASETS.values(), key=lambda d: d.uploaded_at)[0]
            _DATASETS.pop(oldest.dataset_id, None)


def get(dataset_id: str) -> Optional[Dataset]:
    with _LOCK:
        return _DATASETS.get(dataset_id)


def list_all() -> list:
    with _LOCK:
        return [
            {
                "dataset_id": d.dataset_id,
                "kind": d.kind,
                "filename": d.filename,
                "sheet_name": d.sheet_name,
                "uploaded_at": d.uploaded_at,
                "rows": (
                    len(d.notification.df) if d.notification is not None
                    else (len(d.order.df) if d.order is not None else 0)
                ),
            }
            for d in sorted(_DATASETS.values(), key=lambda x: x.uploaded_at, reverse=True)
        ]


def drop(dataset_id: str) -> bool:
    with _LOCK:
        return _DATASETS.pop(dataset_id, None) is not None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def config_fingerprint(cfg: Config) -> str:
    """Sidik jari konfigurasi untuk kunci cache (hanya parameter yang mengubah hasil)."""
    keys = [
        "unit", "fail_types", "pm_type", "window_end", "beta_source", "beta_kmin",
        "cred_m0", "boot_b", "missions", "rel_horizons", "rel_levels", "cp", "cf",
        "red_credit", "beta_dfr", "beta_wear", "ca_ifr", "ca_dfr", "pm_min_saving",
        "risk_cbm", "risk_rtf", "svc_level", "lead_months", "spare_min_rate",
        "eff_rca", "eff_tbm_cap", "eff_cbm", "eff_insp", "eff_trend_bonus",
    ]
    d = cfg.model_dump()
    return "|".join(f"{k}={d.get(k)}" for k in keys)


# ==========================================================================
# Serialisasi JSON yang aman
# ==========================================================================
def json_safe(obj: Any) -> Any:
    """Bersihkan objek agar menghasilkan JSON yang SAH.

    NaN dan Infinity bukan JSON yang sah (RFC 8259) tetapi `json.dumps` Python
    menuliskannya apa adanya, sehingga `JSON.parse` di browser gagal. Fungsi ini
    mengubah nilai tak-hingga/NaN menjadi null, tipe numpy/pandas menjadi tipe
    Python asli, dan Timestamp menjadi teks ISO.
    """
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (pd.Timestamp, datetime)):
        return None if pd.isna(obj) else obj.isoformat()
    if isinstance(obj, np.ndarray):
        return [json_safe(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [json_safe(v) for v in obj]
    if obj is pd.NaT:
        return None
    # dataclass / objek lain -> dict atributnya
    if hasattr(obj, "__dataclass_fields__"):
        return {k: json_safe(getattr(obj, k)) for k in obj.__dataclass_fields__}
    if hasattr(obj, "model_dump"):
        return json_safe(obj.model_dump())
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return str(obj)
