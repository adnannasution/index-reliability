/**
 * Ikon garis bergaya Tabler Icons, yaitu keluarga ikon yang dipakai
 * pertamina.com. Digambar sebagai SVG inline (stroke, bukan isian) sehingga:
 *   - tidak ada emoji yang membuat antarmuka terlihat seperti templat,
 *   - ketebalan garis dan ukuran seragam dengan tipografi,
 *   - warna mengikuti `currentColor` sehingga otomatis serasi dengan tema.
 *
 * viewBox 24x24, stroke-width 1.75, ujung dan sambungan membulat.
 */
import type { SVGProps } from 'react'

export type NamaIkon =
  | 'unggah'
  | 'berkas'
  | 'roda-gigi'
  | 'kilang'
  | 'grafik-garis'
  | 'bagan-alir'
  | 'dadu'
  | 'kunci-inggris'
  | 'sebaran'
  | 'papan-periksa'
  | 'buku'
  | 'unduh'
  | 'segarkan'
  | 'jalan'
  | 'silang'
  | 'centang'
  | 'peringatan'
  | 'informasi'
  | 'cari'
  | 'panah-kanan'
  | 'panah-bawah'
  | 'gembok'
  | 'penggeser'
  | 'hapus'
  | 'titik'
  | 'jam'
  | 'lapisan'
  | 'menu'

/** Jalur SVG tiap ikon. Kunci `f` menandai bagian yang perlu diisi penuh. */
const JALUR: Record<NamaIkon, { d: string; f?: boolean }[]> = {
  unggah: [{ d: 'M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2' }, { d: 'M7 9l5-5 5 5' }, { d: 'M12 4v12' }],
  berkas: [
    { d: 'M14 3v4a1 1 0 0 0 1 1h4' },
    { d: 'M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z' },
    { d: 'M8 11h8v7H8z' },
    { d: 'M8 14.5h8' },
    { d: 'M12 11v7' },
  ],
  'roda-gigi': [
    {
      d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 0 0-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 0 0-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 0 0-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 0 0-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 0 0 1.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z',
    },
    { d: 'M9 12a3 3 0 1 0 6 0 3 3 0 0 0-6 0' },
  ],
  kilang: [
    { d: 'M3 21h18' },
    { d: 'M5 21V9l5 4V9l5 4h4v8' },
    { d: 'M13 13v.01' },
    { d: 'M17 13v.01' },
    { d: 'M13 17v.01' },
    { d: 'M17 17v.01' },
    { d: 'M9 17v.01' },
  ],
  'grafik-garis': [{ d: 'M4 19h16' }, { d: 'M4 15l4-6 4 2 4-5 4 4' }],
  'bagan-alir': [
    { d: 'M5 15h2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2z' },
    { d: 'M17 15h2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2z' },
    { d: 'M11 3h2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z' },
    { d: 'M6 15v-1a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1' },
    { d: 'M12 9v3' },
  ],
  dadu: [
    { d: 'M6 3h12a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3z' },
    { d: 'M8.5 8.5v.01' },
    { d: 'M15.5 8.5v.01' },
    { d: 'M12 12v.01' },
    { d: 'M8.5 15.5v.01' },
    { d: 'M15.5 15.5v.01' },
  ],
  'kunci-inggris': [
    {
      d: 'M7 10h3V7L6.5 3.5a6 6 0 0 1 8 8l5.5 5.5a2.828 2.828 0 1 1-4 4l-5.5-5.5a6 6 0 0 1-8-8L7 10',
    },
  ],
  sebaran: [
    { d: 'M4 4v16h16' },
    { d: 'M9 15a1.5 1.5 0 1 0 3 0 1.5 1.5 0 0 0-3 0' },
    { d: 'M16 8a1.5 1.5 0 1 0 3 0 1.5 1.5 0 0 0-3 0' },
    { d: 'M7 9a1.5 1.5 0 1 0 3 0 1.5 1.5 0 0 0-3 0' },
    { d: 'M12.2 14.1l3.9-4.6' },
  ],
  'papan-periksa': [
    { d: 'M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2' },
    { d: 'M11 3h2a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2 2 2 0 0 1 2-2z' },
    { d: 'M9 14l2 2 4-4' },
  ],
  buku: [
    { d: 'M19 4v16H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h12z' },
    { d: 'M19 16H7a2 2 0 0 0-2 2' },
    { d: 'M9 8h6' },
  ],
  unduh: [{ d: 'M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2' }, { d: 'M7 11l5 5 5-5' }, { d: 'M12 4v12' }],
  segarkan: [{ d: 'M20 11A8.1 8.1 0 0 0 4.5 9M4 5v4h4' }, { d: 'M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4' }],
  jalan: [{ d: 'M7 4v16l13-8z' }],
  silang: [{ d: 'M18 6L6 18' }, { d: 'M6 6l12 12' }],
  centang: [{ d: 'M5 12l5 5 10-10' }],
  peringatan: [
    { d: 'M12 9v4' },
    {
      d: 'M10.363 3.591L2.257 17.125A1.914 1.914 0 0 0 3.893 19.996h16.214a1.914 1.914 0 0 0 1.636-2.87L13.637 3.59a1.914 1.914 0 0 0-3.274 0z',
    },
    { d: 'M12 16v.01' },
  ],
  informasi: [{ d: 'M3 12a9 9 0 1 0 18 0 9 9 0 0 0-18 0' }, { d: 'M12 9h.01' }, { d: 'M11 12h1v4h1' }],
  cari: [{ d: 'M3 10a7 7 0 1 0 14 0 7 7 0 0 0-14 0' }, { d: 'M21 21l-6-6' }],
  'panah-kanan': [{ d: 'M9 6l6 6-6 6' }],
  'panah-bawah': [{ d: 'M6 9l6 6 6-6' }],
  gembok: [
    { d: 'M7 11h10a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2z' },
    { d: 'M8 11V7a4 4 0 1 1 8 0v4' },
  ],
  penggeser: [
    { d: 'M12 6a2 2 0 1 0 4 0 2 2 0 0 0-4 0' },
    { d: 'M4 6h8' },
    { d: 'M16 6h4' },
    { d: 'M6 12a2 2 0 1 0 4 0 2 2 0 0 0-4 0' },
    { d: 'M4 12h2' },
    { d: 'M10 12h10' },
    { d: 'M15 18a2 2 0 1 0 4 0 2 2 0 0 0-4 0' },
    { d: 'M4 18h11' },
    { d: 'M19 18h1' },
  ],
  hapus: [
    { d: 'M4 7h16' },
    { d: 'M10 11v6' },
    { d: 'M14 11v6' },
    { d: 'M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12' },
    { d: 'M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3' },
  ],
  titik: [{ d: 'M9 12a3 3 0 1 0 6 0 3 3 0 0 0-6 0' }],
  jam: [{ d: 'M3 12a9 9 0 1 0 18 0 9 9 0 0 0-18 0' }, { d: 'M12 7v5l3 3' }],
  lapisan: [{ d: 'M12 3l9 5-9 5-9-5 9-5z' }, { d: 'M3 13l9 5 9-5' }],
  menu: [{ d: 'M4 6h16' }, { d: 'M4 12h16' }, { d: 'M4 18h16' }],
}

interface Props extends Omit<SVGProps<SVGSVGElement>, 'children'> {
  name: NamaIkon
  /** Ukuran sisi dalam piksel. Bawaan 20 agar seimbang dengan teks 13-14 px. */
  size?: number
}

export function Icon({ name, size = 20, strokeWidth = 1.75, ...rest }: Props) {
  const jalur = JALUR[name]
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {jalur.map((p, i) => (
        <path key={i} d={p.d} fill={p.f ? 'currentColor' : 'none'} />
      ))}
    </svg>
  )
}

/** Cincin berputar untuk keadaan memuat. */
export function Pemuat({ size = 16, className }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      className={className ? `animate-spin ${className}` : 'animate-spin'}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.2" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  )
}
