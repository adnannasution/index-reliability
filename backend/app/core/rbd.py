"""
Reliability Block Diagram seri-paralel: port dari CDU_PdM_Balongan.m (modul E).

Rumus inti (Ref: Rausand, M. & Hoyland, A., System Reliability Theory:
Models, Statistical Methods, and Applications, 2nd ed., bab 4):
    stage SERI   : R(t) = prod_i R_i(t)
    stage PARALEL: R(t) = 1 - prod_i (1 - R_i(t))
    sistem satu FS: R(t) = prod_stage R_stage(t)        (stage tersusun seri)
    CDU total    : R(t) = R_FS1(t) * R_FS2(t) * R_FS3(t)

Ketersediaan (Ref: ISO 14224:2016; Blanchard & Fabrycky, Systems Engineering
and Analysis):
    A_inh = MTBF / (MTBF + MTTR)     ketersediaan inheren   (MTTR per kelas, OREDA)
    A_op  = MTBF / (MTBF + MDT)      ketersediaan operasional (MDT per tag)

Peta fungsi MATLAB -> Python
    eqParams     -> build_equipment_params   (baris 1491-1519)
    eqR / eqA    -> eq_r / eq_a              (baris 1521-1532)
    stageR/stageA-> stage_r / stage_a        (baris 1537-1564)
    rbdR / rbdA  -> rbd_r / rbd_a            (baris 1566-1581)
    fullSeriesR  -> full_series_r            (baris 1583-1590)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np
from scipy.special import gamma as gamma_fn

from app.config.defaults import MTTR_BY_CLASS
from app.core.fs_mapping import RBD_STAGES, Stage, stages_of_fs


@dataclass
class EquipmentParams:
    """Parameter keandalan satu peralatan: setara struct `EQ(tag)` MATLAB."""

    tag: str
    beta: float
    eta: float          # jam; inf bila tak pernah gagal
    mtbf: float         # jam; inf bila tak pernah gagal
    n_cm: int
    a_inh: float
    a_op: float
    mdt: float          # jam
    mttr: float         # jam
    kelas: str

    @property
    def never_failed(self) -> bool:
        return self.n_cm == 0 or not np.isfinite(self.eta)


def build_equipment_params(
    tags: Sequence[str],
    n_cm: Mapping[str, int],
    kelas: Mapping[str, str],
    mdt: Mapping[str, float],
    t_obs: float,
    *,
    beta_source: str,
    beta_by_tag: Optional[Mapping[str, float]] = None,
    beta_by_class: Optional[Mapping[str, float]] = None,
) -> Dict[str, EquipmentParams]:
    """Hitung beta/eta/MTBF/A_inh/A_op tiap tag: port `eqParams()` (baris 1491).

    Sumber beta (cfg.beta_source):
      'equipment' -> beta per-tag hasil modul C3 bila tersedia, selain itu
                     prior kelas;
      'mle'       -> beta MLE per kelas (modul C);
      'workbook'  -> konstanta per kelas (agar sebanding laporan lama).

    eta = MTBF / Gamma(1 + 1/beta) sehingga laju kegagalan teramati tetap
    konsisten; hanya BENTUK kurva yang ditentukan beta.

    Tag dengan n_CM = 0 (mis. unit cadangan yang tak pernah gagal) mendapat
    MTBF = eta = inf dan A = 1: persis MATLAB, sehingga blok redundan yang
    tidak muncul di notifikasi tidak menurunkan keandalan sistem.
    """
    beta_by_tag = beta_by_tag or {}
    beta_by_class = beta_by_class or {}
    use_eq = str(beta_source).lower() == "equipment"

    out: Dict[str, EquipmentParams] = {}
    for tg in tags:
        cc = kelas.get(tg, "other")
        if use_eq and tg in beta_by_tag:
            b = float(beta_by_tag[tg])
        elif cc in beta_by_class:
            b = float(beta_by_class[cc])
        else:
            b = 1.0
        if not np.isfinite(b) or b <= 0:
            b = 1.0

        mt = MTTR_BY_CLASS.get(cc, MTTR_BY_CLASS["other"])
        k = int(n_cm.get(tg, 0))
        d = float(mdt.get(tg, 48.0))

        if k == 0:
            mtbf = float("inf")
            eta = float("inf")
            a_inh = 1.0
            a_op = 1.0
        else:
            mtbf = t_obs / k
            eta = mtbf / float(gamma_fn(1.0 + 1.0 / b))
            a_inh = mtbf / (mtbf + mt)
            a_op = mtbf / (mtbf + d)

        out[tg] = EquipmentParams(
            tag=tg, beta=b, eta=eta, mtbf=mtbf, n_cm=k,
            a_inh=a_inh, a_op=a_op, mdt=d, mttr=mt, kelas=cc,
        )
    return out


# --------------------------------------------------------------------------
# Keandalan & ketersediaan tingkat peralatan
# --------------------------------------------------------------------------
def eq_r(eq: Mapping[str, EquipmentParams], tag: str, t: np.ndarray | float) -> np.ndarray:
    """R(t) satu peralatan: port `eqR()`.

    Tag yang tidak dikenal ATAU tidak pernah gagal -> R = 1 (bukan kegagalan
    data, melainkan bukti bahwa peralatan itu tidak gagal pada jendela ini).
    """
    arr = np.asarray(t, dtype=float)
    e = eq.get(tag)
    if e is None or e.never_failed:
        return np.ones_like(arr)
    with np.errstate(over="ignore", under="ignore"):
        return np.exp(-((arr / e.eta) ** e.beta))


def eq_a(eq: Mapping[str, EquipmentParams], tag: str, which: str = "op") -> float:
    """Ketersediaan satu peralatan: port `eqA()`. 'inh' atau 'op'."""
    e = eq.get(tag)
    if e is None:
        return 1.0
    return e.a_inh if which == "inh" else e.a_op


# --------------------------------------------------------------------------
# Keandalan & ketersediaan tingkat stage / sistem
# --------------------------------------------------------------------------
def stage_r(stage: Stage, eq: Mapping[str, EquipmentParams], t: np.ndarray | float) -> np.ndarray:
    """R(t) satu stage: port `stageR()`. Stage tanpa tag -> R = 1."""
    arr = np.asarray(t, dtype=float)
    if not stage.tags:
        return np.ones_like(arr)
    if stage.typ == "ser":
        r = np.ones_like(arr)
        for tg in stage.tags:
            r = r * eq_r(eq, tg, arr)
        return r
    p = np.ones_like(arr)
    for tg in stage.tags:
        p = p * (1.0 - eq_r(eq, tg, arr))
    return 1.0 - p


def stage_a(stage: Stage, eq: Mapping[str, EquipmentParams], which: str = "inh") -> float:
    """Ketersediaan satu stage: port `stageA()`."""
    if not stage.tags:
        return 1.0
    if stage.typ == "ser":
        a = 1.0
        for tg in stage.tags:
            a *= eq_a(eq, tg, which)
        return a
    p = 1.0
    for tg in stage.tags:
        p *= 1.0 - eq_a(eq, tg, which)
    return 1.0 - p


def rbd_r(eq: Mapping[str, EquipmentParams], fs: int, t: np.ndarray | float) -> np.ndarray:
    """R(t) satu Functional System = perkalian seluruh stage-nya: port `rbdR()`."""
    arr = np.asarray(t, dtype=float)
    r = np.ones_like(arr)
    for s in RBD_STAGES:
        if s.fs == fs:
            r = r * stage_r(s, eq, arr)
    return r


def rbd_a(eq: Mapping[str, EquipmentParams], fs: int, which: str = "inh") -> float:
    """Ketersediaan satu Functional System: port `rbdA()`."""
    a = 1.0
    for s in RBD_STAGES:
        if s.fs == fs:
            a *= stage_a(s, eq, which)
    return a


def cdu_r(eq: Mapping[str, EquipmentParams], t: np.ndarray | float) -> np.ndarray:
    """R(t) gabungan CDU = R_FS1 * R_FS2 * R_FS3 (tiga FS tersusun SERI)."""
    arr = np.asarray(t, dtype=float)
    return rbd_r(eq, 1, arr) * rbd_r(eq, 2, arr) * rbd_r(eq, 3, arr)


def cdu_a(eq: Mapping[str, EquipmentParams], which: str = "inh") -> float:
    """Ketersediaan gabungan CDU = hasil kali ketersediaan ketiga FS."""
    return rbd_a(eq, 1, which) * rbd_a(eq, 2, which) * rbd_a(eq, 3, which)


def full_series_r(
    tags_of_fs: Iterable[str], eq: Mapping[str, EquipmentParams], t: float
) -> float:
    """Batas bawah konservatif: port `fullSeriesR()`.

    SELURUH tag di FS dianggap seri (redundansi diabaikan), termasuk tag yang
    tidak masuk jalur RBD. Berguna sebagai pembanding pesimistis.
    """
    r = 1.0
    for tg in tags_of_fs:
        r *= float(eq_r(eq, tg, float(t)))
    return r


# --------------------------------------------------------------------------
# Seleksi dinamis (fitur §6): gabungan keandalan equipment pilihan pengguna
# --------------------------------------------------------------------------
def selection_r(
    selected: Sequence[str], eq: Mapping[str, EquipmentParams], t: np.ndarray | float
) -> np.ndarray:
    """R(t) gabungan dari sekumpulan tag yang dipilih pengguna pada diagram RBD.

    Logika mengikuti struktur RBD yang sebenarnya, bukan asumsi seragam:
      * tag yang dipilih dikelompokkan menurut stage asalnya;
      * di dalam satu stage, gabungan memakai tipe stage itu (seri / paralel);
      * antar-stage selalu SERI (stage tersusun seri pada jalur proses);
      * tag terpilih yang berada di LUAR jalur RBD diperlakukan sebagai satu
        blok seri tambahan (tidak ada informasi redundansi untuknya).

    Dengan demikian memilih dua pompa A/B pada stage paralel menghasilkan
    redundansi (1-(1-Ra)(1-Rb)), sedangkan memilih F-101 dan C-101 yang berada
    di stage seri berbeda menghasilkan perkalian Ra*Rb.
    """
    arr = np.asarray(t, dtype=float)
    chosen = [s for s in selected if s]
    if not chosen:
        return np.ones_like(arr)

    remaining = set(chosen)
    r = np.ones_like(arr)

    for st in RBD_STAGES:
        picked = [tg for tg in st.tags if tg in remaining]
        if not picked:
            continue
        remaining.difference_update(picked)
        if st.typ == "ser" or len(picked) == 1:
            for tg in picked:
                r = r * eq_r(eq, tg, arr)
        else:
            p = np.ones_like(arr)
            for tg in picked:
                p = p * (1.0 - eq_r(eq, tg, arr))
            r = r * (1.0 - p)

    # Tag di luar jalur RBD -> seri.
    for tg in sorted(remaining):
        r = r * eq_r(eq, tg, arr)
    return r


def selection_availability(
    selected: Sequence[str], eq: Mapping[str, EquipmentParams], which: str = "op"
) -> float:
    """Ketersediaan gabungan seleksi, memakai logika stage yang sama."""
    chosen = [s for s in selected if s]
    if not chosen:
        return 1.0
    remaining = set(chosen)
    a = 1.0
    for st in RBD_STAGES:
        picked = [tg for tg in st.tags if tg in remaining]
        if not picked:
            continue
        remaining.difference_update(picked)
        if st.typ == "ser" or len(picked) == 1:
            for tg in picked:
                a *= eq_a(eq, tg, which)
        else:
            p = 1.0
            for tg in picked:
                p *= 1.0 - eq_a(eq, tg, which)
            a *= 1.0 - p
    for tg in sorted(remaining):
        a *= eq_a(eq, tg, which)
    return a


def stage_of_tag(tag: str) -> Optional[Stage]:
    """Stage RBD tempat sebuah tag berada (None bila di luar jalur)."""
    for st in RBD_STAGES:
        if tag in st.tags:
            return st
    return None


def describe_stages(fs: int) -> List[Stage]:
    """Stage satu FS, untuk membangun diagram di frontend."""
    return stages_of_fs(fs)
