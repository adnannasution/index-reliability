/**
 * Pemformatan angka dan token warna.
 *
 * Angka memakai kaidah penulisan Indonesia: koma sebagai pemisah desimal dan
 * titik sebagai pemisah ribuan. Palet mengikuti gaya visual pertamina.com.
 */

export const PALET = {
  biru: '#0B2F9F', // primer korporat
  biruMuda: '#5C7AE6',
  merah: '#E21F23', // aksen Pertamina
  hijau: '#1F9D68',
  kuning: '#DD8B16',
  abu: '#64748B',
  gelap: '#0F172A',
  /** Warna khusus FS-1, FS-2, FS-3 pada seluruh grafik. */
  fs: ['#0B2F9F', '#1F9D68', '#DD8B16'] as const,
  cdu: '#0F172A',
}

/** Warna blok menurut kelas kritikalitas SAP. */
export const WARNA_KRITIS: Record<string, string> = {
  H: '#E21F23',
  M: '#DD8B16',
  I: '#0B2F9F',
  L: '#1F9D68',
  Z: '#64748B',
}

export const LABEL_KRITIS: Record<string, string> = {
  H: 'Tinggi',
  M: 'Sedang',
  I: 'Insidental',
  L: 'Rendah',
  Z: 'Tanpa klasifikasi',
}

/** Penanda nilai yang tidak tersedia. Sengaja hanya satu tanda hubung biasa. */
export const KOSONG = '-'

/** Bilangan desimal. */
export function num(v: unknown, d = 2): string {
  if (v === null || v === undefined || v === '') return KOSONG
  const n = Number(v)
  if (!Number.isFinite(n)) return KOSONG
  return n.toLocaleString('id-ID', { minimumFractionDigits: d, maximumFractionDigits: d })
}

/** Bilangan bulat dengan pemisah ribuan. */
export function int(v: unknown): string {
  if (v === null || v === undefined || v === '') return KOSONG
  const n = Number(v)
  if (!Number.isFinite(n)) return KOSONG
  return Math.round(n).toLocaleString('id-ID')
}

/**
 * Nilai sangat kecil ditulis dalam notasi ilmiah, sisanya desimal biasa.
 * Mengikuti `sigOrRound()` MATLAB supaya R(1 tahun) tetap terbaca.
 */
export function sci(v: unknown, d = 4): string {
  if (v === null || v === undefined) return KOSONG
  const n = Number(v)
  if (!Number.isFinite(n)) return KOSONG
  if (n !== 0 && Math.abs(n) < 1e-4) {
    const [m, e] = n.toExponential(2).split('e')
    return `${m.replace('.', ',')}×10${sup(Number(e))}`
  }
  return num(n, d)
}

/** Pangkat dalam karakter superskrip, misalnya 10⁻⁷. */
function sup(e: number): string {
  const peta: Record<string, string> = {
    '-': '⁻',
    '0': '⁰',
    '1': '¹',
    '2': '²',
    '3': '³',
    '4': '⁴',
    '5': '⁵',
    '6': '⁶',
    '7': '⁷',
    '8': '⁸',
    '9': '⁹',
  }
  return String(e)
    .split('')
    .map((c) => peta[c] ?? c)
    .join('')
}

/** Persentase dengan satu desimal. */
export function pct(v: unknown, d = 1): string {
  if (v === null || v === undefined) return KOSONG
  const n = Number(v)
  if (!Number.isFinite(n)) return KOSONG
  return `${num(n, d)}%`
}

/** Rupiah ringkas. Nilai SAP dapat mencapai miliaran. */
export function rupiah(v: unknown, d = 1): string {
  if (v === null || v === undefined) return KOSONG
  const n = Number(v)
  if (!Number.isFinite(n)) return KOSONG
  const abs = Math.abs(n)
  if (abs >= 1e12) return `Rp ${num(n / 1e12, d)} T`
  if (abs >= 1e9) return `Rp ${num(n / 1e9, d)} miliar`
  if (abs >= 1e6) return `Rp ${num(n / 1e6, d)} juta`
  if (abs >= 1e3) return `Rp ${num(n / 1e3, 0)} ribu`
  return `Rp ${int(n)}`
}

/** Jam yang besar dinyatakan dalam hari agar lebih mudah dibayangkan. */
export function jam(v: unknown): string {
  const n = Number(v)
  if (!Number.isFinite(n)) return KOSONG
  if (n >= 48) return `${num(n / 24, 1)} hari`
  return `${num(n, 1)} jam`
}

/** Gaya lencana untuk tiap pita risiko (API 580/581). */
export const NADA_RISIKO: Record<string, string> = {
  Ekstrem: 'bg-merah-50 text-merah-700 ring-1 ring-merah-200',
  Tinggi: 'bg-kuning-50 text-kuning-600 ring-1 ring-kuning-100',
  Sedang: 'bg-hijau-50 text-hijau-700 ring-1 ring-hijau-100',
  Rendah: 'bg-slate-100 text-slate-600 ring-1 ring-slate-200',
}

/** Warna latar sel matriks risiko 5x5. */
export function warnaPita(pita: string): string {
  switch (pita) {
    case 'Ekstrem':
      return '#f3c4c6'
    case 'Tinggi':
      return '#fbe0bc'
    case 'Sedang':
      return '#cdeadd'
    default:
      return '#eef1f5'
  }
}

/** Gaya lencana untuk wilayah laju kegagalan (IFR / CFR / DFR). */
export function nadaWilayah(wilayah: string | undefined): string {
  if (!wilayah) return 'bg-slate-100 text-slate-600'
  if (wilayah.includes('Aus')) return 'bg-kuning-50 text-kuning-600'
  if (wilayah.includes('Dini')) return 'bg-merah-50 text-merah-700'
  return 'bg-hijau-50 text-hijau-700'
}
