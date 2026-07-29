"""
Endpoint analisis interval pemeliharaan terhadap waktu.

Melayani tiga kebutuhan:
  * kurva laju biaya untuk beberapa tag peralatan pilihan pengguna;
  * grafik titik optimal bersumbu-y ganda (laju biaya dan keandalan) pada
    lingkup satu tag peralatan maupun satu Functional System;
  * rekomendasi interval bernalar beserta rujukannya.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core import store
from app.core.interval_analysis import (
    analisis_fs,
    analisis_peralatan,
    kurva_banyak_peralatan,
)
from app.routers.analysis import get_analysis, resolve_config
from app.routers.optimization import build_cost_model
from app.schemas.models import IntervalCurvesRequest, IntervalOptimumRequest

router = APIRouter(prefix="/api/interval", tags=["interval-pemeliharaan"])


@router.post("/curves")
async def curves(req: IntervalCurvesRequest) -> Dict[str, Any]:
    """Kurva laju biaya terhadap interval untuk tag yang dipilih pengguna."""
    cfg = resolve_config(req.config)

    def work() -> Dict[str, Any]:
        res = get_analysis(req.dataset_id, cfg)
        nds = store.get(req.dataset_id)
        cm = build_cost_model(nds, req.order_dataset_id, cfg)
        out = kurva_banyak_peralatan(
            res.eq_params, req.tags, cfg,
            pengali_rentang=req.range_multiplier,
            cost_by_tag=cm.by_tag if cm else None,
        )
        # Daftar tag yang layak dipilih, supaya UI dapat membangun pemilihnya
        # tanpa perlu memanggil endpoint analisis lain.
        out["pilihan_tag"] = [
            {
                "tag": r["tag"],
                "fs": r["fs"],
                "kelas": r["kelas"],
                "n_cm": r["n_cm"],
                "mtbf_hari": r["mtbf_hari"],
                "spof": r["spof"],
                "redundan": r["redundan"],
            }
            for r in res.equipment
            if r["n_cm"] > 0
        ]
        return out

    return store.json_safe(await run_in_threadpool(work))


@router.post("/optimum")
async def optimum(req: IntervalOptimumRequest) -> Dict[str, Any]:
    """Titik optimal biaya dan keandalan terhadap waktu, per tag atau per FS."""
    cfg = resolve_config(req.config)

    if req.scope == "equipment" and not req.tag:
        raise HTTPException(
            status_code=422,
            detail="Lingkup 'equipment' memerlukan satu tag peralatan pada kolom 'tag'.",
        )
    if req.scope == "fs" and req.fs is None:
        raise HTTPException(
            status_code=422,
            detail="Lingkup 'fs' memerlukan nomor Functional System 1, 2, atau 3 pada kolom 'fs'.",
        )

    def work() -> Dict[str, Any]:
        res = get_analysis(req.dataset_id, cfg)
        nds = store.get(req.dataset_id)
        cm = build_cost_model(nds, req.order_dataset_id, cfg)
        by_tag = cm.by_tag if cm else None

        try:
            if req.scope == "equipment":
                hasil = analisis_peralatan(
                    res.eq_params, str(req.tag), cfg,
                    r_target=req.r_target,
                    pengali_rentang=req.range_multiplier,
                    cost_by_tag=by_tag,
                )
            else:
                hasil = analisis_fs(
                    res.eq_params, int(req.fs), cfg,
                    r_target=req.r_target,
                    pengali_rentang=req.range_multiplier,
                    cost_by_tag=by_tag,
                )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "lingkup": hasil.lingkup,
            "label": hasil.label,
            "n_peralatan": hasil.n_peralatan,
            "kurva": hasil.kurva,
            "optimal_biaya": hasil.optimal_biaya,
            "optimal_keandalan": hasil.optimal_keandalan,
            "garis_dasar": hasil.garis_dasar,
            "rekomendasi": hasil.rekomendasi,
            "parameter": hasil.parameter,
            "peralatan": hasil.peralatan,
            "referensi": hasil.referensi,
            "catatan_sumbu": (
                "Sumbu mendatar adalah interval penggantian dalam hari. Sumbu tegak kiri "
                "adalah laju biaya pemeliharaan tahunan menurut model age replacement "
                "Barlow dan Hunter (1960). Sumbu tegak kanan adalah keandalan pada saat "
                "penggantian, yaitu peluang peralatan mencapai umur tersebut tanpa gagal. "
                "Titik biaya minimum menandai interval paling ekonomis, sedangkan garis "
                "target keandalan menandai interval terpanjang yang masih memenuhi "
                "persyaratan keandalan."
            ),
        }

    return store.json_safe(await run_in_threadpool(work))
