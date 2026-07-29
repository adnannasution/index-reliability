"""
Data master domain CDU RU VI Balongan: port PERSIS dari CDU_PdM_Balongan.m.

Isi berkas ini adalah STRUKTUR DOMAIN (mapping tag -> Functional System, MDT,
struktur RBD, beta workbook, klasifikasi tag), bukan data variabel. Nilai-nilai
ini diambil dari workbook Analisis_Reliability_CDU_RU_VI.xlsx melalui MATLAB,
sehingga modul RBD mereproduksi angka pada laporan.

Data VARIABEL (daftar tag yang benar-benar muncul, jumlah kegagalan, tanggal)
selalu diturunkan dari file Excel yang di-upload: lihat core/data_loader.py.

Sumber MATLAB:
  fsMap()        -> FS_MAP          (baris 1396-1427)
  rbdStages()    -> RBD_STAGES      (baris 1429-1474)
  betaWorkbook() -> BETA_WORKBOOK   (baris 1476-1486)
  tagType()      -> tag_type()      (baris 1669-1681)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Tuple

from app.config.defaults import MDT_DEFAULT

StageType = Literal["ser", "par"]


# ==========================================================================
# fsMap(): Tag -> (FS, MDT jam).  FS: 1/2/3, 0 = OTHER (di luar jalur utama).
# Disalin PENUH dari MATLAB; jangan diringkas.
#   FS-1: 23 tag | FS-2: 19 tag | FS-3: 21 tag | OTHER: 4 tag
# ==========================================================================
FS_MAP: Dict[str, Tuple[int, float]] = {
    # ---------------- FS-1 (23 tag) ----------------
    "11-A-101": (1, 48.0),
    "11-A-102": (1, 48.0),
    "11-A-103": (1, 48.0),
    "11-A-104": (1, 201.6),
    "11-C-106": (1, 192.0),
    "11-E-105": (1, 312.0),
    "11-E-116": (1, 48.0),
    "11-E-117": (1, 312.0),
    "11-E-131": (1, 192.0),
    "11-P-101A": (1, 16.0),
    "11-P-101B": (1, 48.0),
    "11-P-102A": (1, 229.714),
    "11-P-102B": (1, 42.0),
    "11-P-113A": (1, 48.0),
    "11-P-113B": (1, 48.0),
    "11-P-114A": (1, 48.0),
    "11-P-114B": (1, 48.0),
    "11-P-122": (1, 48.0),
    "11-P-126A": (1, 48.0),
    "11-P-132A": (1, 222.0),
    "11-P-132B": (1, 48.0),
    "11-V-101A": (1, 48.0),
    "11-V-101B": (1, 195.0),
    # ---------------- FS-2 (19 tag) ----------------
    "11-C-101": (2, 384.0),
    "11-E-108": (2, 48.0),
    "11-E-110A": (2, 264.0),
    "11-E-112": (2, 216.0),
    "11-F-101": (2, 115.636),
    "11-P-104A": (2, 57.0),
    "11-P-104B": (2, 48.0),
    "11-P-105A": (2, 48.0),
    "11-P-105B": (2, 48.0),
    "11-P-106A": (2, 48.0),
    "11-P-106B": (2, 48.0),
    "11-P-107A": (2, 48.0),
    "11-P-107B": (2, 48.0),
    "11-P-108A": (2, 48.0),
    "11-P-108B": (2, 48.0),
    "11-P-109A": (2, 78.0),
    "11-P-109B": (2, 48.0),
    "11-P-125A": (2, 48.0),
    "11-P-125B": (2, 48.0),
    # ---------------- FS-3 (21 tag) ----------------
    "11-C-105": (3, 48.0),
    "11-E-114": (3, 102.0),
    "11-E-123": (3, 48.0),
    "11-P-103A": (3, 48.0),
    "11-P-103B": (3, 108.0),
    "11-P-103C": (3, 48.0),
    "11-P-110A": (3, 48.0),
    "11-P-110B": (3, 48.0),
    "11-P-111A": (3, 96.0),
    "11-P-111B": (3, 48.0),
    "11-P-111C": (3, 48.0),
    "11-P-111D": (3, 48.0),
    "11-P-112B": (3, 24.0),
    "11-P-115A": (3, 168.0),
    "11-P-115B": (3, 72.0),
    "11-P-120A": (3, 48.0),
    "11-P-120B": (3, 48.0),
    "11-V-102": (3, 180.0),
    "11-V-104": (3, 48.0),
    "11-V-105": (3, 48.0),
    "11-V-113A": (3, 480.0),
    # ---------------- OTHER (4 tag) ----------------
    "11-DTU-101": (0, 48.0),
    "11-OS-901": (0, 24.0),
    "11-P-601A": (0, 48.0),
    "11-P-601B": (0, 48.0),
}


@dataclass(frozen=True)
class Stage:
    """Satu stage pada Reliability Block Diagram.

    `typ='ser'`: seri  -> R = prod(Ri)        (semua harus jalan)
    `typ='par'`: paralel/redundan -> R = 1 - prod(1-Ri)  (cukup satu jalan)
    Ref: Rausand & Hoyland, System Reliability Theory, bab RBD.
    """

    fs: int
    name: str
    typ: StageType
    tags: Tuple[str, ...] = field(default_factory=tuple)


# ==========================================================================
# rbdStages(): struktur RBD sesuai sheet Reliability_FS pada laporan.
# Catatan MATLAB: tag redundan yang TIDAK muncul di notifikasi (mis. P-112A/C/D)
# berarti tidak pernah gagal pada jendela ini -> R=1, A=1 (ditangani eq_r/eq_a).
# ==========================================================================
RBD_STAGES: Tuple[Stage, ...] = (
    # ---------------- FS-1 ----------------
    Stage(1, "Crude Charge Pumps (P-101 A/B)", "par", ("11-P-101A", "11-P-101B")),
    Stage(1, "Cold Preheat Train (E-101>E-105)", "ser", ("11-E-105",)),
    Stage(1, "2-Stage Desalter (V-101 A>B)", "ser", ("11-V-101A", "11-V-101B")),
    Stage(1, "Desalted Crude Pumps (P-102 A/B)", "par", ("11-P-102A", "11-P-102B")),
    Stage(1, "Preflash Column (C-106)", "ser", ("11-C-106",)),
    Stage(1, "Preflash Bottom Pumps (P-132 A/B)", "par", ("11-P-132A", "11-P-132B")),
    # ---------------- FS-2 ----------------
    Stage(2, "Hot Preheat Train (E-106>E-111)", "ser", ("11-E-108",)),
    Stage(2, "Crude Charge Heater (F-101)", "ser", ("11-F-101",)),
    Stage(2, "Main Fractionator (C-101)", "ser", ("11-C-101",)),
    Stage(2, "Side Strippers (C-102/103/104)", "ser", ()),
    # ---------------- FS-3 ----------------
    Stage(3, "Overhead Condenser (E-114)", "ser", ("11-E-114",)),
    Stage(3, "OH Accumulator (V-102)", "ser", ("11-V-102",)),
    Stage(3, "OH Distillate Pumps (P-103 A/B/C)", "par", ("11-P-103A", "11-P-103B", "11-P-103C")),
    Stage(3, "Stabilizer Drum (V-104)", "ser", ("11-V-104",)),
    Stage(3, "Splitter + OH Drum (C-105, V-105)", "ser", ("11-C-105", "11-V-105")),
    Stage(3, "Splitter OH Pumps (P-111 A-D)", "par",
          ("11-P-111A", "11-P-111B", "11-P-111C", "11-P-111D")),
    Stage(3, "Product Coolers (E-124>E-127)", "ser", ()),
    Stage(3, "Product Pumps (P-112 A-D)", "par",
          ("11-P-112A", "11-P-112B", "11-P-112C", "11-P-112D")),
)


# ==========================================================================
# betaWorkbook(): beta per kelas sesuai laporan (estimator time-terminated).
# Dipakai bila cfg.beta_source == 'workbook' agar hasil sebanding laporan lama.
# ==========================================================================
BETA_WORKBOOK: Dict[str, float] = {
    "heater": 2.46877143309813,
    "vessel": 1.58547404451843,
    "exchanger": 1.31895915990839,
    "pump": 1.28280529058255,
    "column": 1.0,
    "injection": 1.0,
    "other": 1.0,
}


# ==========================================================================
# Fungsi penolong
# ==========================================================================
def tag_type(tag: str, unit_prefix: str = "11-") -> str:
    """Kelas peralatan dari pola tag: port `tagType()` MATLAB.

    MATLAB: p = extractBetween(tag, "11-", "-"); switch upper(p(1))
    Yaitu: ambil potongan antara prefix unit dan tanda '-' berikutnya, lalu
    petakan huruf tunggal ke kelas. Potongan multi-huruf (mis. 'DTU', 'OS')
    tidak cocok dengan huruf tunggal mana pun -> 'other', persis MATLAB.

    Prefix unit dibuat parameter (§3.1) agar unit selain 11 dapat dianalisis;
    default '11-' mereproduksi MATLAB apa adanya.
    """
    s = str(tag or "").strip()
    if not s.startswith(unit_prefix):
        return "other"
    rest = s[len(unit_prefix):]
    head, sep, _ = rest.partition("-")
    if not sep or not head:
        # Tidak ada '-' kedua -> extractBetween MATLAB mengembalikan kosong.
        return "other"
    return {
        "F": "heater",
        "V": "vessel",
        "E": "exchanger",
        "P": "pump",
        "C": "column",
        "A": "injection",
    }.get(head.upper(), "other")


def fs_of(tag: str) -> int:
    """FS suatu tag: 1/2/3, 0 = OTHER, -1 = tidak ada di mapping (port `fsOf`)."""
    entry = FS_MAP.get(str(tag).strip())
    return entry[0] if entry else -1


def mdt_of(tag: str, mdt_default: float = MDT_DEFAULT) -> float:
    """MDT (jam) suatu tag; `mdt_default` bila tak ada di tabel (port `mdtOf`)."""
    entry = FS_MAP.get(str(tag).strip())
    return entry[1] if entry else float(mdt_default)


def fs_name(f: int) -> str:
    """Label FS: port `fsName()`. Nilai di luar 1..3 menjadi 'OTHER'."""
    return {1: "FS-1", 2: "FS-2", 3: "FS-3"}.get(f, "OTHER")


FS_FULL_NAME: Dict[int, str] = {
    1: "FS-1, Crude Receiving, Cold Preheat & Desalting",
    2: "FS-2, Hot Preheat, Fired Heating & Main Fractionation",
    3: "FS-3, Overhead Cooling, Stabilization & Product Refinement",
    0: "OTHER, di luar jalur proses utama",
}


def stages_of_fs(fs: int) -> List[Stage]:
    """Seluruh stage milik satu Functional System, urut sesuai jalur proses."""
    return [s for s in RBD_STAGES if s.fs == fs]


def rbd_tags() -> List[str]:
    """Semua tag unik yang muncul pada jalur RBD (urut stabil)."""
    seen: List[str] = []
    for s in RBD_STAGES:
        for t in s.tags:
            if t not in seen:
                seen.append(t)
    return seen


def is_redundant_tag(tag: str) -> bool:
    """True bila tag berada di stage bertipe paralel: port `isRedundantTag()`."""
    return any(s.typ == "par" and tag in s.tags for s in RBD_STAGES)


def is_single_point_of_failure(tag: str) -> bool:
    """True bila tag berada di stage SERI (tanpa redundansi) pada jalur RBD.

    Dipakai UI untuk menandai blok SPOF dengan border merah (§6), mengikuti
    catatan pada RBD laporan (mis. F-101, C-101).
    """
    return any(s.typ == "ser" and tag in s.tags for s in RBD_STAGES)
