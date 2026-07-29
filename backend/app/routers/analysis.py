"""
Endpoint analisis keandalan (modul A, B, B2-B4, C, C2, C3, D, D2, E1-E4).

Seluruh perhitungan berat dijalankan di threadpool agar event loop FastAPI
tidak terblokir (§10: frontend tidak boleh freeze).
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.config.defaults import Config, config_from_overrides
from app.core import store
from app.core.analysis import AnalysisResult, run_analysis
from app.core.data_loader import DataLoadError, load_notifications
from app.schemas.models import AnalyzeRequest

router = APIRouter(prefix="/api", tags=["analisis"])


def resolve_config(overrides: Any) -> Config:
    """Bangun Config dari override UI dengan pesan galat yang ramah."""
    try:
        raw = overrides.model_dump(exclude_none=True) if overrides is not None else {}
        return config_from_overrides(raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=422, detail=f"Parameter pengaturan tidak sah: {exc}"
        ) from exc


def get_analysis(dataset_id: str, cfg: Config) -> AnalysisResult:
    """Ambil hasil analisis dari cache, hitung bila belum ada.

    Bila `cfg.unit`/`window_end`/`fail_types` berbeda dari saat upload, berkas
    dibaca ulang dari DataFrame mentah yang sudah tersimpan agar jendela
    pengamatan dan filter unit ikut berubah.
    """
    ds = store.get(dataset_id)
    if ds is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset tidak ditemukan atau sudah kedaluwarsa. Unggah ulang berkas notifikasi.",
        )
    if ds.notification is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Berkas '{ds.filename}' dikenali sebagai berkas ORDER/BIAYA, bukan NOTIFIKASI. "
                "Analisis keandalan memerlukan berkas notifikasi (kolom 'Notifictn type')."
            ),
        )

    fp = store.config_fingerprint(cfg)
    cached = ds.analyses.get(fp)
    if cached is not None:
        return cached

    nd = ds.notification
    # Parameter pembacaan berubah -> baca ulang dari berkas asal bila perlu.
    needs_reload = (
        nd.unit_prefix != cfg.unit
        or nd.window_end_mode != cfg.window_end
        or set(nd.df.loc[nd.df["is_fail"], "type"].unique()) - set(cfg.fail_types)
    )
    if needs_reload and ds.raw_sheets is not None:
        try:
            nd = load_notifications(
                ds.raw_sheets, ds.sheet_name,
                unit_prefix=cfg.unit, fail_types=cfg.fail_types, window_end=cfg.window_end,
            )
        except DataLoadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        ds.notification = nd

    try:
        res = run_analysis(nd, cfg)
    except DataLoadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=(
                "Analisis gagal diselesaikan. Periksa apakah berkas memuat cukup "
                f"kegagalan korektif untuk unit '{cfg.unit}'. Rincian teknis: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    ds.analyses[fp] = res
    # Jaga cache tetap kecil.
    if len(ds.analyses) > 6:
        ds.analyses.pop(next(iter(ds.analyses)))
    return res


@router.post("/analyze")
async def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    """Jalankan seluruh pipa analisis dan kembalikan semua tabel + data grafik."""
    cfg = resolve_config(req.config)
    res = await run_in_threadpool(get_analysis, req.dataset_id, cfg)

    return store.json_safe(
        {
            "dataset_id": req.dataset_id,
            "config": cfg.model_dump(),
            "meta": res.meta,
            "kpi": res.kpi,
            "data_quality": res.data_quality,
            "equipment": res.equipment,
            "functional_system": res.functional_system,
            "crosstab": res.crosstab,
            "pareto": res.pareto,
            "weibull_class": res.weibull_class,
            "weibull_fs": res.weibull_fs,
            "weibull_equipment": res.weibull_equipment,
            "mrr_example": res.mrr_example,
            "mrr_plots": res.mrr_plots,
            "laplace": res.laplace,
            "rbd_stages": res.rbd_stages,
            "rbd_system": res.rbd_system,
            "reliability_curve": res.reliability_curve,
            "reliability_horizons": res.reliability_horizons,
            "reliability_life": res.reliability_life,
            "availability": res.availability,
            "beta_comparison": res.beta_comparison,
        }
    )
