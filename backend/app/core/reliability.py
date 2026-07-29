"""
Mesin estimasi keandalan: port PERSIS dari CDU_PdM_Balongan.m (modul C, C2, C3, D).

Setiap fungsi mencantumkan sumber rumusnya. Tidak ada rumus yang dikarang;
bila terdapat ambiguitas, MATLAB diikuti apa adanya.

Peta fungsi MATLAB -> Python
    weibullMLE / weibullNLL  -> weibull_mle            (baris 1780-1790)
    weibullCI                -> weibull_ci             (baris 1792-1807)
    weibullR2                -> weibull_r2             (baris 1809-1815)
    mrrFit                   -> mrr_fit                (baris 1818-1848)
    mleCens                  -> mle_censored           (baris 1850-1873)
    crowAMSAA                -> crow_amsaa             (baris 1875-1884)
    ufFactor                 -> uf_factor              (baris 1886-1894)
    laplaceTrend             -> laplace_trend          (baris 1922-1926)
    fitBlock                 -> fit_block              (baris 1744-1756)
    ifrRegion                -> ifr_region             (baris 1907-1912)
    pctl                     -> pctl                   (baris 1942-1947)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import erfc, gamma as gamma_fn

#: eps MATLAB (jarak dari 1.0 ke bilangan double berikutnya).
MATLAB_EPS = float(np.finfo(float).eps)


# ==========================================================================
# Penolong umum
# ==========================================================================
def pctl(x: Sequence[float], p: float) -> float:
    """Persentil versi MATLAB skrip ini: port `pctl()` (baris 1942).

    CATATAN: ini BUKAN np.percentile. MATLAB memakai indeks
    ``idx = min(n, max(1, ceil(p/100 * n)))`` pada data terurut (tanpa
    interpolasi). Diport apa adanya agar P10/P50/P90 Monte Carlo identik.
    """
    arr = np.sort(np.asarray(x, dtype=float).ravel())
    n = arr.size
    if n == 0:
        return float("nan")
    idx = min(n, max(1, math.ceil(p / 100.0 * n)))
    return float(arr[idx - 1])


def ifr_region(b: float) -> str:
    """Wilayah laju kegagalan: port `ifrRegion()` (baris 1907)."""
    if not np.isfinite(b):
        return "tidak tersedia"
    if b > 1.1:
        return "Aus (IFR)"
    if b < 0.9:
        return "Dini (DFR)"
    return "Umur guna (CFR)"


def pm_verdict(b: float) -> str:
    """Port `pmVerdict()` (baris 1914)."""
    return "PM berkala efektif" if b > 1.1 else "beta~1: PM berkala kurang berguna"


def uf_factor(m: int) -> float:
    """Faktor unbias MLE beta sampel-kecil: port `ufFactor()` (baris 1886).

    Ref: Thoman, D.R., Bain, L.J. & Antle, C.E. (1969), "Inferences on the
    Parameters of the Weibull Distribution", Technometrics 11(3), 445-460.
    Dikalikan ke beta_MLE untuk mengoreksi bias positif pada sampel kecil.
    """
    ks = np.array([2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 30, 50, 100], dtype=float)
    vs = np.array(
        [0.549, 0.686, 0.766, 0.815, 0.848, 0.872, 0.891, 0.905, 0.916,
         0.933, 0.949, 0.962, 0.975, 0.985, 0.992],
        dtype=float,
    )
    if m <= ks[0]:
        return float(vs[0])
    if m >= ks[-1]:
        return 1.0
    return float(np.interp(float(m), ks, vs))


# ==========================================================================
# Weibull 2 parameter: sampel LENGKAP (modul C / C2)
# ==========================================================================
def _weibull_nll(b: float, x: np.ndarray) -> float:
    """Negatif log-likelihood Weibull dengan eta ter-profil: port `weibullNLL`.

    eta(b) = (mean(x^b))^(1/b) adalah MLE eta untuk b tertentu, sehingga
    optimasi menjadi satu dimensi atas b saja.
    """
    n = x.size
    with np.errstate(over="ignore", invalid="ignore"):
        eta = float(np.mean(x**b) ** (1.0 / b))
        if not np.isfinite(eta) or eta <= 0:
            return float("inf")
        val = (
            n * math.log(b)
            - n * b * math.log(eta)
            + (b - 1.0) * float(np.sum(np.log(x)))
            - float(np.sum((x / eta) ** b))
        )
    return -val if np.isfinite(val) else float("inf")


def weibull_mle(x: Sequence[float]) -> Tuple[float, float]:
    """MLE Weibull sampel lengkap: port `weibullMLE()` (baris 1780).

    MATLAB memakai fminbnd pada b di [0.3, 6]; di sini dipakai
    scipy.optimize.minimize_scalar(method='bounded') dengan batas sama.
    Ref: Nelson, W. (1982), Applied Life Data Analysis, Wiley.
    """
    arr = np.asarray(x, dtype=float).ravel()
    arr = arr[arr > 0]
    if arr.size == 0:
        return float("nan"), float("nan")
    res = minimize_scalar(
        _weibull_nll, bounds=(0.3, 6.0), args=(arr,), method="bounded",
        options={"xatol": 1e-10},
    )
    b = float(res.x)
    eta = float(np.mean(arr**b) ** (1.0 / b))
    return b, eta


def _weibull_acov(a: float, b: float, x: np.ndarray) -> Optional[np.ndarray]:
    """Kovarians asimtotik MLE Weibull dari matriks informasi teramati.

    Parameterisasi MATLAB wblfit: a = skala (eta), b = bentuk (beta).
        logL = n ln b - n b ln a + (b-1) sum(ln x) - sum((x/a)^b)
    Turunan kedua (z = (x/a)^b, u = ln(x/a)):
        d2L/da2  =  n b/a^2 - b(b+1)/a^2 * sum(z)
        d2L/dadb = -n/a + (1/a) sum(z) + (b/a) sum(z u)
        d2L/db2  = -n/b^2 - sum(z u^2)
    Informasi teramati I = -Hessian; acov = inv(I).
    Ref: Nelson (1982) §4; Meeker & Escobar, Statistical Methods for
    Reliability Data, §8 (matriks informasi Weibull).
    """
    n = x.size
    if n < 2 or a <= 0 or b <= 0:
        return None
    with np.errstate(over="ignore", invalid="ignore"):
        z = (x / a) ** b
        u = np.log(x / a)
        d2a = n * b / a**2 - b * (b + 1.0) / a**2 * float(np.sum(z))
        dab = -n / a + float(np.sum(z)) / a + (b / a) * float(np.sum(z * u))
        d2b = -n / b**2 - float(np.sum(z * u**2))
    hess = np.array([[d2a, dab], [dab, d2b]], dtype=float)
    if not np.all(np.isfinite(hess)):
        return None
    info = -hess
    try:
        acov = np.linalg.inv(info)
    except np.linalg.LinAlgError:
        return None
    if not np.all(np.isfinite(acov)) or acov[1, 1] <= 0:
        return None
    return acov


def weibull_ci(
    x: Sequence[float], *, boot_b: int = 400, method: str = "asymptotic", seed: int = 7
) -> Tuple[float, float]:
    """Selang kepercayaan 95% untuk beta: port `weibullCI()` (baris 1792).

    MATLAB memakai `wblfit` bila Statistics Toolbox tersedia (jalur yang
    menghasilkan angka pada laporan), dan bootstrap persentil bila tidak.
    Kedua jalur disediakan di sini:

    * ``method='asymptotic'`` (default, setara wblfit): normal-approksimasi
      pada skala log parameter, beta_lo/hi = beta * exp(+-1.96 * SE/beta).
      Ref: Nelson (1982); dokumentasi wblfit memakai skala log yang sama.
    * ``method='bootstrap'``: persentil 2,5% dan 97,5% dari `boot_b`
      pengambilan ulang: port jalur fallback MATLAB.
    """
    arr = np.asarray(x, dtype=float).ravel()
    arr = arr[arr > 0]
    if arr.size < 2:
        return float("nan"), float("nan")

    if method == "asymptotic":
        b, a = weibull_mle(arr)
        acov = _weibull_acov(a, b, arr)
        if acov is not None:
            se_b = math.sqrt(acov[1, 1])
            if np.isfinite(se_b) and se_b > 0 and b > 0:
                z = 1.959963984540054  # norminv(0.975)
                lo = b * math.exp(-z * se_b / b)
                hi = b * math.exp(z * se_b / b)
                return float(lo), float(hi)
        # Informasi tidak dapat dihitung -> jatuh ke bootstrap.

    rng = np.random.default_rng(seed)
    n = arr.size
    bs = np.empty(boot_b, dtype=float)
    for j in range(boot_b):
        sample = arr[rng.integers(0, n, size=n)]
        bs[j] = weibull_mle(sample)[0]
    bs = bs[np.isfinite(bs)]
    if bs.size == 0:
        return float("nan"), float("nan")
    return pctl(bs, 2.5), pctl(bs, 97.5)


def weibull_r2(x: Sequence[float]) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """Goodness-of-fit plot Weibull: port `weibullR2()` (baris 1809).

    Median rank Bernard F_i = (i - 0.3)/(n + 0.4); regresi
    y = ln(-ln(1-F)) atas x = ln(t); R^2 dari regresi tersebut.
    Ref: Abernethy, R.B., The New Weibull Handbook (5th ed.).
    """
    arr = np.sort(np.asarray(x, dtype=float).ravel())
    arr = arr[arr > 0]
    n = arr.size
    if n < 2:
        empty = np.array([], dtype=float)
        return float("nan"), empty, empty, empty
    i = np.arange(1, n + 1, dtype=float)
    F = (i - 0.3) / (n + 0.4)
    X = np.log(arr)
    Y = np.log(-np.log(1.0 - F))
    slope, intercept = np.polyfit(X, Y, 1)
    Yhat = slope * X + intercept
    ss_tot = float(np.sum((Y - Y.mean()) ** 2))
    r2 = 1.0 - float(np.sum((Y - Yhat) ** 2)) / ss_tot if ss_tot > 0 else float("nan")
    return float(r2), X, Y, Yhat


@dataclass
class BlockFit:
    """Hasil fit satu blok (kelas peralatan atau Functional System)."""

    name: str
    n_tbf: int
    beta: float
    eta: float
    beta_lo: float
    beta_hi: float
    r2: float
    region: str
    source: str
    plot_x: List[float] = field(default_factory=list)
    plot_y: List[float] = field(default_factory=list)
    plot_yhat: List[float] = field(default_factory=list)


def fit_block(
    x: Sequence[float], name: str, *, boot_b: int = 400, ci_method: str = "asymptotic"
) -> BlockFit:
    """Port `fitBlock()` (baris 1744).

    n >= 4 -> MLE penuh + CI + probability plot.
    n <  4 -> shape tidak teridentifikasi: beta = 1 (asumsi eksponensial),
              eta = mean(x) (720 jam bila kosong/tak sah), CI & R2 = NaN.
    """
    arr = np.asarray(x, dtype=float).ravel()
    arr = arr[np.isfinite(arr)]
    if arr.size >= 4:
        b, eta = weibull_mle(arr)
        lo, hi = weibull_ci(arr, boot_b=boot_b, method=ci_method)
        r2, X, Y, Yhat = weibull_r2(arr)
        return BlockFit(
            name=name, n_tbf=int(arr.size), beta=b, eta=eta, beta_lo=lo, beta_hi=hi,
            r2=r2, region=ifr_region(b), source="MLE",
            plot_x=X.tolist(), plot_y=Y.tolist(), plot_yhat=Yhat.tolist(),
        )
    b = 1.0
    eta = float(np.mean(arr)) if arr.size else 0.0
    if arr.size == 0 or not np.isfinite(eta) or eta <= 0:
        eta = 720.0
    return BlockFit(
        name=name, n_tbf=int(arr.size), beta=b, eta=eta,
        beta_lo=float("nan"), beta_hi=float("nan"), r2=float("nan"),
        region=ifr_region(b), source="asumsi (n<4)",
    )


# ==========================================================================
# Estimator beta PER EQUIPMENT (modul C3)
# ==========================================================================
@dataclass
class MRRResult:
    """Hasil Median Rank Regression, termasuk tabel langkah perhitungan."""

    beta: Optional[float]
    eta: Optional[float]
    r2: Optional[float]
    #: baris = [t, adj_rank, median_rank, x=ln t, y=ln(-ln(1-MR))]
    table: List[Tuple[float, float, float, float, float]]


def mrr_fit(tf: Sequence[float], susp: Optional[float]) -> MRRResult:
    """Median Rank Regression dengan koreksi rank Johnson: port `mrrFit()`.

    tf   = TBF kegagalan (jam); susp = SATU waktu tersensor kanan (jam) atau None.
    Kenaikan peringkat Johnson untuk data tersensor:
        inc = (N + 1 - prev) / (1 + reverse_rank)
        adj = prev + inc
    Median rank Bernard: MR = (adj - 0.3) / (N + 0.4).
    Regresi y = ln(-ln(1-MR)) atas x = ln(t): slope = beta, eta = exp(-c/beta).

    Ref: Abernethy, R.B., The New Weibull Handbook (5th ed.), bab 2-3
    (median rank regression, Bernard approximation, Johnson rank adjustment).
    """
    arr = np.asarray(tf, dtype=float).ravel()
    arr = arr[arr > 0]
    # kode 1 = kegagalan (F), kode 0 = sensor kanan (S)
    pts: List[Tuple[float, int]] = [(float(t), 1) for t in arr]
    if susp is not None and np.isfinite(susp) and susp > 0:
        pts.append((float(susp), 0))
    if sum(1 for _, c in pts if c == 1) < 2:
        return MRRResult(None, None, None, [])

    pts.sort(key=lambda p: p[0])
    N = len(pts)
    prev = 0.0
    X: List[float] = []
    Y: List[float] = []
    table: List[Tuple[float, float, float, float, float]] = []
    for idx in range(1, N + 1):
        t_i, code = pts[idx - 1]
        rev = N - idx + 1                     # reverse-rank (termasuk item ini)
        inc = (N + 1.0 - prev) / (1.0 + rev)  # kenaikan peringkat Johnson
        adj = prev + inc
        if code == 1:
            mr = (adj - 0.3) / (N + 0.4)
            mr = min(max(mr, 1e-6), 1.0 - 1e-6)  # jaga 0<MR<1 (hindari log kompleks)
            xv = math.log(t_i)
            yv = math.log(-math.log(1.0 - mr))
            X.append(xv)
            Y.append(yv)
            table.append((t_i, adj, mr, xv, yv))
        prev = adj

    Xa = np.asarray(X)
    Ya = np.asarray(Y)
    mx = float(Xa.mean())
    my = float(Ya.mean())
    denom = float(np.sum((Xa - mx) ** 2))
    if denom <= 0:
        # Seluruh TBF identik -> kemiringan tak terdefinisi.
        return MRRResult(None, None, None, table)
    beta = float(np.sum((Xa - mx) * (Ya - my)) / denom)
    inter = my - beta * mx
    Yh = beta * Xa + inter
    ss_tot = float(np.sum((Ya - my) ** 2))
    r2 = 1.0 - float(np.sum((Ya - Yh) ** 2)) / ss_tot if ss_tot > 0 else 1.0
    eta = float(math.exp(-inter / beta)) if beta != 0 else float("nan")
    return MRRResult(beta, eta, r2, table)


def mle_censored(
    tf: Sequence[float], susp: Optional[float]
) -> Tuple[Optional[float], Optional[float], bool]:
    """MLE Weibull tersensor kanan: port `mleCens()` (baris 1850).

    Menyelesaikan persamaan likelihood (Nelson 1982):
        sum(t^b ln t)/sum(t^b) - 1/b - mean(ln t_gagal) = 0
    dengan bagi-dua pada b di [0.1, 10]. Kembalian ketiga `boundary` = True
    bila solusi menempel batas (mis. satu kegagalan + satu sensor: shape
    tidak teridentifikasi) sehingga TIDAK layak dipakai sebagai shape.
    """
    arr = np.asarray(tf, dtype=float).ravel()
    arr = arr[arr > 0]
    m = arr.size
    if m < 1:
        return None, None, True

    allt = arr if (susp is None or not np.isfinite(susp) or susp <= 0) else np.append(arr, float(susp))
    C = float(np.mean(np.log(arr)))

    def g(b: float) -> float:
        with np.errstate(over="ignore", invalid="ignore"):
            wb = allt**b
            s = float(np.sum(wb))
            if not np.isfinite(s) or s <= 0:
                return float("inf")
            return float(np.sum(wb * np.log(allt)) / s - 1.0 / b - C)

    lo, hi = 0.1, 10.0
    if g(lo) > 0:
        beta = lo
    elif g(hi) < 0:
        beta = hi
    else:
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if g(mid) > 0:
                hi = mid
            else:
                lo = mid
        beta = 0.5 * (lo + hi)

    boundary = (beta >= 9.9) or (beta <= 0.11)
    eta = float((float(np.sum(allt**beta)) / m) ** (1.0 / beta))
    return float(beta), eta, bool(boundary)


def crow_amsaa(cal: Sequence[float], T: float) -> Tuple[Optional[float], Optional[float]]:
    """NHPP power-law Crow-AMSAA: port `crowAMSAA()` (baris 1875).

    Data time-terminated pada T:  beta = n / sum(ln(T/t_i)),  lambda = n / T^beta.
    beta > 1 = intensitas kegagalan MENINGKAT (sistem repairable memburuk);
    beta < 1 = membaik. Dipakai sebagai DIAGNOSTIK TREN, bukan untuk R(t).

    Ref: Crow, L.H. (1975), "Reliability Analysis for Complex Repairable
    Systems", AMSAA TR-138; MIL-HDBK-189.
    """
    arr = np.asarray(cal, dtype=float).ravel()
    arr = arr[(arr > 0) & (arr <= T)]
    n = arr.size
    if n < 2:
        return None, None
    s = float(np.sum(np.log(T / arr)))
    if s <= 0:
        return None, None
    beta = n / s
    lam = n / (T**beta)
    return float(beta), float(lam)


@dataclass
class EquipmentBeta:
    """Parameter Weibull satu tag hasil modul C3 (dengan kredibilitas Buhlmann)."""

    tag: str
    fs: str
    kelas: str
    n_cm: int
    mtbf_hours: float
    beta_mrr: Optional[float]
    r2: Optional[float]
    beta_mle_corrected: Optional[float]
    beta_crow_amsaa: Optional[float]
    prior_class: float
    weight_w: float
    beta_final: float
    eta_final: float
    source: str
    mrr_table: List[Tuple[float, float, float, float, float]] = field(default_factory=list)


def equipment_beta(
    tag: str,
    fs_label: str,
    kelas: str,
    tbf_hours: Sequence[float],
    susp_hours: Optional[float],
    cal_hours: Sequence[float],
    n_failures: int,
    t_obs_hours: float,
    prior_beta_class: float,
    *,
    beta_kmin: int = 3,
    cred_m0: float = 3.0,
) -> EquipmentBeta:
    """Beta & eta per tag dengan kredibilitas Buhlmann: port modul C3 (baris 361-401).

    Langkah (persis MATLAB):
      1. b_mrr dari mrr_fit(TBF, sensor kanan).
      2. Bila k >= beta_kmin dan b_mrr ada:
             b_hat = clamp(b_mrr, 0.3, 6),  w = m / (m + M0)
         selain itu: b_hat = prior kelas, w = 0.
      3. beta_final = w*b_hat + (1-w)*prior_kelas; jatuh ke prior bila tak sah.
      4. eta_final = MTBF / Gamma(1 + 1/beta_final), sehingga laju kegagalan
         teramati tetap konsisten; hanya BENTUK kurva yang diperbaiki.

    Ref: Buhlmann, H., credibility theory (pembobotan estimasi individual
    terhadap prior kelompok); Abernethy (MRR); Nelson (MLE tersensor).
    """
    tf = np.asarray(tbf_hours, dtype=float).ravel()
    tf = tf[tf > 0]
    m = int(tf.size)
    k = int(n_failures)

    mrr = mrr_fit(tf, susp_hours)
    b_mle, _, boundary = mle_censored(tf, susp_hours)
    b_ca, _ = crow_amsaa(cal_hours, t_obs_hours)

    b0 = float(prior_beta_class)
    if not np.isfinite(b0) or b0 <= 0:
        b0 = 1.0

    mtbf = t_obs_hours / k if k > 0 else float("inf")

    if k >= beta_kmin and mrr.beta is not None:
        b_hat = min(max(mrr.beta, 0.3), 6.0)
        w = m / (m + cred_m0)
        source = "MRR+kredibilitas"
    else:
        b_hat = b0
        w = 0.0
        source = "prior kelas (nCM<min)"

    b_fin = w * b_hat + (1.0 - w) * b0
    if not np.isfinite(b_fin) or b_fin <= 0.1:
        b_fin = b0
    eta_fin = mtbf / gamma_fn(1.0 + 1.0 / b_fin) if np.isfinite(mtbf) else float("inf")

    b_mlec: Optional[float] = None
    if b_mle is not None and not boundary:
        b_mlec = float(b_mle * uf_factor(m))

    return EquipmentBeta(
        tag=tag, fs=fs_label, kelas=kelas, n_cm=k, mtbf_hours=float(mtbf),
        beta_mrr=mrr.beta, r2=mrr.r2, beta_mle_corrected=b_mlec, beta_crow_amsaa=b_ca,
        prior_class=b0, weight_w=float(w), beta_final=float(b_fin), eta_final=float(eta_fin),
        source=source, mrr_table=mrr.table,
    )


# ==========================================================================
# Uji tren Laplace (modul D / D2)
# ==========================================================================
def laplace_trend(t: Sequence[float], T: float) -> Tuple[float, float]:
    """Statistik uji tren Laplace: port `laplaceTrend()` (baris 1922).

        U = (sum(t_i) - n*T/2) / (T * sqrt(n/12))
        p = erfc(|U| / sqrt(2))          (dua sisi)

    U > +1,96 -> laju kegagalan MEMBURUK (IFR); U < -1,96 -> MEMBAIK (DFR).
    Ref: Ascher, H. & Feingold, H. (1984), Repairable Systems Reliability.
    """
    arr = np.asarray(t, dtype=float).ravel()
    n = arr.size
    if n == 0 or T <= 0:
        return float("nan"), float("nan")
    u = (float(np.sum(arr)) - n * T / 2.0) / (T * math.sqrt(n / 12.0))
    p = float(erfc(abs(u) / math.sqrt(2.0)))
    return float(u), p


@dataclass
class LaplaceRow:
    level: str
    name: str
    n_fail: int
    u: float
    p_value: float
    verdict: str


def laplace_row(level: str, name: str, fail_times: Sequence[float], t_obs: float) -> LaplaceRow:
    """Port `laplaceRow()` (baris 1766). Perlu >= 4 kejadian agar diuji."""
    arr = np.asarray(fail_times, dtype=float).ravel()
    arr = np.sort(arr[(arr > 0) & (arr < t_obs)])
    if arr.size >= 4:
        u, p = laplace_trend(arr, t_obs)
        if u > 1.96:
            verdict = "Memburuk (IFR)"
        elif u < -1.96:
            verdict = "Membaik (DFR)"
        else:
            verdict = "Stasioner (CFR)"
    else:
        u, p, verdict = float("nan"), float("nan"), "data kurang"
    return LaplaceRow(level, name, int(arr.size), u, p, verdict)


# ==========================================================================
# Umur keandalan
# ==========================================================================
def rel_life(td: Sequence[float], rv: Sequence[float], level: float) -> float:
    """Waktu saat R(t) pertama kali turun ke `level`: port `relLife()` (baris 2590)."""
    t = np.asarray(td, dtype=float)
    r = np.asarray(rv, dtype=float)
    idx = np.flatnonzero(r <= level)
    if idx.size == 0:
        return float("nan")
    i = int(idx[0])
    if i == 0:
        return float(t[0])
    x1, x2 = float(t[i - 1]), float(t[i])
    y1, y2 = float(r[i - 1]), float(r[i])
    if y1 == y2:
        return x2
    return x1 + (y1 - level) * (x2 - x1) / (y1 - y2)
