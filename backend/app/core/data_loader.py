"""
Pembacaan & normalisasi berkas Excel SAP (robust): §3 spesifikasi.

Prinsip:
  * Jenis berkas dideteksi dari NAMA KOLOM, bukan nama berkas.
  * Sheet dipilih dengan mencari sheet yang memuat kolom wajib: nama sheet
    tidak pernah di-hard-code.
  * Pencocokan nama kolom case-insensitive dan tahan spasi ganda / tanda baca,
    memakai kunci normalisasi yang sama dengan `pickcol()` MATLAB:
    lower(regexprep(s, '[^a-zA-Z0-9]', '')).
  * Kolom wajib yang hilang menghasilkan pesan jelas (DataLoadError), bukan
    stack trace.
  * Tidak ada daftar tag, jumlah baris, atau tanggal yang di-hard-code; semua
    diturunkan dari berkas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

# Excel (Windows) menyimpan tanggal sebagai serial hari sejak 1899-12-30.
# Sama dengan datetime(x,'ConvertFrom','excel') pada MATLAB.
EXCEL_EPOCH = pd.Timestamp("1899-12-30")


class DataLoadError(Exception):
    """Kesalahan pembacaan berkas yang layak ditampilkan apa adanya ke pengguna."""


# --------------------------------------------------------------------------
# Normalisasi nama kolom
# --------------------------------------------------------------------------
def norm_key(s: object) -> str:
    """Kunci pencocokan kolom: port `pickcol()` MATLAB.

    Membuang seluruh karakter non-alfanumerik lalu huruf kecil, sehingga
    'Notif.date', 'NOTIF DATE', dan 'Notif  Date' semuanya cocok.
    """
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).lower()


def find_column(df: pd.DataFrame, want: str) -> Optional[str]:
    """Nama kolom asli pada `df` yang cocok dengan `want`, atau None."""
    key = norm_key(want)
    for col in df.columns:
        if norm_key(col) == key:
            return col
    return None


def pick_column(df: pd.DataFrame, want: str, *, sheet: str = "") -> pd.Series:
    """Ambil satu kolom; error informatif bila tidak ada (§3.3)."""
    col = find_column(df, want)
    if col is None:
        where = f" pada sheet '{sheet}'" if sheet else ""
        raise DataLoadError(
            f"Kolom '{want}' tidak ditemukan{where}; pastikan format file sama. "
            f"Kolom yang tersedia: {', '.join(str(c) for c in df.columns[:25])}"
        )
    return df[col]


def has_columns(df: pd.DataFrame, wanted: Sequence[str]) -> bool:
    keys = {norm_key(c) for c in df.columns}
    return all(norm_key(w) in keys for w in wanted)


# --------------------------------------------------------------------------
# Konversi tanggal
# --------------------------------------------------------------------------
def to_id_series(s: pd.Series) -> pd.Series:
    """Normalisasi kolom nomor SAP (Notification / Order) menjadi teks kanonik.

    PENTING untuk keandalan join antar-berkas: ekspor SAP menyimpan nomor yang
    sama kadang sebagai int64 dan kadang sebagai float64 (karena ada sel
    kosong). Tanpa normalisasi, `str(2102362822.0)` = '2102362822.0' tidak
    pernah cocok dengan '2102362822', sehingga penggabungan order-notifikasi
    gagal diam-diam. Di sini seluruh nilai numerik dibulatkan ke bilangan bulat
    lalu dijadikan teks tanpa '.0'.
    """
    num = pd.to_numeric(s, errors="coerce")
    out = s.astype("string").str.strip()
    ok = num.notna()
    if ok.any():
        out.loc[ok] = num[ok].round().astype("int64").astype("string")
    return out.replace({"": pd.NA, "nan": pd.NA, "<NA>": pd.NA})


def to_datetime_series(s: pd.Series) -> pd.Series:
    """Konversi kolom tanggal ke datetime, apa pun bentuk aslinya.

    Menangani tiga bentuk yang lazim keluar dari ekspor SAP:
      1. sudah datetime (openpyxl mengenali number-format tanggal),
      2. serial Excel numerik (mis. 46173),
      3. teks tanggal.
    Nilai yang tak dapat ditafsirkan menjadi NaT dan DIBUANG oleh pemanggil,
    lalu dilaporkan sebagai 'Tanggal kosong (dibuang)' pada kartu kualitas data.
    """
    if pd.api.types.is_datetime64_any_dtype(s):
        return s

    if pd.api.types.is_numeric_dtype(s):
        num = pd.to_numeric(s, errors="coerce")
        # Serial Excel yang wajar: > 0 dan < 2958466 (31-12-9999).
        num = num.where((num > 0) & (num < 2958466))
        return EXCEL_EPOCH + pd.to_timedelta(num, unit="D")

    # Campuran teks/angka: coba angka dulu, sisanya sebagai teks tanggal.
    num = pd.to_numeric(s, errors="coerce")
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    mask_num = num.notna() & (num > 0) & (num < 2958466)
    if mask_num.any():
        out.loc[mask_num] = EXCEL_EPOCH + pd.to_timedelta(num[mask_num], unit="D")
    rest = ~mask_num
    if rest.any():
        out.loc[rest] = pd.to_datetime(s[rest], errors="coerce", dayfirst=True)
    return out


# --------------------------------------------------------------------------
# Deteksi jenis berkas
# --------------------------------------------------------------------------
#: Kolom penanda berkas NOTIFIKASI (§3.1).
NOTIF_REQUIRED = ["Notifictn type", "Notif.date", "Functional Loc."]
#: Kolom penanda berkas ORDER/BIAYA (§3.2).
ORDER_REQUIRED = ["TotalPlnndCosts"]


@dataclass
class SheetPick:
    """Sheet terpilih beserta jenisnya."""

    kind: str  # 'notification' | 'order'
    sheet_name: str
    df: pd.DataFrame


def read_all_sheets(path_or_buf) -> Dict[str, pd.DataFrame]:
    """Baca seluruh sheet. Error I/O diterjemahkan menjadi DataLoadError."""
    try:
        sheets = pd.read_excel(path_or_buf, sheet_name=None, engine="openpyxl")
    except Exception as exc:  # noqa: BLE001 - dilaporkan apa adanya ke UI
        raise DataLoadError(
            "Berkas tidak dapat dibaca sebagai Excel (.xlsx). "
            f"Rincian: {type(exc).__name__}: {exc}"
        ) from exc
    if not sheets:
        raise DataLoadError("Berkas Excel tidak memuat sheet apa pun.")
    return sheets


def detect_kind(sheets: Dict[str, pd.DataFrame]) -> SheetPick:
    """Tentukan jenis berkas dari NAMA KOLOM (bukan nama berkas): §3.

    Sheet notifikasi dicari lebih dulu; bila tidak ada, dicari sheet order.
    """
    for name, df in sheets.items():
        if has_columns(df, NOTIF_REQUIRED):
            return SheetPick("notification", name, df)
    for name, df in sheets.items():
        if has_columns(df, ORDER_REQUIRED) and find_column(df, "Functional Loc.") is not None:
            return SheetPick("order", name, df)

    tried = "; ".join(
        f"'{n}' ({', '.join(str(c) for c in d.columns[:8])}...)" for n, d in list(sheets.items())[:4]
    )
    raise DataLoadError(
        "Jenis berkas tidak dikenali. Berkas NOTIFIKASI harus memuat kolom "
        f"{NOTIF_REQUIRED}; berkas ORDER harus memuat 'TotalPlnndCosts' dan "
        f"'Functional Loc.'. Sheet yang diperiksa: {tried}"
    )


# --------------------------------------------------------------------------
# Hasil pembacaan
# --------------------------------------------------------------------------
@dataclass
class NotificationData:
    """Notifikasi Unit terpilih, sudah bersih dan urut tanggal."""

    df: pd.DataFrame               # kolom: type, date, tag, crit, equipment, description, order
    sheet_name: str
    t_start: pd.Timestamp
    t_end: pd.Timestamp
    t_obs_hours: float
    n_dropped_dates: int           # baris unit dengan tanggal kosong yang dibuang
    n_rows_file: int               # total baris pada sheet (seluruh unit)
    window_end_mode: str
    unit_prefix: str
    #: nomor notifikasi -> jenis (M1/M2/M3) untuk SELURUH berkas (semua unit).
    #: Dipakai modul biaya untuk menggolongkan order sebagai korektif/preventif.
    notif_type_by_id: Dict[str, str] = field(default_factory=dict)

    @property
    def is_fail(self) -> pd.Series:
        return self.df["is_fail"]


@dataclass
class OrderData:
    """Order pemeliharaan Unit terpilih beserta biaya."""

    df: pd.DataFrame               # kolom: tag, equipment, planned_cost, actual_cost, ...
    sheet_name: str
    n_rows_file: int
    unit_prefix: str


def load_notifications(
    sheets: Dict[str, pd.DataFrame],
    sheet_name: str,
    *,
    unit_prefix: str = "11-",
    fail_types: Sequence[str] = ("M1", "M2"),
    window_end: str = "cutoff",
) -> NotificationData:
    """Baca & normalisasi berkas notifikasi (modul A MATLAB).

    Jendela pengamatan (ISO 14224:2016: periode surveilans, bukan jarak
    antar-kejadian):
        T_start = notifikasi unit PERTAMA
        T_end   = 'cutoff'    -> tanggal terakhir di SELURUH berkas (tanggal
                                 ekspor SAP; menghasilkan T_obs = 17.064 j,
                                 identik laporan)
                  'lastevent' -> notifikasi unit TERAKHIR
        T_obs   = T_end - T_start
    """
    raw = sheets[sheet_name]
    n_rows_file = int(len(raw))

    ntype = pick_column(raw, "Notifictn type", sheet=sheet_name).astype("string").str.strip()
    floc = pick_column(raw, "Functional Loc.", sheet=sheet_name).astype("string").str.strip()
    ndate_all = to_datetime_series(pick_column(raw, "Notif.date", sheet=sheet_name))

    # Kolom pendukung: opsional, tidak boleh menggagalkan pembacaan.
    def optional(name: str) -> pd.Series:
        col = find_column(raw, name)
        if col is None:
            return pd.Series([pd.NA] * len(raw), index=raw.index, dtype="string")
        return raw[col].astype("string").str.strip()

    def optional_id(name: str) -> pd.Series:
        col = find_column(raw, name)
        if col is None:
            return pd.Series([pd.NA] * len(raw), index=raw.index, dtype="string")
        return to_id_series(raw[col])

    crit = optional("Criticality")
    equipment = optional("Equipment")
    description = optional("Description")
    order_no = optional_id("Order")
    notif_no = optional_id("Notification")

    mask_unit = floc.fillna("").str.startswith(unit_prefix)
    if not mask_unit.any():
        found = sorted({str(v)[:3] for v in floc.dropna().unique()[:400] if str(v)[:1].isdigit()})
        raise DataLoadError(
            f"Tidak ada baris dengan Functional Loc. berawalan '{unit_prefix}'. "
            f"Prefix unit yang terlihat pada berkas: {', '.join(found[:15]) or '(tidak terbaca)'}. "
            "Ubah 'Prefix unit' pada panel pengaturan bila unit yang dituju berbeda."
        )

    df = pd.DataFrame(
        {
            "type": ntype[mask_unit],
            "date": ndate_all[mask_unit],
            "tag": floc[mask_unit],
            "crit": crit[mask_unit],
            "equipment": equipment[mask_unit],
            "description": description[mask_unit],
            "order": order_no[mask_unit],
            "notification": notif_no[mask_unit],
        }
    )

    n_dropped = int(df["date"].isna().sum())
    df = df[df["date"].notna()].sort_values("date", kind="mergesort").reset_index(drop=True)
    if df.empty:
        raise DataLoadError(
            f"Seluruh baris unit '{unit_prefix}' memiliki tanggal kosong atau tidak "
            "dapat ditafsirkan; tidak ada yang dapat dianalisis."
        )

    df["is_fail"] = df["type"].isin(list(fail_types))

    t_start = df["date"].min()
    if str(window_end).lower() == "cutoff":
        valid_all = ndate_all.dropna()
        t_end = valid_all.max() if not valid_all.empty else df["date"].max()
    else:
        t_end = df["date"].max()

    t_obs_hours = float((t_end - t_start).total_seconds() / 3600.0)
    if t_obs_hours <= 0:
        raise DataLoadError(
            "Jendela pengamatan nol atau negatif (tanggal awal dan akhir sama). "
            "Diperlukan rentang tanggal yang lebih dari satu hari untuk menghitung MTBF."
        )

    # Peta nomor notifikasi -> jenis untuk SELURUH berkas (bukan hanya unit ini),
    # agar order yang menunjuk notifikasi unit lain tetap dapat digolongkan.
    notif_type_by_id: Dict[str, str] = {}
    id_col = find_column(raw, "Notification")
    if id_col is not None:
        ids = to_id_series(raw[id_col])
        for nid, ntp in zip(ids, ntype):
            if pd.notna(nid) and pd.notna(ntp):
                notif_type_by_id[str(nid)] = str(ntp)

    return NotificationData(
        df=df,
        sheet_name=sheet_name,
        t_start=t_start,
        t_end=t_end,
        t_obs_hours=t_obs_hours,
        n_dropped_dates=n_dropped,
        n_rows_file=n_rows_file,
        window_end_mode=str(window_end).lower(),
        unit_prefix=unit_prefix,
        notif_type_by_id=notif_type_by_id,
    )


def load_orders(
    sheets: Dict[str, pd.DataFrame],
    sheet_name: str,
    *,
    unit_prefix: str = "11-",
) -> OrderData:
    """Baca & normalisasi berkas order/biaya (§3.2).

    Biaya diambil apa adanya dari SAP; pemisahan preventif vs korektif
    dikerjakan di core/cost_optimization.py karena memerlukan tautan ke
    notifikasi.
    """
    raw = sheets[sheet_name]
    n_rows_file = int(len(raw))

    floc = pick_column(raw, "Functional Loc.", sheet=sheet_name).astype("string").str.strip()
    planned = pd.to_numeric(
        pick_column(raw, "TotalPlnndCosts", sheet=sheet_name), errors="coerce"
    ).fillna(0.0)

    def optional_num(name: str) -> pd.Series:
        col = find_column(raw, name)
        if col is None:
            return pd.Series(0.0, index=raw.index, dtype="float64")
        return pd.to_numeric(raw[col], errors="coerce").fillna(0.0)

    def optional_str(name: str) -> pd.Series:
        col = find_column(raw, name)
        if col is None:
            return pd.Series([pd.NA] * len(raw), index=raw.index, dtype="string")
        return raw[col].astype("string").str.strip()

    def optional_date(name: str) -> pd.Series:
        col = find_column(raw, name)
        if col is None:
            return pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]")
        return to_datetime_series(raw[col])

    def optional_id(name: str) -> pd.Series:
        col = find_column(raw, name)
        if col is None:
            return pd.Series([pd.NA] * len(raw), index=raw.index, dtype="string")
        return to_id_series(raw[col])

    actual = optional_num("Total act.costs")

    mask_unit = floc.fillna("").str.startswith(unit_prefix)

    df = pd.DataFrame(
        {
            "tag": floc,
            "equipment": optional_str("Equipment"),
            "notification": optional_id("Notification"),
            "order": optional_id("Order"),
            "description": optional_str("Description"),
            "planned_cost": planned,
            "actual_cost": actual,
            "order_type": optional_str("Order Type"),
            "maint_act_type": optional_str("MaintActivType"),
            "priority": optional_str("Priority"),
            "priority_type": optional_str("PriorityType"),
            "basic_start": optional_date("Bas. start date"),
            "basic_finish": optional_date("Basic fin. date"),
            "actual_finish": optional_date("Actual Finish"),
        }
    )[mask_unit].reset_index(drop=True)

    return OrderData(
        df=df, sheet_name=sheet_name, n_rows_file=n_rows_file, unit_prefix=unit_prefix
    )


# --------------------------------------------------------------------------
# Pratinjau untuk UI
# --------------------------------------------------------------------------
def preview_rows(df: pd.DataFrame, limit: int = 25) -> List[Dict[str, object]]:
    """Baris awal untuk tabel pratinjau; nilai dibuat aman untuk JSON."""
    head = df.head(limit)
    out: List[Dict[str, object]] = []
    for _, row in head.iterrows():
        rec: Dict[str, object] = {}
        for col, val in row.items():
            rec[str(col)] = _json_safe(val)
        out.append(rec)
    return out


def _json_safe(val: object) -> object:
    if val is None or (isinstance(val, float) and not np.isfinite(val)):
        return None
    if isinstance(val, (pd.Timestamp, datetime)):
        return None if pd.isna(val) else val.strftime("%Y-%m-%d")
    if val is pd.NaT or (not isinstance(val, (list, dict, tuple)) and pd.isna(val)):
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        f = float(val)
        return f if np.isfinite(f) else None
    if isinstance(val, (np.bool_,)):
        return bool(val)
    return val if isinstance(val, (str, int, float, bool)) else str(val)
