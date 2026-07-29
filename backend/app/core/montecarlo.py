"""
Simulasi Monte Carlo ketersediaan tingkat SISTEM (modul F): RBD-aware.

Tiap peralatan pada jalur RBD disimulasikan sepanjang satu tahun operasi:
  * waktu menuju kegagalan (TTF) ~ Weibull(beta, eta) peralatan itu sendiri;
  * durasi perbaikan (TTR) ~ lognormal dengan RERATA sama dengan MDT tag;
  * garis waktu naik/turun digabung mengikuti logika seri dan paralel RBD,
    jam demi jam, lalu ketersediaan tahunan dihitung sebagai fraksi jam
    sistem dalam kondisi operasi.

Pengambilan sampel Weibull memakai metode inversi:
    TTF = eta * (-ln U)^(1/beta),  U ~ Uniform(0,1)
Durasi perbaikan memakai exp(sigma*Z - sigma^2/2) sehingga E[TTR] = MDT
(faktor koreksi -sigma^2/2 membuat rerata lognormal tepat sama dengan 1).

Ref:
  - Rausand, M. & Hoyland, A., System Reliability Theory, bab simulasi.
  - Zio, E., The Monte Carlo Simulation Method for System Reliability and
    Risk Analysis.
  - ISO 14224:2016 untuk definisi MDT/downtime.

Port dari `mcSystem()` / `simUp()` MATLAB (baris 1595-1644). Seed diset agar
hasil reprodusibel (§10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

import numpy as np

from app.core.fs_mapping import RBD_STAGES, fs_name, rbd_tags
from app.core.rbd import EquipmentParams
from app.core.reliability import pctl

#: Sigma lognormal durasi perbaikan (nilai MATLAB `sig = 0.4`).
REPAIR_SIGMA = 0.4


def _sim_up(
    e: EquipmentParams, horizon: float, dt: float, n: int, rng: np.random.Generator
) -> np.ndarray:
    """Garis waktu naik/turun satu peralatan: port `simUp()` (baris 1628).

    Mengembalikan larik boolean panjang `n`; True = beroperasi.
    Peralatan yang tak pernah gagal (n_CM = 0) selalu True, persis MATLAB.
    """
    up = np.ones(n, dtype=bool)
    if e.never_failed:
        return up

    t = 0.0
    while t < horizon:
        # TTF Weibull melalui inversi (identik e.eta*(-log(rand))^(1/e.beta)).
        t += e.eta * (-np.log(rng.random())) ** (1.0 / e.beta)
        if t >= horizon:
            break
        ttr = max(dt, e.mdt * float(np.exp(REPAIR_SIGMA * rng.standard_normal()
                                           - REPAIR_SIGMA**2 / 2.0)))
        i1 = max(1, int(np.floor(t / dt)) + 1)
        i2 = min(n, int(np.floor((t + ttr) / dt)))
        if i2 >= i1:
            up[i1 - 1:i2] = False   # MATLAB 1-based -> Python 0-based
        t += ttr
    return up


@dataclass
class MonteCarloResult:
    table: List[Dict[str, Any]]
    #: sampel ketersediaan tahunan per replikasi (untuk histogram)
    samples: Dict[str, List[float]]
    reps: int
    horizon_hours: float
    seed: int


def mc_system(
    eq: Mapping[str, EquipmentParams],
    *,
    reps: int = 400,
    horizon: float = 8760.0,
    dt: float = 1.0,
    seed: int = 7,
    a_op_analytic: Mapping[str, float] | None = None,
) -> MonteCarloResult:
    """Jalankan simulasi Monte Carlo sistem: port `mcSystem()` (baris 1595)."""
    n = int(round(horizon / dt))
    rng = np.random.default_rng(seed)
    all_tags = rbd_tags()

    a_fs = np.zeros((reps, 3), dtype=float)
    a_cdu = np.zeros(reps, dtype=float)

    for r in range(reps):
        ups: Dict[str, np.ndarray] = {}
        for tg in all_tags:
            e = eq.get(tg)
            if e is None:
                ups[tg] = np.ones(n, dtype=bool)
            else:
                ups[tg] = _sim_up(e, horizon, dt, n, rng)

        fs_up = np.ones((3, n), dtype=bool)
        for st in RBD_STAGES:
            if not st.tags:
                continue
            if st.typ == "ser":
                blk = np.ones(n, dtype=bool)
                for tg in st.tags:
                    blk &= ups[tg]
            else:
                blk = np.zeros(n, dtype=bool)
                for tg in st.tags:
                    blk |= ups[tg]
            fs_up[st.fs - 1] &= blk

        a_fs[r,:] = fs_up.mean(axis=1)
        a_cdu[r] = float(np.all(fs_up, axis=0).mean())

    table: List[Dict[str, Any]] = []
    samples: Dict[str, List[float]] = {}
    for i in range(3):
        col = a_fs[:, i]
        name = fs_name(i + 1)
        samples[name] = col.tolist()
        table.append(_row(name, col, a_op_analytic.get(name) if a_op_analytic else None))
    samples["CDU"] = a_cdu.tolist()
    table.append(_row("CDU total", a_cdu, a_op_analytic.get("CDU") if a_op_analytic else None))

    return MonteCarloResult(
        table=table, samples=samples, reps=reps, horizon_hours=horizon, seed=seed
    )


def _row(name: str, col: np.ndarray, a_op: float | None) -> Dict[str, Any]:
    mean = float(col.mean())
    return {
        "sistem": name,
        "a_mean": round(mean, 4),
        "a_p10": round(pctl(col, 10), 4),
        "a_p50": round(pctl(col, 50), 4),
        "a_p90": round(pctl(col, 90), 4),
        # Waktu henti tahunan pada skenario P10 (dipakai untuk buffer & spare).
        "downtime_hari_thn": round((1.0 - mean) * 8760.0 / 24.0, 1),
        "downtime_p10_hari_thn": round((1.0 - pctl(col, 10)) * 365.0, 1),
        "a_op_analitik": round(a_op, 4) if a_op is not None else None,
    }
