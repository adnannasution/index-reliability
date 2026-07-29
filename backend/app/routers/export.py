"""Ekspor hasil ke Excel (multi-sheet) dan CSV per tabel (§9: tombol ekspor)."""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.core import store
from app.core.criticality import assess_all, build_module_j
from app.routers.analysis import get_analysis, resolve_config
from app.schemas.models import AnalyzeRequest

router = APIRouter(prefix="/api/export", tags=["ekspor"])

#: Nama sheet Excel maksimal 31 karakter.
_MAX_SHEET = 31


def _sheets_from_analysis(res, cfg) -> Dict[str, List[Dict[str, Any]]]:
    """Susun tabel-tabel hasil menjadi kumpulan sheet, mengikuti penamaan MATLAB."""
    sheets: Dict[str, List[Dict[str, Any]]] = {
        "A_KualitasData": res.data_quality,
        "B_Equipment": res.equipment,
        "B2_FunctionalSystem": res.functional_system,
        "B4_Pareto": res.pareto.get("equipment", []),
        "C_WeibullKelas": [
            {k: v for k, v in r.items() if not k.startswith("plot_")}
            for r in res.weibull_class
        ],
        "C2_WeibullFS": [
            {k: v for k, v in r.items() if not k.startswith("plot_")}
            for r in res.weibull_fs
        ],
        "C3_BetaEquipment": res.weibull_equipment,
        "D_TrenLaplace": res.laplace,
        "E1_StageRBD": [
            {k: (", ".join(v) if isinstance(v, list) else v) for k, v in r.items()}
            for r in res.rbd_stages
        ],
        "E2_SistemRBD": res.rbd_system,
        "E3_KeandalanFS": res.reliability_horizons,
        "E4_UmurKeandalan": res.reliability_life,
        "E5_Ketersediaan": res.availability,
    }
    # Tabulasi silang FS x kelas menjadi bentuk tabel.
    ct = res.crosstab
    if ct:
        rows = []
        for i, rname in enumerate(ct.get("rows", [])):
            row: Dict[str, Any] = {"Sistem": rname}
            for j, cname in enumerate(ct.get("classes", [])):
                row[cname] = ct["values"][i][j]
            rows.append(row)
        sheets["B3_TabSilang"] = rows
    if res.mrr_example:
        sheets["C3_ContohMRR"] = res.mrr_example.get("rows", [])
    return sheets


@router.post("/excel")
async def export_excel(req: AnalyzeRequest) -> StreamingResponse:
    """Unduh seluruh tabel hasil sebagai satu workbook Excel."""
    cfg = resolve_config(req.config)

    def work() -> bytes:
        res = get_analysis(req.dataset_id, cfg)
        sheets = _sheets_from_analysis(res, cfg)

        # Modul J bila dapat dihitung.
        try:
            ds = store.get(req.dataset_id)
            cost_by_tag = ds.cost_model.by_tag if ds and ds.cost_model else None
            ass = assess_all(
                res.eq_params, res.tags, res.n_cm, res.kelas, res.crit, res.fs_of_tag,
                res.beta_crow_by_tag, res.p_class_laplace, cfg, cost_by_tag=cost_by_tag,
            )
            j = build_module_j(ass, cfg)
            sheets["J1_Kekritisan"] = j["kekritisan"]
            sheets["J2_Strategi"] = j["strategi"]
            sheets["J3_SukuCadang"] = j["suku_cadang"]
            sheets["J4_DaftarTindakan"] = [
                {k: v for k, v in r.items() if k != "narasi"} for r in j["tindakan"]
            ]
        except Exception:  # noqa: BLE001 - ekspor tidak boleh gagal karena satu modul
            pass

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as xl:
            book = xl.book
            head = book.add_format(
                {"bold": True, "bg_color": "#1F3864", "font_color": "white",
                 "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True}
            )
            # Sampul.
            info = pd.DataFrame(
                [
                    ["Laporan", "Analisis Keandalan & Optimasi Pemeliharaan CDU"],
                    ["Unit", f"RU VI Balongan: Unit {cfg.unit.rstrip('-')} (CDU)"],
                    ["Jendela pengamatan", f"{res.meta['t_start']} s.d. {res.meta['t_end']}"],
                    ["T_obs (jam)", res.meta["t_obs_hours"]],
                    ["T_obs (hari)", round(res.meta["t_obs_days"] or 0, 1)],
                    ["Mode akhir jendela", res.meta["window_end"]],
                    ["Sumber beta RBD", cfg.beta_source],
                    ["Jumlah tag", res.meta["n_tags"]],
                    ["Kegagalan korektif", res.meta["total_cm"]],
                    ["Dibuat oleh", "Reliability & Maintenance Optimization Dashboard"],
                ],
                columns=["Keterangan", "Nilai"],
            )
            info.to_excel(xl, sheet_name="Sampul", index=False)
            for c, name in enumerate(info.columns):
                xl.sheets["Sampul"].write(0, c, name, head)
            xl.sheets["Sampul"].set_column(0, 0, 26)
            xl.sheets["Sampul"].set_column(1, 1, 58)

            for name, rows in sheets.items():
                if not rows:
                    continue
                df = pd.DataFrame(rows)
                sheet = name[:_MAX_SHEET]
                df.to_excel(xl, sheet_name=sheet, index=False)
                ws = xl.sheets[sheet]
                for c, col in enumerate(df.columns):
                    ws.write(0, c, str(col), head)
                    width = max(11, min(42, int(df[col].astype(str).str.len().max() or 11) + 2))
                    ws.set_column(c, c, width)
                ws.freeze_panes(1, 0)
                ws.autofilter(0, 0, max(len(df), 1), max(len(df.columns) - 1, 0))
        return buf.getvalue()

    data = await run_in_threadpool(work)
    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="Hasil_Keandalan_CDU_{stamp}.xlsx"'},
    )


@router.post("/csv/{table}")
async def export_csv(table: str, req: AnalyzeRequest) -> StreamingResponse:
    """Unduh satu tabel sebagai CSV (pemisah titik-koma, ramah Excel Indonesia)."""
    cfg = resolve_config(req.config)

    def work() -> str:
        res = get_analysis(req.dataset_id, cfg)
        sheets = _sheets_from_analysis(res, cfg)
        key = next((k for k in sheets if k.lower() == table.lower()), None)
        if key is None:
            raise HTTPException(
                status_code=404,
                detail=f"Tabel '{table}' tidak dikenal. Pilihan: {', '.join(sheets.keys())}",
            )
        rows = sheets[key]
        if not rows:
            raise HTTPException(status_code=404, detail=f"Tabel '{table}' kosong.")
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=list(rows[0].keys()), delimiter=";",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
        return out.getvalue()

    text = await run_in_threadpool(work)
    return StreamingResponse(
        io.StringIO(text), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{table}.csv"'},
    )
