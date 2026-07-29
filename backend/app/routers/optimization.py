"""Endpoint optimasi biaya-keandalan NSGA-II (§7) + penurunan biaya dari Order."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core import store
from app.core.cost_optimization import derive_costs, optimize_cost_reliability
from app.routers.analysis import get_analysis, resolve_config
from app.schemas.models import CostOptimizeRequest

router = APIRouter(prefix="/api", tags=["optimasi-biaya"])


def build_cost_model(notif_ds, order_dataset_id: str | None, cfg):
    """Turunkan CostModel dari berkas Order bila ada, dan simpan di dataset notifikasi."""
    if not order_dataset_id:
        return None
    ods = store.get(order_dataset_id)
    if ods is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset ORDER tidak ditemukan atau sudah kedaluwarsa. Unggah ulang berkas order.",
        )
    if ods.order is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Berkas '{ods.filename}' bukan berkas ORDER/BIAYA. Modul optimasi biaya "
                "memerlukan berkas dengan kolom 'TotalPlnndCosts'."
            ),
        )
    cm = derive_costs(
        ods.order, notif_ds.notification.notif_type_by_id,
        fail_types=cfg.fail_types, pm_type=cfg.pm_type,
    )
    notif_ds.cost_model = cm
    return cm


@router.post("/costs")
async def costs(req: CostOptimizeRequest) -> Dict[str, Any]:
    """Ringkasan biaya Cp/Cf per tag hasil agregasi berkas Order."""
    cfg = resolve_config(req.config)

    def work() -> Dict[str, Any]:
        get_analysis(req.dataset_id, cfg)          # memastikan dataset notifikasi sah
        nds = store.get(req.dataset_id)
        cm = build_cost_model(nds, req.order_dataset_id, cfg)
        if cm is None:
            return {
                "tersedia": False,
                "catatan": [
                    "Belum ada berkas ORDER yang diunggah, sehingga rasio biaya default "
                    f"dipakai (Cp = {cfg.cp}, Cf = {cfg.cf})."
                ],
                "cp_default": cfg.cp,
                "cf_default": cfg.cf,
                "per_tag": [],
            }
        return {
            "tersedia": bool(cm.by_tag),
            "n_order": cm.n_orders,
            "n_tertaut_notifikasi": cm.n_matched,
            "n_korektif": cm.n_corrective,
            "n_preventif": cm.n_preventive,
            "cp_global": cm.global_cp,
            "cf_global": cm.global_cf,
            "rasio_global": (cm.global_cf / cm.global_cp) if cm.global_cp > 0 else None,
            "peta_maintacttype": cm.fallback_map,
            "mata_uang": cm.currency,
            "catatan": cm.notes,
            "per_tag": [
                {"tag": t, **v} for t, v in sorted(cm.by_tag.items())
            ],
        }

    return store.json_safe(await run_in_threadpool(work))


@router.post("/cost-optimize")
async def cost_optimize(req: CostOptimizeRequest) -> Dict[str, Any]:
    """Pareto front NSGA-II biaya tahunan vs ketersediaan sistem CDU (§7)."""
    cfg = resolve_config(req.config)

    def work() -> Dict[str, Any]:
        res = get_analysis(req.dataset_id, cfg)
        nds = store.get(req.dataset_id)
        cm = build_cost_model(nds, req.order_dataset_id, cfg)

        lingkup_kunci = f"{req.scope}|{req.fs}|{','.join(sorted(req.tags or []))}"
        key = (
            f"ga|{store.config_fingerprint(cfg)}|{cfg.ga_pop_size}|{cfg.ga_generations}"
            f"|{cfg.ga_crossover_prob}|{cfg.ga_mutation_eta}|{cfg.ga_seed}"
            f"|{cfg.ga_tau_min_days}|{cfg.ga_tau_max_days}|{req.order_dataset_id}"
            f"|{lingkup_kunci}"
        )
        if nds is not None and key in nds.heavy:
            return nds.heavy[key]

        try:
            opt = optimize_cost_reliability(
                res.eq_params, cfg, cost_model=cm,
                scope=req.scope, fs=req.fs, tags=req.tags,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        out = {
            "variabel": opt.variables,
            "pareto": opt.pareto,
            "garis_dasar": opt.baseline,
            "tradeoff": opt.tradeoff,
            "konfigurasi_ga": opt.config,
            "sumber_biaya": opt.cost_source,
            "lingkup": opt.scope,
            "catatan": (
                "Objektif 1 adalah total biaya pemeliharaan tahunan memakai model age "
                "replacement Barlow dan Hunter. Objektif 2 adalah ketersediaan operasional "
                f"pada lingkup {opt.scope['label']} melalui RBD, dengan laju kegagalan "
                "efektif dari teorema pembaharuan. Front yang hampir datar pada sumbu "
                "ketersediaan berarti interval PM sedikit berpengaruh, konsisten dengan "
                "beta di sekitar satu yang menandakan kegagalan acak."
            ),
        }
        if nds is not None:
            nds.heavy[key] = out
        return out

    return store.json_safe(await run_in_threadpool(work))
