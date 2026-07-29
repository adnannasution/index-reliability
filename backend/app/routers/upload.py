"""Endpoint upload & pratinjau berkas Excel (Fase 1)."""

from __future__ import annotations

import io
import logging
import traceback
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

from app.config.defaults import DEFAULT_CONFIG
from app.core import store
from app.core.data_loader import (
    DataLoadError,
    detect_kind,
    load_notifications,
    load_orders,
    preview_rows,
    read_all_sheets,
)

router = APIRouter(prefix="/api", tags=["upload"])

#: Batas ukuran berkas (berkas contoh ~2,4 MB; batas longgar untuk ekspor besar).
MAX_UPLOAD_BYTES = 80 * 1024 * 1024


def _load_sync(raw: bytes, filename: str) -> store.Dataset:
    """Pekerjaan berat pembacaan Excel: dijalankan di threadpool."""
    sheets = read_all_sheets(io.BytesIO(raw))
    pick = detect_kind(sheets)

    ds = store.Dataset(
        dataset_id=store.new_dataset_id(),
        kind=pick.kind,
        filename=filename,
        sheet_name=pick.sheet_name,
        uploaded_at=store.now_iso(),
        columns=[str(c) for c in pick.df.columns],
        sheets={name: [str(c) for c in df.columns] for name, df in sheets.items()},
        raw_sheets=sheets,
    )

    if pick.kind == "notification":
        nd = load_notifications(
            sheets, pick.sheet_name,
            unit_prefix=DEFAULT_CONFIG.unit,
            fail_types=DEFAULT_CONFIG.fail_types,
            window_end=DEFAULT_CONFIG.window_end,
        )
        ds.notification = nd
        ds.preview = preview_rows(nd.df, 25)
    else:
        od = load_orders(sheets, pick.sheet_name, unit_prefix=DEFAULT_CONFIG.unit)
        ds.order = od
        ds.preview = preview_rows(od.df, 25)
    return ds


@router.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    """Terima satu berkas Excel, deteksi jenisnya dari nama kolom, simpan sesi."""
    name = file.filename or "tanpa-nama.xlsx"
    if not name.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Format berkas '{name}' tidak didukung. Unggah berkas Excel "
                ".xlsx hasil ekspor SAP (bukan .xls atau .csv)."
            ),
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Berkas kosong (0 byte).")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Ukuran berkas {len(raw)/1_048_576:.1f} MB melebihi batas "
                f"{MAX_UPLOAD_BYTES/1_048_576:.0f} MB."
            ),
        )

    try:
        ds = await run_in_threadpool(_load_sync, raw, name)
    except DataLoadError as exc:
        # Pesan sudah ditulis untuk pengguna akhir (§3.3).
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - jangan biarkan crash jadi HTTP 500 buta.
        logger.exception("Kegagalan tak terduga saat membaca berkas %s", name)
        tb = traceback.format_exception_only(type(exc), exc)[-1].strip()
        raise HTTPException(
            status_code=400,
            detail=(
                f"Berkas '{name}' tidak dapat diproses. Rincian teknis: {tb}. "
                "Periksa bahwa berkas adalah ekspor SAP standar (IW28/IW29 untuk "
                "notifikasi, IW38/IW39 untuk order) dan tidak dimodifikasi manual."
            ),
        ) from exc

    store.put(ds)

    payload = {
        "dataset_id": ds.dataset_id,
        "kind": ds.kind,
        "filename": ds.filename,
        "sheet_name": ds.sheet_name,
        "uploaded_at": ds.uploaded_at,
        "columns": ds.columns,
        "sheets": ds.sheets,
        "preview": ds.preview,
    }
    if ds.notification is not None:
        nd = ds.notification
        payload["summary"] = {
            "rows_in_file": nd.n_rows_file,
            "rows_unit": len(nd.df),
            "unit_prefix": nd.unit_prefix,
            "t_start": nd.t_start.strftime("%Y-%m-%d"),
            "t_end": nd.t_end.strftime("%Y-%m-%d"),
            "t_obs_hours": nd.t_obs_hours,
            "t_obs_days": nd.t_obs_hours / 24.0,
            "n_dropped_dates": nd.n_dropped_dates,
            "n_tags": int(nd.df["tag"].nunique()),
            "n_fail": int(nd.df["is_fail"].sum()),
            "window_end": nd.window_end_mode,
        }
    else:
        od = ds.order
        assert od is not None
        payload["summary"] = {
            "rows_in_file": od.n_rows_file,
            "rows_unit": len(od.df),
            "unit_prefix": od.unit_prefix,
            "n_tags": int(od.df["tag"].nunique()) if len(od.df) else 0,
            "planned_cost_total": float(od.df["planned_cost"].sum()) if len(od.df) else 0.0,
            "actual_cost_total": float(od.df["actual_cost"].sum()) if len(od.df) else 0.0,
        }
    return store.json_safe(payload)


@router.get("/datasets")
async def datasets() -> List[dict]:
    """Daftar berkas yang sudah di-upload pada sesi ini."""
    return store.json_safe(store.list_all())


@router.get("/datasets/{dataset_id}/preview")
async def preview(dataset_id: str, limit: int = 25) -> dict:
    ds = store.get(dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan atau sudah kedaluwarsa.")
    limit = max(1, min(int(limit), 500))
    df = ds.notification.df if ds.notification is not None else ds.order.df  # type: ignore[union-attr]
    return store.json_safe(
        {
            "dataset_id": dataset_id,
            "kind": ds.kind,
            "columns": [str(c) for c in df.columns],
            "rows": preview_rows(df, limit),
            "total_rows": int(len(df)),
        }
    )


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str) -> dict:
    if not store.drop(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan.")
    return {"ok": True, "dataset_id": dataset_id}
