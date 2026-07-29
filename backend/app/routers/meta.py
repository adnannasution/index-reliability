"""Endpoint metadata: parameter default, struktur domain, dan referensi akademik (§11)."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app.config.defaults import CLASSES, CRIT_WEIGHT, DEFAULT_CONFIG, MDT_DEFAULT, MTTR_BY_CLASS
from app.core import store
from app.core.fs_mapping import (
    BETA_WORKBOOK,
    FS_FULL_NAME,
    FS_MAP,
    RBD_STAGES,
    fs_name,
)

router = APIRouter(prefix="/api/meta", tags=["metadata"])


#: Referensi wajib §11: ditampilkan pada halaman Metodologi dan ditautkan
#: dari setiap modul perhitungan.
REFERENCES: List[Dict[str, Any]] = [
    {
        "id": 1, "kunci": "ISO 14224:2016",
        "judul": ("Petroleum, petrochemical and natural gas industries: Collection and "
                  "exchange of reliability and maintenance data for equipment"),
        "dipakai_untuk": ("Taksonomi peralatan, definisi MTBF, MTTR, MDT, ketersediaan, "
                          "jendela pengamatan (periode surveilans), dan kekritisan."),
        "modul": ["A", "B", "B2", "E", "J"],
    },
    {
        "id": 2, "kunci": "Abernethy, R.B.: The New Weibull Handbook (5th ed.)",
        "judul": "The New Weibull Handbook",
        "dipakai_untuk": ("Median Rank Regression, aproksimasi median rank Bernard, dan "
                          "koreksi peringkat Johnson untuk data tersensor."),
        "modul": ["C", "C2", "C3"],
    },
    {
        "id": 3, "kunci": "Nelson, W. (1982): Applied Life Data Analysis",
        "judul": "Applied Life Data Analysis (Wiley)",
        "dipakai_untuk": "MLE Weibull tersensor kanan dan selang kepercayaan asimtotik.",
        "modul": ["C", "C3"],
    },
    {
        "id": 4, "kunci": "Thoman, Bain & Antle (1969)",
        "judul": ("Inferences on the Parameters of the Weibull Distribution, "
                  "Technometrics 11(3), 445-460"),
        "dipakai_untuk": "Faktor unbias MLE beta untuk sampel kecil.",
        "modul": ["C3"],
    },
    {
        "id": 5, "kunci": "Crow, L.H. (1975); MIL-HDBK-189",
        "judul": "Reliability Analysis for Complex Repairable Systems (AMSAA TR-138)",
        "dipakai_untuk": ("Crow-AMSAA / NHPP power-law sebagai diagnostik tren sistem "
                          "repairable (beta > 1 memburuk, beta < 1 membaik)."),
        "modul": ["C3", "J"],
    },
    {
        "id": 6, "kunci": "Ascher, H. & Feingold, H. (1984)",
        "judul": "Repairable Systems Reliability: Modeling, Inference, Misconceptions",
        "dipakai_untuk": "Uji tren Laplace beserta p-value.",
        "modul": ["D", "D2"],
    },
    {
        "id": 7, "kunci": "Rausand, M. & Hoyland, A.: System Reliability Theory",
        "judul": "System Reliability Theory: Models, Statistical Methods, and Applications",
        "dipakai_untuk": ("RBD seri-paralel, keandalan sistem, ketersediaan, dan metode "
                          "simulasi Monte Carlo."),
        "modul": ["E", "F"],
    },
    {
        "id": 8, "kunci": "Barlow, R.E. & Hunter, L.C. (1960)",
        "judul": "Optimum Preventive Maintenance Policies, Operations Research 8(1), 90-100",
        "dipakai_untuk": "Model biaya age replacement dan interval optimal tau*.",
        "modul": ["G", "Optimasi biaya"],
    },
    {
        "id": 9, "kunci": "Jardine, A.K.S. & Tsang, A.H.C.",
        "judul": "Maintenance, Replacement, and Reliability: Theory and Applications",
        "dipakai_untuk": "Optimasi interval pemeliharaan preventif dan interpretasinya.",
        "modul": ["G"],
    },
    {
        "id": 10, "kunci": "Blanchard, B.S. & Fabrycky, W.J.",
        "judul": "Systems Engineering and Analysis",
        "dipakai_untuk": "Pembedaan ketersediaan inheren dan ketersediaan operasional.",
        "modul": ["E"],
    },
    {
        "id": 11, "kunci": "Deb, K., Pratap, A., Agarwal, S. & Meyarivan, T. (2002)",
        "judul": ("A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II, "
                  "IEEE Transactions on Evolutionary Computation 6(2), 182-197"),
        "dipakai_untuk": "Pareto front multi-objektif biaya vs ketersediaan.",
        "modul": ["Optimasi biaya"],
    },
    {
        "id": 12, "kunci": "SAE JA1011 / JA1012",
        "judul": "Evaluation Criteria for RCM Processes / A Guide to the RCM Standard",
        "dipakai_untuk": "Logika pemilihan strategi CBM / TBM / inspeksi / run-to-failure.",
        "modul": ["J"],
    },
    {
        "id": 13, "kunci": "API 580 / API 581",
        "judul": "Risk-Based Inspection / Risk-Based Inspection Methodology",
        "dipakai_untuk": "Matriks risiko Risk = PoF x CoF (5x5) dan pita risiko.",
        "modul": ["J"],
    },
    {
        "id": 14, "kunci": "Knights, P.F. (2001)",
        "judul": ("Rethinking Pareto Analysis: Maintenance Applications of Logarithmic "
                  "Scatterplots, Journal of Quality in Maintenance Engineering 7(4)"),
        "dipakai_untuk": "Diagram jack-knife (kronis vs akut) dengan garis iso-downtime.",
        "modul": ["J"],
    },
    {
        "id": 15, "kunci": "OREDA",
        "judul": "Offshore and Onshore Reliability Data Handbook",
        "dipakai_untuk": "Nilai MTTR inheren acuan per kelas peralatan.",
        "modul": ["E"],
    },
    {
        "id": 16, "kunci": "Buhlmann, H.: Credibility Theory",
        "judul": "Mathematical Methods in Risk Theory",
        "dipakai_untuk": ("Pembobotan kredibilitas beta per-tag terhadap prior kelas: "
                          "w = m / (m + M0)."),
        "modul": ["C3"],
    },
    {
        "id": 17,
        "kunci": "Ebeling, C.E.: An Introduction to Reliability and Maintainability Engineering",
        "judul": "An Introduction to Reliability and Maintainability Engineering, McGraw-Hill",
        "dipakai_untuk": (
            "Penentuan interval preventif dari tingkat keandalan minimum yang masih "
            "diterima, yaitu tau_R = eta dikali (-ln R_target) pangkat 1/beta. Dipakai "
            "sebagai pembanding terhadap interval ekonomis pada grafik titik optimal."
        ),
        "modul": ["Titik optimal"],
    },
    {
        "id": 18,
        "kunci": "Barlow, R.E. & Proschan, F.: Mathematical Theory of Reliability",
        "judul": "Mathematical Theory of Reliability, Wiley",
        "dipakai_untuk": (
            "Teorema pembaharuan (renewal reward) yang menjadi dasar laju kegagalan "
            "efektif lambda_eff(tau) = [1 - R(tau)] dibagi integral R(t)dt, serta "
            "kebijakan block replacement untuk interval bersama pada tingkat sistem."
        ),
        "modul": ["Titik optimal", "Optimasi biaya"],
    },
    {
        "id": 19,
        "kunci": "Dekker, R. (1996)",
        "judul": (
            "Applications of maintenance optimisation models: a review and analysis, "
            "Reliability Engineering & System Safety 51(3), 229-240"
        ),
        "dipakai_untuk": (
            "Tinjauan kebijakan pengelompokan interval pada tingkat sistem, yang menjadi "
            "dasar penerapan satu interval bersama bagi seluruh peralatan dalam satu "
            "Functional System."
        ),
        "modul": ["Titik optimal"],
    },
]


#: Penjelasan singkat tiap modul untuk halaman Metodologi.
MODULES: List[Dict[str, str]] = [
    {"kode": "A", "nama": "Kualitas data & rekap notifikasi",
     "rumus": "T_obs = tanggal_akhir - tanggal_awal", "sumber": "ISO 14224:2016"},
    {"kode": "B", "nama": "Keandalan per equipment + Pareto",
     "rumus": "MTBF = T_obs / n_CM ; lambda = n_CM / T_obs ; gagal/thn = 8760 lambda",
     "sumber": "ISO 14224:2016"},
    {"kode": "B2", "nama": "Rekap per Functional System",
     "rumus": "MTBF_seri = T_obs / sum(n_CM dalam FS)", "sumber": "ISO 14224:2016"},
    {"kode": "B3/B4", "nama": "Tabulasi silang FS x kelas & Pareto per FS",
     "rumus": "aturan 80/20 kumulatif", "sumber": "Knights (2001)"},
    {"kode": "C/C2", "nama": "Weibull per kelas & per FS",
     "rumus": "R(t) = exp(-(t/eta)^beta) ; MLE dengan eta ter-profil",
     "sumber": "Nelson (1982); Abernethy"},
    {"kode": "C3", "nama": "Weibull per equipment + kredibilitas",
     "rumus": ("beta_final = w beta_MRR + (1-w) beta_kelas, w = m/(m+M0) ; "
               "eta_final = MTBF / Gamma(1 + 1/beta)"),
     "sumber": "Abernethy; Buhlmann; Thoman-Bain-Antle; Crow"},
    {"kode": "D/D2", "nama": "Uji tren Laplace",
     "rumus": "U = (sum(t_i) - n T/2) / (T sqrt(n/12)) ; p = erfc(|U|/sqrt(2))",
     "sumber": "Ascher & Feingold (1984)"},
    {"kode": "E", "nama": "RBD seri-paralel & ketersediaan",
     "rumus": ("seri R = prod(Ri) ; paralel R = 1 - prod(1-Ri) ; "
               "A_inh = MTBF/(MTBF+MTTR) ; A_op = MTBF/(MTBF+MDT)"),
     "sumber": "Rausand & Hoyland; ISO 14224; Blanchard & Fabrycky"},
    {"kode": "F", "nama": "Monte Carlo ketersediaan sistem",
     "rumus": "TTF ~ Weibull, TTR ~ lognormal(mean = MDT), gabung seri-paralel",
     "sumber": "Rausand & Hoyland; Zio"},
    {"kode": "G", "nama": "Optimasi interval PM (age replacement)",
     "rumus": "C(tau) = [Cp R(tau) + Cf (1-R(tau))] / integral_0^tau R(t) dt",
     "sumber": "Barlow & Hunter (1960); Jardine & Tsang"},
    {"kode": "J", "nama": "Kekritisan & strategi RCM",
     "rumus": "Risk = indeks_frekuensi x indeks_konsekuensi (5x5) ; stok = kuantil Poisson",
     "sumber": "API 580/581; SAE JA1011; ISO 14224; Knights (2001)"},
    {"kode": "Titik optimal", "nama": "Pencarian interval optimal per peralatan dan per FS",
     "rumus": ("C(tau) = [Cp R(tau) + Cf (1-R(tau))] / integral R(t)dt ; "
               "lambda_eff(tau) = [1-R(tau)] / integral R(t)dt ; "
               "A_op(tau) = 1/lambda_eff / (1/lambda_eff + MDT) ; "
               "tau_R = eta (-ln R_target)^(1/beta)"),
     "sumber": ("Barlow & Hunter (1960); Barlow & Proschan; Ebeling; "
                "Dekker (1996); SAE JA1011 untuk uji kelayakan tugas")},
    {"kode": "Opt", "nama": "Optimasi biaya-keandalan NSGA-II",
     "rumus": ("min biaya tahunan vs max A_op sistem ; "
               "lambda_eff(tau) = [1-R(tau)] / integral_0^tau R(t) dt"),
     "sumber": "Deb et al. (2002); Barlow & Hunter (1960); Barlow & Proschan"},
]


@router.get("/defaults")
async def defaults() -> Dict[str, Any]:
    """Seluruh parameter default (port `configDefaults()`) untuk panel pengaturan UI."""
    return store.json_safe(
        {
            "config": DEFAULT_CONFIG.model_dump(),
            "classes": list(CLASSES),
            "mttr_per_kelas": MTTR_BY_CLASS,
            "mdt_default": MDT_DEFAULT,
            "crit_weight": CRIT_WEIGHT,
            "beta_workbook": BETA_WORKBOOK,
            "pilihan": {
                "beta_source": [
                    {"nilai": "equipment",
                     "label": "Per equipment (modul C3): direkomendasikan",
                     "keterangan": "beta Weibull dari riwayat tag itu sendiri + kredibilitas Buhlmann"},
                    {"nilai": "mle", "label": "MLE per kelas (modul C)",
                     "keterangan": "beta hasil MLE gabungan TBF satu kelas peralatan"},
                    {"nilai": "workbook", "label": "Konstanta workbook",
                     "keterangan": "beta tetap per kelas agar sebanding dengan laporan lama"},
                ],
                "window_end": [
                    {"nilai": "cutoff", "label": "Tanggal ekspor SAP (cutoff): default",
                     "keterangan": "tanggal terakhir di SELURUH berkas; menghasilkan T_obs laporan"},
                    {"nilai": "lastevent", "label": "Notifikasi unit terakhir",
                     "keterangan": "tanggal kejadian terakhir pada unit yang dianalisis"},
                ],
                "weibull_estimator": [
                    {"nilai": "mrr", "label": "Median Rank Regression (MRR): default",
                     "keterangan": "Abernethy; transparan, slope plot = beta"},
                    {"nilai": "mle", "label": "MLE tersensor",
                     "keterangan": "Nelson + faktor unbias Thoman-Bain-Antle"},
                    {"nilai": "crow", "label": "Crow-AMSAA (tren)",
                     "keterangan": "NHPP power-law; diagnostik tren, bukan untuk R(t)"},
                    {"nilai": "class", "label": "Per kelas / workbook",
                     "keterangan": "konstanta per kelas peralatan"},
                ],
            },
        }
    )


@router.get("/references")
async def references() -> Dict[str, Any]:
    """Daftar referensi akademik & pemetaannya ke modul (halaman Metodologi)."""
    return store.json_safe({"referensi": REFERENCES, "modul": MODULES})


@router.get("/domain")
async def domain() -> Dict[str, Any]:
    """Struktur domain: mapping tag->FS/MDT dan struktur stage RBD (§5)."""
    return store.json_safe(
        {
            "fs_names": {str(k): v for k, v in FS_FULL_NAME.items()},
            "fs_map": [
                {"tag": t, "fs": fs, "fs_kode": fs_name(fs), "mdt_jam": mdt}
                for t, (fs, mdt) in sorted(FS_MAP.items())
            ],
            "ringkasan_fs": [
                {
                    "fs": fs, "kode": fs_name(fs), "nama": FS_FULL_NAME[fs],
                    "n_tag": sum(1 for v in FS_MAP.values() if v[0] == fs),
                }
                for fs in (1, 2, 3, 0)
            ],
            "rbd_stages": [
                {
                    "fs": s.fs, "fs_kode": fs_name(s.fs), "nama": s.name,
                    "tipe": s.typ, "tags": list(s.tags),
                }
                for s in RBD_STAGES
            ],
        }
    )
