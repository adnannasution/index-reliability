"""
Orkestrator analisis: menjalankan modul A, B, B2-B4, C, C2, C3, D, D2, E1-E4
dengan urutan yang sama seperti CDU_PdM_Balongan.m.

Hasil disimpan sebagai satu objek `AnalysisResult` yang dapat diserialisasi ke
JSON dan dipakai seluruh endpoint. Perhitungan berat (Monte Carlo, NSGA-II)
dipisah ke modulnya sendiri dan dipanggil sesuai permintaan.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from app.config.defaults import CLASSES, Config
from app.core import reliability as rel
from app.core import rbd as rbdmod
from app.core.data_loader import NotificationData
from app.core.fs_mapping import (
    BETA_WORKBOOK,
    FS_MAP,
    RBD_STAGES,
    fs_name,
    fs_of,
    is_redundant_tag,
    is_single_point_of_failure,
    mdt_of,
    tag_type,
)

FS_IDS: Tuple[int, ...] = (1, 2, 3, 0)


def _f(x: Any) -> Optional[float]:
    """Angka aman-JSON: NaN/Inf -> None (agar tidak menghasilkan JSON tak sah)."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def _id(x: Any, d: int = 1) -> str:
    """Format angka menurut kaidah penulisan Indonesia.

    Koma sebagai pemisah desimal dan titik sebagai pemisah ribuan, misalnya
    17064 menjadi "17.064" dan 10.3 menjadi "10,3". Dipakai untuk teks kartu
    ringkasan yang dikirim siap tampil ke antarmuka.
    """
    v = _f(x)
    if v is None:
        return "-"
    # Format Amerika lebih dulu, lalu tukar pemisahnya.
    s = f"{v:,.{d}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


@dataclass
class AnalysisResult:
    """Seluruh keluaran analisis non-biaya."""

    config: Config
    meta: Dict[str, Any] = field(default_factory=dict)
    data_quality: List[Dict[str, Any]] = field(default_factory=list)
    equipment: List[Dict[str, Any]] = field(default_factory=list)
    functional_system: List[Dict[str, Any]] = field(default_factory=list)
    crosstab: Dict[str, Any] = field(default_factory=dict)
    pareto: Dict[str, Any] = field(default_factory=dict)
    weibull_class: List[Dict[str, Any]] = field(default_factory=list)
    weibull_fs: List[Dict[str, Any]] = field(default_factory=list)
    weibull_equipment: List[Dict[str, Any]] = field(default_factory=list)
    mrr_example: Dict[str, Any] = field(default_factory=dict)
    #: data plot probabilitas Weibull per equipment (grafik 7) untuk tag terkaya data
    mrr_plots: List[Dict[str, Any]] = field(default_factory=list)
    laplace: List[Dict[str, Any]] = field(default_factory=list)
    rbd_stages: List[Dict[str, Any]] = field(default_factory=list)
    rbd_system: List[Dict[str, Any]] = field(default_factory=list)
    reliability_curve: Dict[str, Any] = field(default_factory=dict)
    reliability_horizons: List[Dict[str, Any]] = field(default_factory=list)
    reliability_life: List[Dict[str, Any]] = field(default_factory=list)
    availability: List[Dict[str, Any]] = field(default_factory=list)
    beta_comparison: List[Dict[str, Any]] = field(default_factory=list)
    kpi: List[Dict[str, Any]] = field(default_factory=list)

    # ---- objek internal (tidak diserialisasi langsung) ----
    eq_params: Dict[str, rbdmod.EquipmentParams] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    n_cm: Dict[str, int] = field(default_factory=dict)
    n_pm: Dict[str, int] = field(default_factory=dict)
    kelas: Dict[str, str] = field(default_factory=dict)
    crit: Dict[str, str] = field(default_factory=dict)
    mdt: Dict[str, float] = field(default_factory=dict)
    fs_of_tag: Dict[str, int] = field(default_factory=dict)
    beta_class_mle: Dict[str, float] = field(default_factory=dict)
    beta_crow_by_tag: Dict[str, float] = field(default_factory=dict)
    p_class_laplace: Dict[str, float] = field(default_factory=dict)
    t_obs: float = 0.0


def run_analysis(nd: NotificationData, cfg: Config) -> AnalysisResult:
    """Jalankan seluruh pipa analisis keandalan pada satu berkas notifikasi."""
    res = AnalysisResult(config=cfg)
    df = nd.df
    t_obs = nd.t_obs_hours
    res.t_obs = t_obs
    unit = nd.unit_prefix

    fail = df[df["is_fail"]]
    tags: List[str] = sorted(df["tag"].dropna().unique().tolist())
    res.tags = tags

    # ---------------- A. Kualitas data & rekap ----------------
    n_cm = {t: 0 for t in tags}
    n_pm = {t: 0 for t in tags}
    for t, c in Counter(fail["tag"]).items():
        n_cm[t] = int(c)
    pm_rows = df[df["type"] == cfg.pm_type]
    for t, c in Counter(pm_rows["tag"]).items():
        n_pm[t] = int(c)

    kelas = {t: tag_type(t, unit) for t in tags}
    mdt = {t: mdt_of(t) for t in tags}
    fs_tag_raw = {t: fs_of(t) for t in tags}
    fs_tag = {t: (v if v >= 0 else 0) for t, v in fs_tag_raw.items()}
    # Kritikalitas = nilai pada notifikasi PERTAMA tag tsb (df sudah urut tanggal).
    crit: Dict[str, str] = {}
    for t in tags:
        vals = df.loc[df["tag"] == t, "crit"].dropna()
        crit[t] = str(vals.iloc[0]) if len(vals) else ""

    res.n_cm, res.n_pm, res.kelas, res.crit, res.mdt = n_cm, n_pm, kelas, crit, mdt
    res.fs_of_tag = fs_tag

    n_unmapped = sum(1 for v in fs_tag_raw.values() if v < 0)
    total_cm = int(sum(n_cm.values()))

    res.data_quality = [
        {"metrik": "Total notifikasi Unit terpilih", "nilai": int(len(df))},
        {"metrik": "Kegagalan korektif M1", "nilai": int((df["type"] == "M1").sum())},
        {"metrik": "Kegagalan korektif M2", "nilai": int((df["type"] == "M2").sum())},
        {"metrik": f"Preventif {cfg.pm_type}", "nilai": int((df["type"] == cfg.pm_type).sum())},
        {"metrik": "Jumlah tag unik", "nilai": len(tags)},
        {"metrik": "Tag tanpa mapping FS", "nilai": n_unmapped},
        {"metrik": "Tanggal kosong (dibuang)", "nilai": nd.n_dropped_dates},
        {"metrik": "Jendela pengamatan (hari)", "nilai": int(round((nd.t_end - nd.t_start).days))},
        {"metrik": "Jendela pengamatan (jam)", "nilai": int(round(t_obs))},
    ]

    res.meta = {
        "unit_prefix": unit,
        "sheet_name": nd.sheet_name,
        "rows_in_file": nd.n_rows_file,
        "rows_unit": int(len(df)),
        "t_start": nd.t_start.strftime("%Y-%m-%d"),
        "t_end": nd.t_end.strftime("%Y-%m-%d"),
        "t_obs_hours": _f(t_obs),
        "t_obs_days": _f(t_obs / 24.0),
        "window_end": nd.window_end_mode,
        "n_tags": len(tags),
        "n_unmapped": n_unmapped,
        "total_cm": total_cm,
        "unmapped_tags": [t for t, v in fs_tag_raw.items() if v < 0],
    }

    # ---------------- B. Keandalan per equipment ----------------
    # MTBF = T_obs / n_CM  (ISO 14224:2016: periode surveilans / jumlah kegagalan)
    eq_rows: List[Dict[str, Any]] = []
    for t in tags:
        k = n_cm[t]
        mtbf = t_obs / k if k > 0 else float("inf")
        eq_rows.append(
            {
                "tag": t,
                "fs": fs_name(fs_tag[t]),
                "kelas": kelas[t],
                "kritikalitas": crit[t],
                "n_cm": k,
                "n_pm": n_pm[t],
                "mtbf_hari": _f(mtbf / 24.0),
                "mtbf_jam": _f(mtbf),
                "gagal_per_thn": _f(8760.0 / mtbf) if k > 0 else 0.0,
                "mdt_jam": _f(mdt[t]),
                "redundan": is_redundant_tag(t),
                "spof": is_single_point_of_failure(t),
            }
        )
    eq_rows.sort(key=lambda r: (-r["n_cm"], r["tag"]))
    res.equipment = eq_rows

    # ---- Pareto equipment (aturan 80/20) ----
    ranked = [r for r in eq_rows if r["n_cm"] > 0]
    cum = 0.0
    pareto_eq = []
    for r in ranked:
        cum += r["n_cm"]
        pareto_eq.append(
            {"tag": r["tag"], "n_cm": r["n_cm"],
             "kumulatif_pct": _f(100.0 * cum / total_cm) if total_cm else 0.0}
        )

    # ---------------- B2. Rekap per Functional System ----------------
    fs_cm = {f: 0 for f in FS_IDS}
    fs_pm = {f: 0 for f in FS_IDS}
    fs_tags: Dict[int, List[str]] = defaultdict(list)
    for t in tags:
        f = fs_tag[t]
        fs_cm[f] += n_cm[t]
        fs_pm[f] += n_pm[t]
        fs_tags[f].append(t)

    fs_rows = []
    for f in FS_IDS:
        cm = fs_cm[f]
        lam = cm / t_obs if t_obs > 0 else 0.0
        mtbf_f = t_obs / cm if cm > 0 else float("inf")
        fs_rows.append(
            {
                "fs": f,
                "sistem": fs_name(f),
                "n_tag": len(fs_tags[f]),
                "n_cm": cm,
                "n_pm": fs_pm[f],
                "share_cm_pct": _f(100.0 * cm / total_cm) if total_cm else 0.0,
                "lambda_seri_perjam": _f(lam),
                "mtbf_seri_jam": _f(mtbf_f),
                "mtbf_seri_hari": _f(mtbf_f / 24.0),
                "e_gagal_per_thn": _f(8760.0 * lam),
            }
        )
    res.functional_system = fs_rows

    # ---------------- B3. Tabulasi silang FS x kelas ----------------
    ct = [[0 for _ in CLASSES] for _ in range(3)]
    for t in tags:
        f = fs_tag[t]
        if f in (1, 2, 3) and kelas[t] in CLASSES:
            ct[f - 1][CLASSES.index(kelas[t])] += n_cm[t]
    res.crosstab = {"classes": list(CLASSES), "rows": ["FS-1", "FS-2", "FS-3"], "values": ct}

    # ---------------- B4. Pareto per FS ----------------
    pareto_fs: Dict[str, List[Dict[str, Any]]] = {}
    for f in (1, 2, 3):
        items = [(t, n_cm[t]) for t in fs_tags[f] if n_cm[t] > 0]
        items.sort(key=lambda p: (-p[1], p[0]))
        pareto_fs[fs_name(f)] = [{"tag": t, "n_cm": c} for t, c in items]
    res.pareto = {"equipment": pareto_eq, "per_fs": pareto_fs, "total_cm": total_cm}

    # ---------------- C. Weibull per kelas ----------------
    def pool_tbf_class(cc: str) -> List[float]:
        """Port `poolTBF(..., 'class')`: TBF gabungan seluruh tag satu kelas."""
        out: List[float] = []
        for t in tags:
            if kelas[t] != cc:
                continue
            d = np.sort(fail.loc[fail["tag"] == t, "date"].values)
            if d.size >= 2:
                out.extend((np.diff(d) / np.timedelta64(1, "h")).tolist())
        return [v for v in out if v > 0]

    def pool_tbf_fs(f: int) -> List[float]:
        """Port `poolTBF(..., 'fs')`."""
        out: List[float] = []
        for t in tags:
            if fs_tag[t] != f:
                continue
            d = np.sort(fail.loc[fail["tag"] == t, "date"].values)
            if d.size >= 2:
                out.extend((np.diff(d) / np.timedelta64(1, "h")).tolist())
        return [v for v in out if v > 0]

    w_class: Dict[str, float] = {}
    for cc in CLASSES:
        fit = rel.fit_block(pool_tbf_class(cc), cc, boot_b=cfg.boot_b)
        w_class[cc] = fit.beta
        res.weibull_class.append(_fit_to_row(fit, "Kelas"))
    res.beta_class_mle = w_class

    # ---------------- C2. Weibull per FS ----------------
    for f in (1, 2, 3):
        fit = rel.fit_block(pool_tbf_fs(f), fs_name(f), boot_b=cfg.boot_b)
        res.weibull_fs.append(_fit_to_row(fit, "Sistem"))

    # ---------------- C3. Weibull per equipment ----------------
    beta_by_tag: Dict[str, float] = {}
    crow_by_tag: Dict[str, float] = {}
    rich_tag, rich_k, rich_obj = "", -1, None
    mrr_objs: List[rel.EquipmentBeta] = []
    for t in tags:
        k = n_cm[t]
        if k < 1:
            continue
        d = np.sort(fail.loc[fail["tag"] == t, "date"].values)
        tbf = (np.diff(d) / np.timedelta64(1, "h")).tolist() if d.size >= 2 else []
        tbf = [v for v in tbf if v > 0]
        susp = float((nd.t_end.to_datetime64() - d[-1]) / np.timedelta64(1, "h"))
        cal = ((d - nd.t_start.to_datetime64()) / np.timedelta64(1, "h")).tolist()

        eb = rel.equipment_beta(
            tag=t, fs_label=fs_name(fs_tag[t]), kelas=kelas[t],
            tbf_hours=tbf, susp_hours=susp, cal_hours=cal,
            n_failures=k, t_obs_hours=t_obs,
            prior_beta_class=w_class.get(kelas[t], 1.0),
            beta_kmin=cfg.beta_kmin, cred_m0=cfg.cred_m0,
        )
        beta_by_tag[t] = eb.beta_final
        if eb.beta_crow_amsaa is not None:
            crow_by_tag[t] = eb.beta_crow_amsaa

        res.weibull_equipment.append(
            {
                "tag": eb.tag, "fs": eb.fs, "kelas": eb.kelas, "n_cm": eb.n_cm,
                "mtbf_hari": _f(eb.mtbf_hours / 24.0),
                "beta_mrr": _f(eb.beta_mrr), "gof_r2": _f(eb.r2),
                "beta_mlec": _f(eb.beta_mle_corrected),
                "beta_crow_amsaa": _f(eb.beta_crow_amsaa),
                "prior_kelas": _f(eb.prior_class), "bobot_w": _f(eb.weight_w),
                "beta_final": _f(eb.beta_final), "eta_final_j": _f(eb.eta_final),
                "region": rel.ifr_region(eb.beta_final),
                "sumber": eb.source,
                "n_tbf": len(tbf),
            }
        )
        if k > rich_k:
            rich_k, rich_tag, rich_obj = k, t, eb
        if len(eb.mrr_table) >= 2:
            mrr_objs.append(eb)

    res.weibull_equipment.sort(key=lambda r: (-(r["n_cm"] or 0), r["tag"]))
    res.beta_crow_by_tag = crow_by_tag

    # ---- Data plot probabilitas Weibull per equipment (grafik 7) ----
    # Enam tag terkaya data: ln(TBF) vs ln(-ln(1-F)) beserta garis regresinya.
    mrr_objs.sort(key=lambda e: (-e.n_cm, e.tag))
    for eb in mrr_objs[:6]:
        xs = [r[3] for r in eb.mrr_table]
        ys = [r[4] for r in eb.mrr_table]
        if eb.beta_mrr is None or len(xs) < 2:
            continue
        mx, my = float(np.mean(xs)), float(np.mean(ys))
        inter = my - eb.beta_mrr * mx
        res.mrr_plots.append(
            {
                "tag": eb.tag, "fs": eb.fs, "kelas": eb.kelas, "n_cm": eb.n_cm,
                "beta_mrr": _f(eb.beta_mrr), "r2": _f(eb.r2),
                "x": [_f(v) for v in xs], "y": [_f(v) for v in ys],
                "fit_x": [_f(min(xs)), _f(max(xs))],
                "fit_y": [_f(eb.beta_mrr * min(xs) + inter), _f(eb.beta_mrr * max(xs) + inter)],
            }
        )

    # ---- Contoh perhitungan MRR langkah-demi-langkah (transparansi akademik) ----
    if rich_obj is not None and rich_obj.mrr_table:
        res.mrr_example = {
            "tag": rich_tag,
            "n_cm": rich_k,
            "n_tbf": len(rich_obj.mrr_table),
            "beta_mrr": _f(rich_obj.beta_mrr),
            "r2": _f(rich_obj.r2),
            "beta_mlec": _f(rich_obj.beta_mle_corrected),
            "beta_crow": _f(rich_obj.beta_crow_amsaa),
            "beta_final": _f(rich_obj.beta_final),
            "eta_final": _f(rich_obj.eta_final),
            "rows": [
                {"i": i + 1, "tbf_jam": _f(r[0]), "adj_rank": _f(r[1]),
                 "median_rank": _f(r[2]), "x_ln_t": _f(r[3]), "y": _f(r[4])}
                for i, r in enumerate(rich_obj.mrr_table)
            ],
        }

    # ---------------- D / D2. Uji tren Laplace ----------------
    def pool_fail_times(key: Any, mode: str) -> List[float]:
        """Port `poolFailTimes()`: waktu kegagalan (jam sejak awal jendela)."""
        out: List[float] = []
        for t in tags:
            if mode == "class" and kelas[t] != key:
                continue
            if mode == "fs" and fs_tag[t] != key:
                continue
            d = fail.loc[fail["tag"] == t, "date"].values
            out.extend(((d - nd.t_start.to_datetime64()) / np.timedelta64(1, "h")).tolist())
        return out

    p_class: Dict[str, float] = {}
    for cc in CLASSES:
        row = rel.laplace_row("Kelas", cc, pool_fail_times(cc, "class"), t_obs)
        res.laplace.append(_laplace_to_row(row))
        if np.isfinite(row.p_value):
            p_class[cc] = row.p_value
    for f in (1, 2, 3):
        row = rel.laplace_row("Sistem", fs_name(f), pool_fail_times(f, "fs"), t_obs)
        res.laplace.append(_laplace_to_row(row))
    res.p_class_laplace = p_class

    # ---------------- E. RBD ----------------
    eq = rbdmod.build_equipment_params(
        tags=tags, n_cm=n_cm, kelas=kelas, mdt=mdt, t_obs=t_obs,
        beta_source=cfg.beta_source,
        beta_by_tag=beta_by_tag,
        beta_by_class=(BETA_WORKBOOK if cfg.beta_source == "workbook" else w_class),
    )
    # Tag jalur RBD yang tak pernah muncul di notifikasi (mis. P-112A/C/D):
    # tambahkan dengan n_CM = 0 -> R = 1, A = 1 (perilaku eqR/eqA MATLAB).
    for st in RBD_STAGES:
        for tg in st.tags:
            if tg not in eq:
                eq[tg] = rbdmod.EquipmentParams(
                    tag=tg, beta=1.0, eta=float("inf"), mtbf=float("inf"), n_cm=0,
                    a_inh=1.0, a_op=1.0, mdt=mdt_of(tg), mttr=24.0,
                    kelas=tag_type(tg, unit),
                )
    res.eq_params = eq

    # ---- E1. Tabel stage ----
    missions = np.array(cfg.missions, dtype=float)
    for st in RBD_STAGES:
        rv = stage_r_at(st, eq, missions)
        res.rbd_stages.append(
            {
                "fs": st.fs, "sistem": fs_name(st.fs), "stage": st.name,
                "konfig": st.typ, "n_tag": len(st.tags), "tags": list(st.tags),
                "r_24j": _f(rv[0]), "r_1bln": _f(rv[2]), "r_1thn": _f(rv[4]),
                "a_inh": _f(rbdmod.stage_a(st, eq, "inh")),
                "a_op": _f(rbdmod.stage_a(st, eq, "op")),
            }
        )

    # ---- E2. Tabel sistem per FS + total CDU ----
    a_inh_fs, a_op_fs = {}, {}
    r_sys: Dict[int, np.ndarray] = {}
    for f in (1, 2, 3):
        r_sys[f] = rbdmod.rbd_r(eq, f, missions)
        a_inh_fs[f] = rbdmod.rbd_a(eq, f, "inh")
        a_op_fs[f] = rbdmod.rbd_a(eq, f, "op")
        r_ser = rbdmod.full_series_r(fs_tags[f], eq, 720.0)
        res.rbd_system.append(
            {
                "sistem": fs_name(f), "n_cm": fs_cm[f],
                "mtbf_seri_hari": _f(t_obs / fs_cm[f] / 24.0) if fs_cm[f] else None,
                "r_24j": _f(r_sys[f][0]), "r_1bln": _f(r_sys[f][2]), "r_1thn": _f(r_sys[f][4]),
                "r_1bln_seripenuh": _f(r_ser),
                "a_inh": _f(a_inh_fs[f]), "a_op": _f(a_op_fs[f]),
            }
        )
    r_cdu = r_sys[1] * r_sys[2] * r_sys[3]
    a_inh_c = a_inh_fs[1] * a_inh_fs[2] * a_inh_fs[3]
    a_op_c = a_op_fs[1] * a_op_fs[2] * a_op_fs[3]
    cm123 = fs_cm[1] + fs_cm[2] + fs_cm[3]
    res.rbd_system.append(
        {
            "sistem": "CDU (FS-1..3 seri)", "n_cm": cm123,
            "mtbf_seri_hari": _f(t_obs / cm123 / 24.0) if cm123 else None,
            "r_24j": _f(r_cdu[0]), "r_1bln": _f(r_cdu[2]), "r_1thn": _f(r_cdu[4]),
            "r_1bln_seripenuh": None,
            "a_inh": _f(a_inh_c), "a_op": _f(a_op_c),
        }
    )
    res.availability = [
        {"sistem": fs_name(f), "a_inh": _f(a_inh_fs[f]), "a_op": _f(a_op_fs[f])}
        for f in (1, 2, 3)
    ] + [{"sistem": "CDU", "a_inh": _f(a_inh_c), "a_op": _f(a_op_c)}]

    # ---- E3. Kurva & tabel keandalan per horizon ----
    hz_d = np.array(cfg.rel_horizons, dtype=float)
    hz_h = hz_d * 24.0
    r_fs = {f: rbdmod.rbd_r(eq, f, hz_h) for f in (1, 2, 3)}
    r_gab = r_fs[1] * r_fs[2] * r_fs[3]
    for j, d_ in enumerate(hz_d):
        res.reliability_horizons.append(
            {
                "horizon": f"{d_:g} hari", "hari": _f(d_), "jam": _f(hz_h[j]),
                "r_fs1": _f(r_fs[1][j]), "r_fs2": _f(r_fs[2][j]),
                "r_fs3": _f(r_fs[3][j]), "r_gabungan": _f(r_gab[j]),
            }
        )

    # Kurva halus untuk grafik (linear & log): 400 titik sampai 1 tahun.
    tt = np.linspace(1.0, 8760.0, 400)
    curve = {f"fs{f}": rbdmod.rbd_r(eq, f, tt) for f in (1, 2, 3)}
    curve_cdu = curve["fs1"] * curve["fs2"] * curve["fs3"]
    res.reliability_curve = {
        "t_hari": (tt / 24.0).tolist(),
        "fs1": [_f(v) for v in curve["fs1"]],
        "fs2": [_f(v) for v in curve["fs2"]],
        "fs3": [_f(v) for v in curve["fs3"]],
        "cdu": [_f(v) for v in curve_cdu],
    }

    # ---- E4. Umur keandalan ----
    tg_d = np.linspace(0.05, 730.0, 6000)
    rc = {f: rbdmod.rbd_r(eq, f, tg_d * 24.0) for f in (1, 2, 3)}
    rc4 = rc[1] * rc[2] * rc[3]
    for label, arr in (("FS-1", rc[1]), ("FS-2", rc[2]), ("FS-3", rc[3]), ("Gabungan (CDU)", rc4)):
        row: Dict[str, Any] = {"sistem": label}
        for lv in cfg.rel_levels:
            row[f"t_R{int(round(lv * 100)):02d}_hari"] = _f(rel.rel_life(tg_d, arr, lv))
        res.reliability_life.append(row)

    # ---- Perbandingan beta kelas vs beta per-equipment (dampak pilihan metode) ----
    eq_wb = rbdmod.build_equipment_params(
        tags=tags, n_cm=n_cm, kelas=kelas, mdt=mdt, t_obs=t_obs,
        beta_source="workbook", beta_by_tag={}, beta_by_class=BETA_WORKBOOK,
    )
    for st in RBD_STAGES:
        for tg in st.tags:
            if tg not in eq_wb:
                eq_wb[tg] = eq[tg]
    for f in (1, 2, 3):
        res.beta_comparison.append(
            {
                "sistem": fs_name(f),
                "r30_kelas": _f(float(rbdmod.rbd_r(eq_wb, f, 720.0))),
                "r30_equip": _f(float(rbdmod.rbd_r(eq, f, 720.0))),
                "aop_kelas": _f(rbdmod.rbd_a(eq_wb, f, "op")),
                "aop_equip": _f(rbdmod.rbd_a(eq, f, "op")),
            }
        )

    # ---------------- Kartu KPI (port kpiList) ----------------
    worst_fs = max((r for r in fs_rows if r["fs"] in (1, 2, 3)), key=lambda r: r["n_cm"])
    mtbf_vals = [r["mtbf_seri_hari"] for r in fs_rows if r["fs"] in (1, 2, 3) and r["mtbf_seri_hari"]]
    # Kartu ringkasan utama. Angka diformat dengan koma sebagai pemisah desimal
    # dan titik sebagai pemisah ribuan, mengikuti kaidah penulisan Indonesia.
    res.kpi = [
        {"judul": "Kegagalan korektif", "nilai": _id(total_cm, 0), "satuan": "kejadian",
         "keterangan": f"jenis notifikasi {' dan '.join(cfg.fail_types)}",
         "tone": "biru", "ikon": "peringatan"},
        {"judul": "Sistem paling terbebani", "nilai": worst_fs["sistem"], "satuan": "",
         "keterangan": f"menanggung {worst_fs['n_cm']} kegagalan",
         "tone": "merah", "ikon": "kilang"},
        {"judul": "MTBF sistem terendah", "nilai": _id(min(mtbf_vals), 1) if mtbf_vals else "-",
         "satuan": "hari", "keterangan": "jarak rata rata antar gangguan",
         "tone": "merah", "ikon": "jam"},
        {"judul": "Ketersediaan jalur penuh", "nilai": _id(a_op_c, 3), "satuan": "",
         "keterangan": "gabungan ketiga sistem secara seri",
         "tone": "kuning", "ikon": "bagan-alir"},
        {"judul": "Jendela pengamatan", "nilai": _id(t_obs / 24.0, 0), "satuan": "hari",
         "keterangan": f"{_id(t_obs, 0)} jam, mode {nd.window_end_mode}",
         "tone": "biru", "ikon": "berkas"},
        {"judul": "Peralatan dianalisis", "nilai": _id(len(tags), 0), "satuan": "tag",
         "keterangan": f"{sum(1 for t in tags if n_cm[t] > 0)} di antaranya pernah gagal",
         "tone": "hijau", "ikon": "roda-gigi"},
    ]
    return res


def stage_r_at(st, eq, t: np.ndarray) -> np.ndarray:
    return rbdmod.stage_r(st, eq, t)


def _fit_to_row(fit: rel.BlockFit, level: str) -> Dict[str, Any]:
    return {
        "tingkat": level, "nama": fit.name, "n_tbf": fit.n_tbf,
        "beta": _f(fit.beta), "beta_lo": _f(fit.beta_lo), "beta_hi": _f(fit.beta_hi),
        "eta_jam": _f(fit.eta), "gof_r2": _f(fit.r2),
        "region": fit.region, "sumber": fit.source,
        "plot_x": [_f(v) for v in fit.plot_x],
        "plot_y": [_f(v) for v in fit.plot_y],
        "plot_yhat": [_f(v) for v in fit.plot_yhat],
    }


def _laplace_to_row(row: rel.LaplaceRow) -> Dict[str, Any]:
    return {
        "tingkat": row.level, "nama": row.name, "n_gagal": row.n_fail,
        "u_laplace": _f(row.u), "p_value": _f(row.p_value), "tafsiran": row.verdict,
    }
