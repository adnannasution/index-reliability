"""Endpoint komputasi berat: Monte Carlo (modul F), optimasi PM (G), kekritisan (J)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.core import store
from app.core.criticality import assess_all, build_module_j
from app.core.montecarlo import mc_system
from app.core.pm_optimization import optimize_module_g
from app.routers.analysis import get_analysis, resolve_config
from app.schemas.models import AnalyzeRequest

router = APIRouter(prefix="/api", tags=["simulasi"])


@router.post("/montecarlo")
async def montecarlo(req: AnalyzeRequest) -> Dict[str, Any]:
    """Simulasi Monte Carlo ketersediaan sistem (modul F). Seed tetap = reprodusibel."""
    cfg = resolve_config(req.config)

    def work() -> Dict[str, Any]:
        res = get_analysis(req.dataset_id, cfg)
        key = f"mc|{store.config_fingerprint(cfg)}|{cfg.mc_reps}|{cfg.mc_horizon}|{cfg.mc_seed}"
        ds = store.get(req.dataset_id)
        if ds is not None and key in ds.heavy:
            return ds.heavy[key]

        a_op = {r["sistem"]: r["a_op"] for r in res.availability}
        a_op["CDU total"] = a_op.get("CDU")
        mc = mc_system(
            res.eq_params, reps=cfg.mc_reps, horizon=cfg.mc_horizon,
            dt=cfg.mc_dt, seed=cfg.mc_seed, a_op_analytic=a_op,
        )
        out = {
            "tabel": mc.table,
            "sampel": mc.samples,
            "reps": mc.reps,
            "horizon_jam": mc.horizon_hours,
            "seed": mc.seed,
            "catatan": (
                "TTF dibangkitkan dari Weibull tiap peralatan; durasi perbaikan dari "
                "lognormal dengan rerata sama dengan MDT. Nilai P10 dipakai sebagai "
                "skenario buruk yang masih wajar untuk perencanaan suku cadang."
            ),
        }
        if ds is not None:
            ds.heavy[key] = out
        return out

    return store.json_safe(await run_in_threadpool(work))


@router.post("/pm-optimize")
async def pm_optimize_endpoint(req: AnalyzeRequest) -> Dict[str, Any]:
    """Optimasi interval PM age-replacement untuk bad actor tiap FS (modul G)."""
    cfg = resolve_config(req.config)

    def work() -> Dict[str, Any]:
        res = get_analysis(req.dataset_id, cfg)
        ds = store.get(req.dataset_id)
        cost_by_tag = (
            ds.cost_model.by_tag if ds is not None and ds.cost_model is not None else None
        )
        out = optimize_module_g(
            res.eq_params, res.tags, res.n_cm, res.fs_of_tag,
            cp=cfg.cp, cf=cfg.cf, cost_by_tag=cost_by_tag,
        )
        out["catatan"] = (
            "Penghematan bertanda negatif berarti kurva biaya datar atau menanjak: "
            "penggantian terjadwal justru lebih mahal daripada run-to-failure. Hal ini "
            "lazim ketika beta <= 1 karena tidak ada mekanisme aus yang dapat dicegah "
            "oleh jadwal."
        )
        return out

    return store.json_safe(await run_in_threadpool(work))


@router.post("/criticality")
async def criticality(req: AnalyzeRequest) -> Dict[str, Any]:
    """Kekritisan, strategi RCM, jack-knife, dan suku cadang (modul J)."""
    cfg = resolve_config(req.config)

    def work() -> Dict[str, Any]:
        res = get_analysis(req.dataset_id, cfg)
        ds = store.get(req.dataset_id)
        cost_by_tag = (
            ds.cost_model.by_tag if ds is not None and ds.cost_model is not None else None
        )
        assessments = assess_all(
            res.eq_params, res.tags, res.n_cm, res.kelas, res.crit, res.fs_of_tag,
            res.beta_crow_by_tag, res.p_class_laplace, cfg, cost_by_tag=cost_by_tag,
        )
        return build_module_j(assessments, cfg)

    return store.json_safe(await run_in_threadpool(work))
