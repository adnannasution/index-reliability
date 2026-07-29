"""
Endpoint diagram RBD interaktif (§6).

Menyediakan:
  * struktur diagram (node stage + blok equipment) beserta metrik tiap blok,
  * detail satu equipment + kurva R(t)-nya,
  * perhitungan keandalan gabungan untuk SELEKSI blok pilihan pengguna
    (fitur utama: seleksi dinamis -> reliability instan).
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core import rbd as rbdmod
from app.core import store
from app.core.fs_mapping import (
    FS_FULL_NAME,
    RBD_STAGES,
    fs_name,
    is_redundant_tag,
    is_single_point_of_failure,
)
from app.routers.analysis import get_analysis, resolve_config
from app.schemas.models import SelectionRequest

router = APIRouter(prefix="/api/rbd", tags=["rbd"])

#: Grid waktu kurva R(t) untuk panel samping (hari).
_CURVE_DAYS = np.linspace(0.0, 365.0, 200)


def _block(tag: str, res) -> Dict[str, Any]:
    """Metrik ringkas satu blok equipment untuk diagram & tooltip."""
    e = res.eq_params.get(tag)
    return {
        "tag": tag,
        "label": tag.replace(res.meta["unit_prefix"], ""),
        "kelas": res.kelas.get(tag, (e.kelas if e else "other")),
        "kritikalitas": res.crit.get(tag, ""),
        "fs": fs_name(res.fs_of_tag.get(tag, 0)),
        "n_cm": int(res.n_cm.get(tag, 0)),
        "beta": float(e.beta) if e else None,
        "eta_jam": float(e.eta) if e and np.isfinite(e.eta) else None,
        "mtbf_jam": float(e.mtbf) if e and np.isfinite(e.mtbf) else None,
        "mtbf_hari": float(e.mtbf / 24.0) if e and np.isfinite(e.mtbf) else None,
        "mdt_jam": float(e.mdt) if e else None,
        "mttr_jam": float(e.mttr) if e else None,
        "a_inh": float(e.a_inh) if e else None,
        "a_op": float(e.a_op) if e else None,
        "redundan": is_redundant_tag(tag),
        "spof": is_single_point_of_failure(tag),
        "pernah_gagal": bool(e and not e.never_failed),
        "r_30hari": float(rbdmod.eq_r(res.eq_params, tag, 720.0)),
    }


@router.post("/diagram")
async def diagram(req: SelectionRequest) -> Dict[str, Any]:
    """Struktur lengkap diagram RBD: CDU keseluruhan + tiga FS.

    `req.tags` diabaikan di sini (dipakai endpoint /selection); dipakai skema
    yang sama agar klien hanya perlu satu bentuk permintaan.
    """
    cfg = resolve_config(req.config)
    res = await run_in_threadpool(get_analysis, req.dataset_id, cfg)

    fs_nodes: List[Dict[str, Any]] = []
    for fs in (1, 2, 3):
        stages: List[Dict[str, Any]] = []
        for st in RBD_STAGES:
            if st.fs != fs:
                continue
            blocks = [_block(t, res) for t in st.tags]
            r30 = float(rbdmod.stage_r(st, res.eq_params, 720.0))
            stages.append(
                {
                    "nama": st.name,
                    "tipe": st.typ,                     # 'ser' | 'par'
                    "notasi": ("seri" if st.typ == "ser"
                               else f"paralel 1-dari-{len(st.tags)}" if st.tags else "seri"),
                    "n_tag": len(st.tags),
                    "blocks": blocks,
                    "r_24j": float(rbdmod.stage_r(st, res.eq_params, 24.0)),
                    "r_30hari": r30,
                    "a_inh": float(rbdmod.stage_a(st, res.eq_params, "inh")),
                    "a_op": float(rbdmod.stage_a(st, res.eq_params, "op")),
                    "kosong": not st.tags,
                    "spof": st.typ == "ser" and any(b["spof"] for b in blocks),
                }
            )
        fs_nodes.append(
            {
                "fs": fs,
                "kode": fs_name(fs),
                "nama": FS_FULL_NAME[fs],
                "stages": stages,
                "r_24j": float(rbdmod.rbd_r(res.eq_params, fs, 24.0)),
                "r_30hari": float(rbdmod.rbd_r(res.eq_params, fs, 720.0)),
                "a_inh": float(rbdmod.rbd_a(res.eq_params, fs, "inh")),
                "a_op": float(rbdmod.rbd_a(res.eq_params, fs, "op")),
                "n_cm": sum(
                    int(res.n_cm.get(t, 0)) for t in res.tags if res.fs_of_tag.get(t) == fs
                ),
            }
        )

    return store.json_safe(
        {
            "dataset_id": req.dataset_id,
            "cdu": {
                "r_24j": float(rbdmod.cdu_r(res.eq_params, 24.0)),
                "r_30hari": float(rbdmod.cdu_r(res.eq_params, 720.0)),
                "a_inh": float(rbdmod.cdu_a(res.eq_params, "inh")),
                "a_op": float(rbdmod.cdu_a(res.eq_params, "op")),
                "susunan": "FS-1 -> FS-2 -> FS-3 (seri)",
            },
            "fs": fs_nodes,
            "legend": {
                "kritikalitas": [
                    {"kode": "H", "label": "Tinggi", "warna": "#B02A2A"},
                    {"kode": "M", "label": "Sedang", "warna": "#D98324"},
                    {"kode": "I", "label": "Insidental", "warna": "#2E5C8A"},
                    {"kode": "L", "label": "Rendah", "warna": "#2E8B74"},
                    {"kode": "Z", "label": "Tidak diklasifikasi", "warna": "#6B7280"},
                ],
                "konfigurasi": [
                    {"kode": "ser", "label": "Seri: semua harus beroperasi"},
                    {"kode": "par", "label": "Paralel / redundan: cukup satu beroperasi"},
                ],
            },
        }
    )


@router.post("/equipment")
async def equipment_detail(req: SelectionRequest) -> Dict[str, Any]:
    """Detail satu equipment + kurva R(t)-nya (klik blok pada diagram)."""
    cfg = resolve_config(req.config)
    res = await run_in_threadpool(get_analysis, req.dataset_id, cfg)

    tag = req.tags[0]
    if tag not in res.eq_params:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Tag '{tag}' tidak ada pada dataset ini. Tag hanya muncul bila "
                "tercatat di berkas notifikasi atau berada pada jalur RBD."
            ),
        )

    days = np.linspace(0.0, float(req.horizon_days), 200)
    rv = rbdmod.eq_r(res.eq_params, tag, days * 24.0)

    detail = _block(tag, res)
    st = rbdmod.stage_of_tag(tag)
    detail["stage"] = st.name if st else None
    detail["stage_tipe"] = st.typ if st else None
    detail["stage_tags"] = list(st.tags) if st else []

    # Baris modul C3 untuk tag ini (beta MRR, R2, Crow-AMSAA, bobot kredibilitas).
    c3 = next((r for r in res.weibull_equipment if r["tag"] == tag), None)

    return store.json_safe(
        {
            "detail": detail,
            "weibull": c3,
            "kurva": {"t_hari": days.tolist(), "r": [float(v) for v in rv]},
        }
    )


@router.post("/selection")
async def selection(req: SelectionRequest) -> Dict[str, Any]:
    """Keandalan gabungan untuk sekumpulan blok yang dipilih pengguna (§6).

    Logika penggabungan mengikuti struktur RBD sebenarnya: tag pada stage
    paralel yang sama digabung redundan (1 - prod(1-Ri)); antar-stage seri.
    """
    cfg = resolve_config(req.config)
    res = await run_in_threadpool(get_analysis, req.dataset_id, cfg)

    unknown = [t for t in req.tags if t not in res.eq_params]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Tag berikut tidak ada pada dataset ini: {', '.join(unknown[:8])}",
        )

    days = np.linspace(0.0, float(req.horizon_days), 240)
    hours = days * 24.0
    r_sel = rbdmod.selection_r(req.tags, res.eq_params, hours)

    # Rincian per stage agar pengguna melihat MENGAPA hasilnya demikian.
    groups: List[Dict[str, Any]] = []
    remaining = set(req.tags)
    for st in RBD_STAGES:
        picked = [t for t in st.tags if t in remaining]
        if not picked:
            continue
        remaining.difference_update(picked)
        groups.append(
            {
                "stage": st.name,
                "fs": fs_name(st.fs),
                "tipe": st.typ,
                "digabung": ("seri" if st.typ == "ser" or len(picked) == 1
                             else f"paralel 1-dari-{len(picked)}"),
                "tags": picked,
                "r_30hari": float(rbdmod.stage_r(
                    type(st)(st.fs, st.name, st.typ, tuple(picked)), res.eq_params, 720.0
                )),
            }
        )
    for t in sorted(remaining):
        groups.append(
            {
                "stage": "(di luar jalur RBD)", "fs": fs_name(res.fs_of_tag.get(t, 0)),
                "tipe": "ser", "digabung": "seri", "tags": [t],
                "r_30hari": float(rbdmod.eq_r(res.eq_params, t, 720.0)),
            }
        )

    horizons = [1.0, 7.0, 30.0, 90.0, 180.0, 365.0]
    ringkas = [
        {"hari": h, "r": float(rbdmod.selection_r(req.tags, res.eq_params, h * 24.0))}
        for h in horizons
    ]

    a_op = rbdmod.selection_availability(req.tags, res.eq_params, "op")
    a_inh = rbdmod.selection_availability(req.tags, res.eq_params, "inh")
    n_cm_total = sum(int(res.n_cm.get(t, 0)) for t in req.tags)

    return store.json_safe(
        {
            "tags": req.tags,
            "n_terpilih": len(req.tags),
            "kurva": {"t_hari": days.tolist(), "r": [float(v) for v in r_sel]},
            "horizon": ringkas,
            "a_inh": a_inh,
            "a_op": a_op,
            "n_cm_total": n_cm_total,
            "kelompok": groups,
            "tabel": [_block(t, res) for t in req.tags],
            "catatan": (
                "Penggabungan mengikuti tipe stage RBD masing-masing tag: tag pada "
                "stage paralel yang sama dihitung redundan, sisanya seri."
            ),
        }
    )
