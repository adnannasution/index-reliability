"""
Optimasi interval pemeliharaan preventif: kebijakan age replacement (modul G).

Model biaya jangka panjang (Barlow & Hunter, 1960):

        Cp * R(tau) + Cf * (1 - R(tau))
 C(tau) = --------------------------------
             integral_0^tau R(t) dt

Pembilang = ekspektasi biaya satu siklus (diganti terjadwal dengan biaya Cp
bila bertahan sampai tau, atau gagal dengan biaya Cf bila tidak). Penyebut =
ekspektasi panjang siklus. Minimum atas tau memberi interval optimal tau*.

Pembanding run-to-failure: C_rtf = Cf / MTTF, MTTF = eta * Gamma(1 + 1/beta).

Ref:
  - Barlow, R.E. & Hunter, L.C. (1960), "Optimum Preventive Maintenance
    Policies", Operations Research 8(1), 90-100.
  - Jardine, A.K.S. & Tsang, A.H.C., Maintenance, Replacement, and Reliability:
    Theory and Applications, bab 2 (optimasi interval penggantian).

Port dari `pmOptimize()` MATLAB (baris 1928-1940). Grid dan jumlah titik
integrasi dipertahankan persis agar tau* dapat direproduksi.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
from scipy.special import gamma as gamma_fn

from app.core.rbd import EquipmentParams
from app.core.reliability import MATLAB_EPS, pm_verdict


@dataclass
class PMOptimum:
    """Hasil optimasi interval untuk satu peralatan."""

    tau_opt_hours: float
    cost_opt: float
    cost_rtf: float
    tau_grid: List[float]
    cost_grid: List[float]

    @property
    def tau_opt_days(self) -> float:
        return self.tau_opt_hours / 24.0

    @property
    def saving_pct(self) -> float:
        """Penghematan (%) kebijakan optimal terhadap run-to-failure, BERTANDA.

        Ini nilai mentah modul G MATLAB: round((1 - Copt/Crtf)*100, 1).
        Nilai <= 0 berarti kurva biaya datar atau menanjak sehingga penggantian
        terjadwal justru lebih mahal daripada run-to-failure: lazim ketika
        beta <= 1 (tidak ada mekanisme aus yang dapat dicegah oleh jadwal).
        Laporan menuliskannya sebagai "0 persen" karena tidak ada penghematan
        yang dapat direalisasikan; gunakan `saving_pct_effective` untuk itu.
        """
        if not np.isfinite(self.cost_rtf) or self.cost_rtf <= 0:
            return 0.0
        return float((1.0 - self.cost_opt / self.cost_rtf) * 100.0)

    @property
    def saving_pct_effective(self) -> float:
        """Penghematan yang dapat direalisasikan: port modul J: max(0, ...).

        Dipakai mesin pemilihan strategi (chooseStrategy) dan penyajian ke
        pengguna, karena penghematan negatif berarti "jangan dijadwalkan",
        bukan "biaya bertambah bila tidak melakukan apa-apa".
        """
        return max(0.0, self.saving_pct)


def pm_optimize(beta: float, eta: float, cp: float, cf: float) -> PMOptimum:
    """Interval optimal age-replacement: port `pmOptimize()` (baris 1928).

    Grid tau = linspace(0.05*eta, 3*eta, 300); integral trapesium 150 titik,
    sama persis dengan MATLAB sehingga tau* dapat dibandingkan langsung.
    """
    if not np.isfinite(eta) or eta <= 0:
        eta = 1e5
    if not np.isfinite(beta) or beta <= 0:
        beta = 1.0

    tau_grid = np.linspace(eta * 0.05, eta * 3.0, 300)
    cost = np.empty_like(tau_grid)
    for i, tau in enumerate(tau_grid):
        tt = np.linspace(0.0, tau, 150)
        r_tt = np.exp(-((tt / eta) ** beta))
        denom = max(float(np.trapezoid(r_tt, tt)), MATLAB_EPS)
        r_tau = math.exp(-((tau / eta) ** beta))
        cost[i] = (cp * r_tau + cf * (1.0 - r_tau)) / denom

    k = int(np.argmin(cost))
    c_rtf = cf / (eta * float(gamma_fn(1.0 + 1.0 / beta)))
    return PMOptimum(
        tau_opt_hours=float(tau_grid[k]),
        cost_opt=float(cost[k]),
        cost_rtf=float(c_rtf),
        tau_grid=tau_grid.tolist(),
        cost_grid=cost.tolist(),
    )


def bad_actor_per_fs(
    tags: Sequence[str], n_cm: Mapping[str, int], fs_of_tag: Mapping[str, int]
) -> Dict[int, Optional[str]]:
    """Peralatan bermasalah utama tiap FS: port `[~,ix] = max(nCM .* sel)`.

    MATLAB `max` mengembalikan indeks PERTAMA pada nilai maksimum, dengan tag
    terurut menaik. Perilaku itu ditiru di sini (urut tag lalu ambil yang
    pertama) sehingga pemilihan bad actor identik saat terjadi seri nilai.
    """
    out: Dict[int, Optional[str]] = {}
    ordered = sorted(tags)
    for f in (1, 2, 3):
        best, best_n = None, -1
        for t in ordered:
            if fs_of_tag.get(t) != f:
                continue
            k = int(n_cm.get(t, 0))
            if k > best_n:
                best, best_n = t, k
        out[f] = best if best_n > 0 else None
    return out


def optimize_module_g(
    eq: Mapping[str, EquipmentParams],
    tags: Sequence[str],
    n_cm: Mapping[str, int],
    fs_of_tag: Mapping[str, int],
    *,
    cp: float,
    cf: float,
    cost_by_tag: Optional[Mapping[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Modul G: optimasi interval PM untuk bad actor tiap Functional System.

    Bila `cost_by_tag` tersedia (dari berkas Order), Cp/Cf per tag memakai
    biaya riil SAP; selain itu memakai rasio default cfg.Cp / cfg.Cf.
    """
    from app.core.fs_mapping import fs_name

    targets = bad_actor_per_fs(tags, n_cm, fs_of_tag)
    rows: List[Dict[str, Any]] = []
    curves: List[Dict[str, Any]] = []

    for f in (1, 2, 3):
        tg = targets[f]
        if tg is None or tg not in eq:
            continue
        e = eq[tg]
        c_p, c_f, src = cp, cf, "rasio default"
        if cost_by_tag and tg in cost_by_tag:
            c = cost_by_tag[tg]
            if c.get("cp", 0) > 0 and c.get("cf", 0) > 0:
                c_p, c_f, src = float(c["cp"]), float(c["cf"]), "biaya SAP (Order)"

        opt = pm_optimize(e.beta, e.eta, c_p, c_f)
        rows.append(
            {
                "sistem": fs_name(f),
                "bad_actor": tg,
                "beta": round(float(e.beta), 2),
                "eta_jam": round(float(e.eta), 0) if np.isfinite(e.eta) else None,
                "tau_opt_hari": round(opt.tau_opt_days, 0),
                "penghematan_pct": round(opt.saving_pct, 1),
                "penghematan_efektif_pct": round(opt.saving_pct_effective, 1),
                "cp": c_p,
                "cf": c_f,
                "sumber_biaya": src,
                "rekomendasi": pm_verdict(float(e.beta)),
            }
        )
        # Kurva untuk grafik: disubsampel agar payload JSON ringan.
        step = max(1, len(opt.tau_grid) // 150)
        curves.append(
            {
                "sistem": fs_name(f),
                "tag": tg,
                "beta": float(e.beta),
                "tau_hari": [t / 24.0 for t in opt.tau_grid[::step]],
                "laju_biaya": opt.cost_grid[::step],
                "tau_opt_hari": opt.tau_opt_days,
                "biaya_opt": opt.cost_opt,
                "biaya_rtf": opt.cost_rtf,
            }
        )
    return {"tabel": rows, "kurva": curves}
