/**
 * Ilustrasi teknis peralatan CDU untuk blok diagram RBD.
 *
 * Digambar sebagai elevasi teknis SVG, bukan foto, dengan alasan:
 *   1. konsisten  : seluruh blok memakai skala, ketebalan garis, dan sudut
 *                   pandang yang sama, sehingga diagram terbaca sebagai satu
 *                   kesatuan (foto dari sumber berbeda selalu bertabrakan);
 *   2. tajam      : vektor tetap bersih pada ukuran blok 132 px maupun saat
 *                   diagram diperbesar atau dicetak;
 *   3. legal      : tidak ada berkas foto kilang berhak cipta yang perlu
 *                   disertakan atau diunduh saat aplikasi berjalan;
 *   4. informatif : bentuk mengikuti wujud nyata peralatan (stack dan burner
 *                   pada dapur pemanas, tray pada kolom, bundle pada shell and
 *                   tube, volute dan motor pada pompa) sehingga operator
 *                   mengenalinya sekali lihat.
 *
 * Warna mengikuti `currentColor` supaya otomatis serasi dengan warna
 * kritikalitas blok induknya. viewBox seragam 64x44.
 */

export type KelasPeralatan = 'heater' | 'column' | 'exchanger' | 'pump' | 'vessel' | 'injection' | 'other'

/** Nama Indonesia tiap kelas, dipakai pada tooltip dan legenda. */
export const NAMA_KELAS: Record<KelasPeralatan, string> = {
  heater: 'Dapur pemanas',
  column: 'Kolom distilasi',
  exchanger: 'Penukar panas',
  pump: 'Pompa sentrifugal',
  vessel: 'Bejana / drum',
  injection: 'Skid injeksi kimia',
  other: 'Peralatan penunjang',
}

const ISI = 0.14 // opasitas isian badan peralatan

/* ------------------------------------------------------------------ heater */
function Heater() {
  return (
    <>
      {/* saluran gas buang */}
      <path d="M45 4h7v14h-7z" fill="currentColor" fillOpacity={ISI} />
      <path d="M45 18V4h7v14" />
      <path d="M44.2 18h8.6" />
      {/* seksi konveksi dan radiasi */}
      <path d="M9 17h36v22H9z" fill="currentColor" fillOpacity={ISI} />
      <path d="M9 39V17h36v22" />
      <path d="M9 24h36" />
      {/* tube konveksi */}
      <path d="M13 20.5h28M13 22h0" strokeOpacity={0.55} />
      {/* tube radiasi tegak */}
      <path d="M15 26v11M21 26v11M27 26v11M33 26v11M39 26v11" strokeOpacity={0.5} />
      {/* burner */}
      <path d="M14 39v2.5M22 39v2.5M30 39v2.5M38 39v2.5" />
      <path d="M5 42h52" />
      {/* sambungan ke stack */}
      <path d="M45 21h-2" strokeOpacity={0.6} />
    </>
  )
}

/* ------------------------------------------------------------------ column */
function Column() {
  return (
    <>
      {/* badan kolom */}
      <path d="M23 9h18v26H23z" fill="currentColor" fillOpacity={ISI} />
      <path d="M23 35V9" />
      <path d="M41 9v26" />
      {/* tutup atas dan bawah berbentuk elips */}
      <path d="M23 9a9 5 0 0 1 18 0" fill="currentColor" fillOpacity={ISI} />
      <path d="M23 35a9 5 0 0 0 18 0" fill="currentColor" fillOpacity={ISI} />
      {/* tray */}
      <path d="M24.5 15h15M24.5 20h15M24.5 25h15M24.5 30h15" strokeOpacity={0.5} />
      {/* nozel puncak, umpan, dan dasar */}
      <path d="M32 4.2V6" />
      <path d="M30 4.2h4" />
      <path d="M23 22.5h-6" />
      <path d="M41 17.5h5" />
      <path d="M32 39.8V38" />
      {/* skirt penopang */}
      <path d="M26 38.6h12" />
      <path d="M27 42h10" />
      <path d="M26.5 38.6 25 42M37.5 38.6 39 42" />
      <path d="M6 42h52" strokeOpacity={0.35} />
    </>
  )
}

/* --------------------------------------------------------------- exchanger */
function Exchanger() {
  return (
    <>
      {/* shell */}
      <path d="M17 14h30v16H17z" fill="currentColor" fillOpacity={ISI} />
      <path d="M17 14h30M17 30h30" />
      {/* tutup kiri (channel head) dan kanan */}
      <path d="M17 14a8 8 0 0 0 0 16" fill="currentColor" fillOpacity={ISI} />
      <path d="M47 14a8 8 0 0 1 0 16" fill="currentColor" fillOpacity={ISI} />
      {/* flange */}
      <path d="M17 12.5v19M47 12.5v19" strokeOpacity={0.75} />
      {/* tube bundle */}
      <path d="M20 18.5h24M20 22h24M20 25.5h24" strokeOpacity={0.45} />
      {/* nozel masuk dan keluar */}
      <path d="M24 14v-4M24 10h4M40 30v4M36 34h4" />
      <path d="M11 22H8M53 22h3" strokeOpacity={0.7} />
      {/* saddle */}
      <path d="M22 30v8M20 38h6M38 30v8M36 38h6" />
      <path d="M6 41h52" />
    </>
  )
}

/* -------------------------------------------------------------------- pump */
function Pump() {
  return (
    <>
      {/* rumah volute */}
      <circle cx="17" cy="22" r="10" fill="currentColor" fillOpacity={ISI} />
      <circle cx="17" cy="22" r="10" />
      <circle cx="17" cy="22" r="4.2" strokeOpacity={0.6} />
      {/* sudu impeller */}
      <path d="M17 17.8v-2M17 26.2v2M12.8 22h-2M21.2 22h2" strokeOpacity={0.4} />
      {/* nozel isap dan tekan */}
      <path d="M7 22H4M4 19v6" />
      <path d="M17 12v-4M14 8h6" />
      {/* kopling */}
      <path d="M27 19h4v6h-4z" fill="currentColor" fillOpacity={ISI} />
      <path d="M27 19v6M31 19v6" />
      {/* motor penggerak */}
      <path d="M31 15h20v14H31z" fill="currentColor" fillOpacity={ISI} />
      <path d="M31 29V15h20v14" />
      <path d="M36 15v14M41 15v14M46 15v14" strokeOpacity={0.4} />
      {/* kotak terminal */}
      <path d="M38 15v-3h6v3" strokeOpacity={0.7} />
      {/* base plate */}
      <path d="M8 34h46v3H8z" fill="currentColor" fillOpacity={ISI} />
      <path d="M8 37V34h46v3" />
      <path d="M17 32v2M41 29v5" strokeOpacity={0.5} />
      <path d="M6 41h52" strokeOpacity={0.35} />
    </>
  )
}

/* ------------------------------------------------------------------ vessel */
function Vessel() {
  return (
    <>
      {/* shell mendatar */}
      <path d="M17 13h30v18H17z" fill="currentColor" fillOpacity={ISI} />
      <path d="M17 13h30M17 31h30" />
      <path d="M17 13a9 9 0 0 0 0 18" fill="currentColor" fillOpacity={ISI} />
      <path d="M47 13a9 9 0 0 1 0 18" fill="currentColor" fillOpacity={ISI} />
      {/* garis batas cairan */}
      <path d="M10 24.5h44" strokeOpacity={0.45} strokeDasharray="3 2.5" />
      {/* nozel dan manway */}
      <path d="M25 13V9M22 9h6" />
      <path d="M39 13V9.5M36.5 9.5h5" />
      <path d="M32 31v3.5M29.5 34.5h5" />
      <circle cx="32" cy="18.5" r="2.6" strokeOpacity={0.6} />
      {/* saddle */}
      <path d="M23 31v7M21 38h5M41 31v7M39 38h5" />
      <path d="M6 41h52" />
    </>
  )
}

/* --------------------------------------------------------------- injection */
function Injection() {
  return (
    <>
      {/* tangki bahan kimia */}
      <path d="M11 10h16v18H11z" fill="currentColor" fillOpacity={ISI} />
      <path d="M11 28V10h16v18" />
      <path d="M11 10a8 3.5 0 0 1 16 0" fill="currentColor" fillOpacity={ISI} />
      {/* kerucut dasar */}
      <path d="M11 28l8 6 8-6" fill="currentColor" fillOpacity={ISI} />
      <path d="M11 28l8 6 8-6" />
      {/* penunjuk level */}
      <path d="M29 14v11" strokeOpacity={0.55} />
      <path d="M27.6 19.5h2.8" strokeOpacity={0.55} />
      {/* pipa ke pompa dosis */}
      <path d="M19 34v3h16" />
      {/* pompa dosis */}
      <path d="M35 27h16v12H35z" fill="currentColor" fillOpacity={ISI} />
      <path d="M35 39V27h16v12" />
      <circle cx="43" cy="33" r="3.4" strokeOpacity={0.6} />
      <path d="M51 33h4" strokeOpacity={0.7} />
      <path d="M39 27v-3h8v3" strokeOpacity={0.6} />
      <path d="M6 41h52" />
    </>
  )
}

/* ------------------------------------------------------------------- other */
function Other() {
  return (
    <>
      <path d="M14 13h36v24H14z" fill="currentColor" fillOpacity={ISI} />
      <path d="M14 37V13h36v24" />
      <path d="M14 20h36" strokeOpacity={0.6} />
      <path d="M20 26h10M20 30h16" strokeOpacity={0.45} />
      <circle cx="43" cy="29" r="4" strokeOpacity={0.55} />
      <path d="M32 13V9M29.5 9h5" />
      <path d="M32 37v4M29.5 41h5" />
      <path d="M6 41h52" strokeOpacity={0.35} />
    </>
  )
}

const GAMBAR: Record<KelasPeralatan, () => JSX.Element> = {
  heater: Heater,
  column: Column,
  exchanger: Exchanger,
  pump: Pump,
  vessel: Vessel,
  injection: Injection,
  other: Other,
}

export function EquipmentArt({
  kelas,
  className,
  width = 62,
}: {
  kelas: string
  className?: string
  width?: number
}) {
  const key = (kelas in GAMBAR ? kelas : 'other') as KelasPeralatan
  const Gambar = GAMBAR[key]
  return (
    <svg
      viewBox="0 0 64 44"
      width={width}
      height={(width * 44) / 64}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.25}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role="img"
      aria-label={NAMA_KELAS[key]}
    >
      <Gambar />
    </svg>
  )
}
