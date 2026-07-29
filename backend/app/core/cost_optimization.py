"""
Optimasi biaya-keandalan multi-objektif dengan NSGA-II (§7).

MASALAH
-------
Variabel keputusan: interval PM tau_i (hari) untuk setiap peralatan kritis
                     pada jalur RBD yang memiliki riwayat kegagalan.
Objektif 1 (min)  : total biaya pemeliharaan tahunan
                     = sum_i 8760 * C_i(tau_i)
                     dengan C_i dari model age-replacement Barlow-Hunter:
                         C(tau) = [Cp*R(tau) + Cf*(1-R(tau))] / L(tau)
                         L(tau) = integral_0^tau R(t) dt
Objektif 2 (max)  : ketersediaan operasional sistem CDU (A_op gabungan),
                     dihitung lewat RBD seri-paralel dari A_op tiap peralatan
                     pada kebijakan tau yang dipilih.

Hubungan tau -> keandalan memakai TEOREMA PEMBAHARUAN (renewal reward):
    laju kegagalan efektif  lambda_eff(tau) = [1 - R(tau)] / L(tau)
    MTBF efektif            = 1 / lambda_eff(tau)
    A_op efektif            = MTBF_eff / (MTBF_eff + MDT)
Saat tau -> tak hingga, lambda_eff -> 1/MTTF sehingga kebijakan kembali ke
run-to-failure: konsisten dengan garis dasar modul E.

Ref:
  - Deb, K., Pratap, A., Agarwal, S. & Meyarivan, T. (2002), "A Fast and
    Elitist Multiobjective Genetic Algorithm: NSGA-II", IEEE Transactions on
    Evolutionary Computation 6(2), 182-197.
  - Barlow, R.E. & Hunter, L.C. (1960), Operations Research 8(1), 90-100.
  - Barlow, R.E. & Proschan, F., Mathematical Theory of Reliability (teorema
    pembaharuan / renewal reward).
  - Rausand & Hoyland, System Reliability Theory (kombinasi RBD).
  - ISO 14224:2016 (definisi MDT dan ketersediaan operasional).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.special import gamma as gamma_fn

from app.config.defaults import Config
from app.core.data_loader import OrderData
from app.core.fs_mapping import RBD_STAGES, fs_name, rbd_tags
from app.core.rbd import EquipmentParams

#: Jumlah titik integrasi L(tau) = integral_0^tau R(t)dt.
_NQUAD = 128


# ==========================================================================
# 1. Penurunan biaya Cp / Cf per tag dari berkas Order
# ==========================================================================
@dataclass
class CostModel:
    """Biaya preventif & korektif per tag beserta jejak asal-usulnya."""

    by_tag: Dict[str, Dict[str, float]] = field(default_factory=dict)
    global_cp: float = 0.0
    global_cf: float = 0.0
    n_orders: int = 0
    n_matched: int = 0
    n_corrective: int = 0
    n_preventive: int = 0
    fallback_map: Dict[str, str] = field(default_factory=dict)
    currency: str = "IDR"
    notes: List[str] = field(default_factory=list)


def derive_costs(
    od: OrderData,
    notif_type_by_id: Mapping[str, str],
    *,
    fail_types: Sequence[str] = ("M1", "M2"),
    pm_type: str = "M3",
) -> CostModel:
    """Agregasi biaya SAP menjadi Cp/Cf per tag.

    Penggolongan korektif vs preventif dilakukan dua tahap:

    1. UTAMA: tautan ke notifikasi. Kolom `Notification` pada order
       dicocokkan dengan berkas notifikasi; jenisnya (M1/M2 = korektif,
       M3 = preventif) memakai taksonomi yang SAMA dengan seluruh analisis
       keandalan, sehingga definisinya konsisten (ISO 14224).
    2. CADANGAN: untuk order tanpa tautan, dipelajari peta
       MaintActivType -> jenis dominan DARI BERKAS ITU SENDIRI (bukan kode
       SAP yang di-hard-code), lalu diterapkan pada sisanya.

    Biaya memakai `Total act.costs` bila terisi, selain itu `TotalPlnndCosts`
    (pada ekspor SAP biaya aktual sering baru terisi setelah order ditutup).
    """
    df = od.df.copy()
    cm = CostModel(n_orders=int(len(df)))
    if df.empty:
        cm.notes.append("Berkas Order tidak memuat baris untuk unit ini.")
        return cm

    # Biaya efektif per order.
    cost = df["actual_cost"].where(df["actual_cost"] > 0, df["planned_cost"])
    df["cost_eff"] = pd.to_numeric(cost, errors="coerce").fillna(0.0)

    # --- Tahap 1: tautan notifikasi ---
    ntype = df["notification"].map(lambda x: notif_type_by_id.get(str(x)) if pd.notna(x) else None)
    df["notif_type"] = ntype
    matched = ntype.notna()
    cm.n_matched = int(matched.sum())

    def to_kind(t: Optional[str]) -> Optional[str]:
        if t is None or (isinstance(t, float) and np.isnan(t)):
            return None
        if t in fail_types:
            return "korektif"
        if t == pm_type:
            return "preventif"
        return None

    df["kind"] = df["notif_type"].map(to_kind)

    # --- Tahap 2: peta cadangan dari MaintActivType (dipelajari dari data) ---
    known = df[df["kind"].notna() & df["maint_act_type"].notna()]
    if not known.empty:
        for mat, grp in known.groupby("maint_act_type"):
            vc = grp["kind"].value_counts()
            if len(vc):
                cm.fallback_map[str(mat)] = str(vc.index[0])
    unknown = df["kind"].isna() & df["maint_act_type"].notna()
    if unknown.any() and cm.fallback_map:
        df.loc[unknown, "kind"] = df.loc[unknown, "maint_act_type"].map(
            lambda m: cm.fallback_map.get(str(m))
        )

    valid = df[df["kind"].notna() & (df["cost_eff"] > 0)]
    cm.n_corrective = int((df["kind"] == "korektif").sum())
    cm.n_preventive = int((df["kind"] == "preventif").sum())

    if valid.empty:
        cm.notes.append(
            "Tidak ada order dengan biaya > 0 yang dapat digolongkan; rasio biaya default dipakai."
        )
        return cm

    corr = valid[valid["kind"] == "korektif"]["cost_eff"]
    prev = valid[valid["kind"] == "preventif"]["cost_eff"]
    cm.global_cf = float(corr.mean()) if len(corr) else 0.0
    cm.global_cp = float(prev.mean()) if len(prev) else 0.0

    # Rasio populasi Cf/Cp: dipakai untuk IMPUTASI bila satu sisi biaya kosong.
    global_ratio = (cm.global_cf / cm.global_cp) if cm.global_cp > 0 else 0.0

    for tag, grp in valid.groupby("tag"):
        c = grp[grp["kind"] == "korektif"]["cost_eff"]
        p = grp[grp["kind"] == "preventif"]["cost_eff"]
        has_c, has_p = len(c) > 0, len(p) > 0
        cf = float(c.mean()) if has_c else 0.0
        cp = float(p.mean()) if has_p else 0.0

        # IMPUTASI yang mempertahankan SKALA biaya tag dan RASIO populasi.
        # Mencampur Cp spesifik-tag dengan Cf global menghasilkan rasio yang
        # tidak masuk akal (mis. Cp 96 ribu vs Cf 83 juta -> 862:1) sehingga
        # optimasi interval akan terdorong ke perawatan berlebih. Karena itu
        # sisi yang kosong diturunkan dari sisi yang ada memakai rasio populasi.
        source = "keduanya dari order"
        if has_c and not has_p:
            cp = cf / global_ratio if global_ratio > 0 else cm.global_cp
            source = "Cf dari order; Cp diimputasi dari rasio populasi"
        elif has_p and not has_c:
            cf = cp * global_ratio if global_ratio > 0 else cm.global_cf
            source = "Cp dari order; Cf diimputasi dari rasio populasi"

        if cf <= 0 or cp <= 0:
            continue
        ratio = cf / cp if cp > 0 else 0.0
        # Rasio sangat tinggi yang bersandar pada sedikit order akan mendorong
        # tau* ke batas bawah (perawatan berlebih). Ditandai agar UI dapat
        # memperingatkan pengguna, bukan disembunyikan.
        extreme = bool(ratio > 50.0 and min(len(c), len(p)) < 5)
        cm.by_tag[str(tag)] = {
            "cp": cp, "cf": cf, "rasio": ratio,
            "n_korektif": int(len(c)), "n_preventif": int(len(p)),
            "biaya_korektif_total": float(c.sum()) if has_c else 0.0,
            "biaya_preventif_total": float(p.sum()) if has_p else 0.0,
            "asal": source,
            "rasio_ekstrem": extreme,
        }

    cm.notes.append(
        f"{cm.n_matched} dari {cm.n_orders} order tertaut langsung ke notifikasi; "
        f"sisanya digolongkan lewat peta MaintActivType yang dipelajari dari berkas ini."
    )
    if cm.global_cp > 0:
        # Koma sebagai pemisah desimal (kaidah penulisan Indonesia), seragam
        # dengan pemformatan angka di seluruh antarmuka.
        rasio = f"{cm.global_cf / cm.global_cp:.2f}".replace(".", ",")
        cm.notes.append(f"Rasio biaya rata-rata Cf/Cp = {rasio} (default MATLAB = 10).")
    n_ext = sum(1 for v in cm.by_tag.values() if v.get("rasio_ekstrem"))
    if n_ext:
        ext = [t for t, v in cm.by_tag.items() if v.get("rasio_ekstrem")]
        cm.notes.append(
            f"{n_ext} tag memiliki rasio Cf/Cp sangat tinggi (>50) yang bersandar pada "
            f"sedikit order: {', '.join(sorted(ext)[:6])}. Interval optimalnya akan "
            "terdorong ke batas bawah; tinjau kembali biaya aktual sebelum dipakai "
            "sebagai dasar keputusan."
        )
    return cm


# ==========================================================================
# 2. Model kebijakan: tau -> biaya & ketersediaan
# ==========================================================================
def _cycle_length(beta: float, eta: float, tau: np.ndarray) -> np.ndarray:
    """L(tau) = integral_0^tau exp(-(t/eta)^beta) dt, tervektorisasi atas tau."""
    # Grid 0..tau untuk setiap tau sekaligus (tau: shape (n,)).
    u = np.linspace(0.0, 1.0, _NQUAD)                 # (_NQUAD,)
    t = tau[:, None] * u[None,:]                     # (n, _NQUAD)
    with np.errstate(over="ignore", under="ignore"):
        r = np.exp(-((t / eta) ** beta))
    return np.trapezoid(r, t, axis=1)


def policy_metrics(
    beta: float, eta: float, mdt: float, cp: float, cf: float, tau_hours: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Biaya per jam, laju kegagalan efektif, dan A_op untuk deret interval tau.

    Mengembalikan (cost_rate, lambda_eff, a_op) masing-masing sebentuk tau.
    """
    tau = np.asarray(tau_hours, dtype=float)
    tau = np.clip(tau, 1e-6, None)
    L = np.maximum(_cycle_length(beta, eta, tau), 1e-12)
    with np.errstate(over="ignore", under="ignore"):
        r_tau = np.exp(-((tau / eta) ** beta))
    cost_rate = (cp * r_tau + cf * (1.0 - r_tau)) / L
    lam = (1.0 - r_tau) / L
    mtbf_eff = np.where(lam > 0, 1.0 / np.maximum(lam, 1e-300), np.inf)
    a_op = np.where(np.isfinite(mtbf_eff), mtbf_eff / (mtbf_eff + mdt), 1.0)
    return cost_rate, lam, a_op


def _stage_availability(st, a_by_tag: Mapping[str, float]) -> float:
    """A_op satu stage: seri memakai perkalian, paralel memakai 1 - prod(1-Ai)."""
    if not st.tags:
        return 1.0
    if st.typ == "ser":
        s = 1.0
        for tg in st.tags:
            s *= a_by_tag.get(tg, 1.0)
        return s
    p = 1.0
    for tg in st.tags:
        p *= 1.0 - a_by_tag.get(tg, 1.0)
    return 1.0 - p


def _system_availability(a_by_tag: Mapping[str, float]) -> float:
    """A_op sistem CDU dari A_op tiap tag, mengikuti struktur RBD seri-paralel."""
    total = 1.0
    for fs in (1, 2, 3):
        for st in RBD_STAGES:
            if st.fs == fs:
                total *= _stage_availability(st, a_by_tag)
    return total


def _fs_availability(fs: int, a_by_tag: Mapping[str, float]) -> float:
    """A_op satu Functional System saja."""
    a = 1.0
    for st in RBD_STAGES:
        if st.fs == fs:
            a *= _stage_availability(st, a_by_tag)
    return a


def _selection_availability(tags: Sequence[str], a_by_tag: Mapping[str, float]) -> float:
    """A_op gabungan sekumpulan tag pilihan, memakai tipe stage masing-masing.

    Tag pada stage paralel yang sama digabung redundan, sisanya seri. Sama
    dengan logika `rbd.selection_availability` sehingga angka yang muncul di
    halaman RBD dan halaman optimasi biaya konsisten.
    """
    sisa = set(tags)
    a = 1.0
    for st in RBD_STAGES:
        dipilih = [t for t in st.tags if t in sisa]
        if not dipilih:
            continue
        sisa.difference_update(dipilih)
        if st.typ == "ser" or len(dipilih) == 1:
            for tg in dipilih:
                a *= a_by_tag.get(tg, 1.0)
        else:
            p = 1.0
            for tg in dipilih:
                p *= 1.0 - a_by_tag.get(tg, 1.0)
            a *= 1.0 - p
    for tg in sorted(sisa):
        a *= a_by_tag.get(tg, 1.0)
    return a


# ==========================================================================
# 3. Optimasi NSGA-II
# ==========================================================================
@dataclass
class OptimizationResult:
    variables: List[str]
    pareto: List[Dict[str, Any]]
    baseline: Dict[str, Any]
    tradeoff: Dict[str, Any]
    config: Dict[str, Any]
    cost_source: Dict[str, Any]
    scope: Dict[str, Any] = field(default_factory=dict)


def _candidates_for_scope(
    eq: Mapping[str, EquipmentParams],
    scope: str,
    fs: Optional[int],
    tags: Optional[Sequence[str]],
) -> Tuple[List[str], str]:
    """Daftar variabel keputusan dan labelnya menurut lingkup analisis.

    Hanya peralatan dengan riwayat kegagalan yang menjadi variabel, karena
    peralatan tanpa kegagalan tidak memiliki parameter Weibull yang dapat
    dioptimasi (R = 1 dan A = 1 pada seluruh interval).
    """
    def punya_riwayat(t: str) -> bool:
        return t in eq and not eq[t].never_failed

    if scope == "fs":
        if fs not in (1, 2, 3):
            raise ValueError("Lingkup 'fs' memerlukan nomor Functional System 1, 2, atau 3.")
        kandidat = [t for st in RBD_STAGES if st.fs == fs for t in st.tags if punya_riwayat(t)]
        return kandidat, fs_name(fs)

    if scope == "equipment":
        if not tags:
            raise ValueError("Lingkup 'equipment' memerlukan minimal satu tag peralatan.")
        kandidat = [t for t in tags if punya_riwayat(t)]
        label = tags[0] if len(tags) == 1 else f"{len(kandidat)} peralatan pilihan"
        return kandidat, label

    return [t for t in rbd_tags() if punya_riwayat(t)], "CDU (FS-1 sampai FS-3)"


def optimize_cost_reliability(
    eq: Mapping[str, EquipmentParams],
    cfg: Config,
    *,
    cost_model: Optional[CostModel] = None,
    scope: str = "cdu",
    fs: Optional[int] = None,
    tags: Optional[Sequence[str]] = None,
) -> OptimizationResult:
    """Cari Pareto front biaya vs ketersediaan dengan NSGA-II (Deb et al., 2002).

    `scope` menentukan lingkup analisis:
      'cdu'        seluruh jalur CDU, objektif ketersediaan memakai ketiga FS seri;
      'fs'         satu Functional System, objektif memakai ketersediaan FS itu;
      'equipment'  sekumpulan tag pilihan, objektif memakai gabungan seleksi
                   dengan logika stage masing-masing.
    """
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.operators.sampling.rnd import FloatRandomSampling
    from pymoo.optimize import minimize

    # ---- Variabel keputusan menurut lingkup analisis ----
    candidates, label_lingkup = _candidates_for_scope(eq, scope, fs, tags)
    if not candidates:
        raise ValueError(
            f"Tidak ada peralatan dengan riwayat kegagalan pada lingkup {label_lingkup}, "
            "sehingga optimasi interval tidak dapat dijalankan. Pilih lingkup lain atau "
            "peralatan yang pernah mengalami kegagalan korektif."
        )

    # Fungsi ketersediaan yang menjadi objektif kedua, sesuai lingkup.
    if scope == "fs":
        def _a_sistem(a_by_tag: Mapping[str, float]) -> float:
            return _fs_availability(int(fs), a_by_tag)
    elif scope == "equipment":
        pilihan = list(candidates)

        def _a_sistem(a_by_tag: Mapping[str, float]) -> float:
            return _selection_availability(pilihan, a_by_tag)
    else:
        _a_sistem = _system_availability

    # Biaya per tag (dari Order bila ada, selain itu rasio default cfg.Cp/cfg.Cf).
    cp_v, cf_v, src_v = [], [], []
    for t in candidates:
        if cost_model and t in cost_model.by_tag:
            cp_v.append(cost_model.by_tag[t]["cp"])
            cf_v.append(cost_model.by_tag[t]["cf"])
            src_v.append("order")
        elif cost_model and cost_model.global_cp > 0 and cost_model.global_cf > 0:
            cp_v.append(cost_model.global_cp)
            cf_v.append(cost_model.global_cf)
            src_v.append("order (rata-rata)")
        else:
            cp_v.append(float(cfg.cp))
            cf_v.append(float(cfg.cf))
            src_v.append("default")
    cp_arr = np.asarray(cp_v, dtype=float)
    cf_arr = np.asarray(cf_v, dtype=float)

    betas = np.asarray([eq[t].beta for t in candidates], dtype=float)
    etas = np.asarray([eq[t].eta for t in candidates], dtype=float)
    mdts = np.asarray([eq[t].mdt for t in candidates], dtype=float)

    lo = float(cfg.ga_tau_min_days) * 24.0
    hi = float(cfg.ga_tau_max_days) * 24.0
    n_var = len(candidates)

    # Tag jalur RBD yang tidak dioptimasi (tak pernah gagal) -> A = 1 tetap.
    fixed_a = {t: eq[t].a_op for t in rbd_tags() if t in eq and eq[t].never_failed}

    class CostReliabilityProblem(Problem):
        """f1 = biaya tahunan (min); f2 = -A_op sistem (agar maksimasi)."""

        def __init__(self) -> None:
            super().__init__(n_var=n_var, n_obj=2, n_ieq_constr=0,
                             xl=np.full(n_var, lo), xu=np.full(n_var, hi))

        def _evaluate(self, X, out, *args, **kwargs):  # noqa: ANN001
            n_pop = X.shape[0]
            total_cost = np.zeros(n_pop, dtype=float)
            a_mat = np.ones((n_pop, n_var), dtype=float)
            for j in range(n_var):
                c_rate, _lam, a_op = policy_metrics(
                    betas[j], etas[j], mdts[j], cp_arr[j], cf_arr[j], X[:, j]
                )
                total_cost += 8760.0 * c_rate
                a_mat[:, j] = a_op
            a_sys = np.empty(n_pop, dtype=float)
            for i in range(n_pop):
                a_by_tag = dict(fixed_a)
                a_by_tag.update({candidates[j]: a_mat[i, j] for j in range(n_var)})
                a_sys[i] = _a_sistem(a_by_tag)
            out["F"] = np.column_stack([total_cost, -a_sys])

    algorithm = NSGA2(
        pop_size=int(cfg.ga_pop_size),
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=float(cfg.ga_crossover_prob), eta=15),
        mutation=PM(eta=float(cfg.ga_mutation_eta)),
        eliminate_duplicates=True,
    )
    result = minimize(
        CostReliabilityProblem(), algorithm, ("n_gen", int(cfg.ga_generations)),
        seed=int(cfg.ga_seed), verbose=False, save_history=False,
    )

    # ---- Garis dasar: run-to-failure (kebijakan saat ini) ----
    base_cost = 0.0
    base_a: Dict[str, float] = dict(fixed_a)
    for j, t in enumerate(candidates):
        mttf = etas[j] * float(gamma_fn(1.0 + 1.0 / betas[j]))
        base_cost += 8760.0 * cf_arr[j] / mttf
        base_a[t] = eq[t].a_op
    base_a_sys = _a_sistem(base_a)
    baseline = {
        "kebijakan": "Run to failure (kebijakan saat ini)",
        "biaya_tahunan": float(base_cost),
        "a_op_sistem": float(base_a_sys),
        "downtime_hari_thn": float((1.0 - base_a_sys) * 365.0),
    }

    # ---- Susun Pareto front ----
    F = np.atleast_2d(result.F)
    X = np.atleast_2d(result.X)
    order = np.argsort(F[:, 0])
    pareto: List[Dict[str, Any]] = []
    for rank, i in enumerate(order):
        cost = float(F[i, 0])
        a_sys = float(-F[i, 1])
        intervals = [
            {
                "tag": candidates[j],
                "tau_hari": round(float(X[i, j]) / 24.0, 1),
                "beta": round(float(betas[j]), 3),
                "eta_jam": round(float(etas[j]), 0),
                "mdt_jam": float(mdts[j]),
                "sumber_biaya": src_v[j],
                "cp": float(cp_arr[j]),
                "cf": float(cf_arr[j]),
            }
            for j in range(n_var)
        ]
        intervals.sort(key=lambda d: d["tau_hari"])
        pareto.append(
            {
                "id": rank,
                "biaya_tahunan": cost,
                "a_op_sistem": a_sys,
                "downtime_hari_thn": (1.0 - a_sys) * 365.0,
                "delta_biaya_pct": ((cost / base_cost - 1.0) * 100.0) if base_cost > 0 else None,
                "delta_availability": a_sys - base_a_sys,
                "interval": intervals,
            }
        )

    # ---- Kurva trade-off satu peralatan (untuk grafik §7.2) ----
    # Dipilih peralatan penyumbang waktu henti tahunan terbesar
    # (downtime/thn = gagal/thn x MDT), karena di situlah trade-off paling nyata.
    downtime_year = [(8760.0 / eq[t].mtbf) * eq[t].mdt for t in candidates]
    worst = int(np.argmax(downtime_year))
    tg = candidates[worst]
    tau_grid = np.linspace(lo, hi, 160)
    c_rate, lam, a_op = policy_metrics(
        betas[worst], etas[worst], mdts[worst], cp_arr[worst], cf_arr[worst], tau_grid
    )
    k = int(np.argmin(c_rate))
    tradeoff = {
        "tag": tg,
        "beta": float(betas[worst]),
        "tau_hari": (tau_grid / 24.0).tolist(),
        "biaya_tahunan": (8760.0 * c_rate).tolist(),
        "a_op": a_op.tolist(),
        "gagal_per_thn": (8760.0 * lam).tolist(),
        "tau_opt_hari": float(tau_grid[k] / 24.0),
        "biaya_opt": float(8760.0 * c_rate[k]),
        "a_op_opt": float(a_op[k]),
    }

    return OptimizationResult(
        variables=candidates,
        pareto=pareto,
        baseline=baseline,
        tradeoff=tradeoff,
        config={
            "pop_size": cfg.ga_pop_size,
            "generations": cfg.ga_generations,
            "crossover_prob": cfg.ga_crossover_prob,
            "mutation_eta": cfg.ga_mutation_eta,
            "seed": cfg.ga_seed,
            "tau_min_hari": cfg.ga_tau_min_days,
            "tau_max_hari": cfg.ga_tau_max_days,
            "n_var": n_var,
            "algoritma": "NSGA-II (Deb et al., 2002) via pymoo",
        },
        cost_source={
            "tersedia": bool(cost_model and cost_model.by_tag),
            "n_tag_berbiaya": len(cost_model.by_tag) if cost_model else 0,
            "cp_global": cost_model.global_cp if cost_model else None,
            "cf_global": cost_model.global_cf if cost_model else None,
            "catatan": cost_model.notes if cost_model else [],
            "mata_uang": cost_model.currency if cost_model else "IDR",
        },
        scope={
            "jenis": scope,
            "label": label_lingkup,
            "fs": fs,
            "tags": list(tags) if tags else None,
            "objektif_ketersediaan": {
                "cdu": "A_op gabungan FS-1, FS-2, dan FS-3 secara seri",
                "fs": f"A_op {label_lingkup} saja",
                "equipment": "A_op gabungan peralatan terpilih menurut tipe stage masing-masing",
            }[scope],
        },
    )
