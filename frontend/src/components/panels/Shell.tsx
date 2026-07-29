/**
 * Kerangka aplikasi: sidebar navigasi modul, header status berkas, dan panel
 * pengaturan metode.
 *
 * Gaya mengikuti pertamina.com: sidebar biru korporat pekat, tipografi Plus
 * Jakarta Sans, ikon garis, tombol pill, dan tanpa huruf kapital seluruhnya.
 */
import clsx from 'clsx'
import { useState } from 'react'
import { int, num } from '../../lib/format'
import { useStore } from '../../store/useStore'
import { Icon, Pemuat, type NamaIkon } from '../ui/Icon'

export type PageId =
  | 'data'
  | 'equipment'
  | 'fs'
  | 'weibull'
  | 'rbd'
  | 'montecarlo'
  | 'pm'
  | 'cost'
  | 'rekomendasi'
  | 'metodologi'

export const NAV: {
  id: PageId
  label: string
  ikon: NamaIkon
  group: string
  needsData: boolean
  ringkas: string
}[] = [
  {
    id: 'data',
    label: 'Data dan unggah',
    ikon: 'unggah',
    group: 'Masukan',
    needsData: false,
    ringkas: 'Unggah ekspor SAP, periksa kualitas data, dan lihat jendela pengamatan.',
  },
  {
    id: 'equipment',
    label: 'Keandalan peralatan',
    ikon: 'roda-gigi',
    group: 'Analisis',
    needsData: true,
    ringkas: 'MTBF, laju kegagalan, dan peralatan penyumbang gangguan terbesar.',
  },
  {
    id: 'fs',
    label: 'Functional System',
    ikon: 'kilang',
    group: 'Analisis',
    needsData: true,
    ringkas: 'Pembagian beban kegagalan antar FS-1, FS-2, dan FS-3.',
  },
  {
    id: 'weibull',
    label: 'Weibull dan tren',
    ikon: 'grafik-garis',
    group: 'Analisis',
    needsData: true,
    ringkas: 'Parameter bentuk β, kecocokan model, dan arah tren laju kegagalan.',
  },
  {
    id: 'rbd',
    label: 'Diagram RBD',
    ikon: 'bagan-alir',
    group: 'Analisis',
    needsData: true,
    ringkas: 'Diagram blok keandalan interaktif beserta keandalan sistem.',
  },
  {
    id: 'montecarlo',
    label: 'Monte Carlo',
    ikon: 'dadu',
    group: 'Simulasi',
    needsData: true,
    ringkas: 'Sebaran ketersediaan tahunan dan skenario buruk yang masih wajar.',
  },
  {
    id: 'pm',
    label: 'Interval pemeliharaan',
    ikon: 'kunci-inggris',
    group: 'Optimasi',
    needsData: true,
    ringkas: 'Interval penggantian optimal dan besar penghematannya.',
  },
  {
    id: 'cost',
    label: 'Biaya dan keandalan',
    ikon: 'sebaran',
    group: 'Optimasi',
    needsData: true,
    ringkas: 'Pareto front biaya pemeliharaan tahunan terhadap ketersediaan.',
  },
  {
    id: 'rekomendasi',
    label: 'Rekomendasi RCM',
    ikon: 'papan-periksa',
    group: 'Keluaran',
    needsData: true,
    ringkas: 'Peringkat kekritisan, strategi terpilih, dan kebutuhan suku cadang.',
  },
  {
    id: 'metodologi',
    label: 'Metodologi',
    ikon: 'buku',
    group: 'Keluaran',
    needsData: false,
    ringkas: 'Rumus tiap modul beserta rujukan standar dan pustakanya.',
  },
]

/** Tanda pengenal aplikasi, memakai tiga warna panah logo Pertamina. */
function Lambang() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true" className="shrink-0">
      <path d="M4 17.5 12.4 4l3.1 5.1-8.4 13.4H4z" fill="#ffffff" fillOpacity=".95" />
      <path d="M10.6 22.5 19 9l3.1 5.1-8.4 8.4h-3.1z" fill="#4ade80" fillOpacity=".9" />
      <path d="M17.8 22.5 22.6 17l1.4 2.3-3.1 3.2h-3.1z" fill="#f87171" fillOpacity=".95" />
    </svg>
  )
}

export function Sidebar({
  page,
  setPage,
  terbuka,
  onTutup,
}: {
  page: PageId
  setPage: (p: PageId) => void
  /** true bila drawer sedang tampak di layar kecil. Tidak berpengaruh di layar ≥lg. */
  terbuka: boolean
  onTutup: () => void
}) {
  const adaData = useStore((s) => !!s.analysis)
  const grup = Array.from(new Set(NAV.map((n) => n.group)))

  // Klik menu di layar kecil: pindah halaman lalu tutup drawer supaya konten
  // terlihat. Di layar besar biarkan sidebar tetap terbuka.
  const pilih = (id: PageId) => {
    setPage(id)
    if (typeof window !== 'undefined' && window.innerWidth < 1024) onTutup()
  }

  return (
    <>
      {/* Backdrop hanya tampak saat drawer terbuka di layar kecil. */}
      <div
        onClick={onTutup}
        aria-hidden="true"
        className={clsx(
          'fixed inset-0 z-20 bg-slate-900/40 transition-opacity lg:hidden',
          terbuka ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      />

      <aside
        aria-label="Navigasi modul"
        className={clsx(
          // mobile: fixed drawer dari kiri, dapat digeser masuk/keluar
          'fixed inset-y-0 left-0 z-30 flex h-full w-64 min-w-0 flex-col overflow-hidden bg-biru-700 text-white shadow-xl transition-all duration-200 ease-out',
          // desktop: menempel di layout; lebar mengecil ke 0 saat ditutup agar
          // konten utama otomatis melebar mengisi ruang.
          'lg:static lg:z-auto lg:h-auto lg:shrink-0 lg:shadow-none',
          terbuka
            ? 'translate-x-0 lg:w-64'
            : '-translate-x-full lg:w-0 lg:basis-0 lg:translate-x-0',
        )}
      >
        <div className="flex items-center gap-2.5 border-b border-white/10 px-4 py-4">
          <Lambang />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold leading-tight">Keandalan CDU</p>
            <p className="truncate text-2xs text-white/60">Pertamina RU VI Balongan</p>
          </div>
          {/* Tombol tutup hanya muncul di layar kecil. */}
          <button
            onClick={onTutup}
            aria-label="Tutup menu"
            className="rounded-md p-1 text-white/70 transition-colors hover:bg-white/10 hover:text-white lg:hidden"
          >
            <Icon name="silang" size={18} />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-2.5 py-3">
          {grup.map((g) => (
            <div key={g} className="mb-4">
              <p className="px-2 pb-1.5 text-2xs font-semibold text-white/40">{g}</p>
              {NAV.filter((n) => n.group === g).map((n) => {
                const terkunci = n.needsData && !adaData
                const aktif = page === n.id
                return (
                  <button
                    key={n.id}
                    onClick={() => !terkunci && pilih(n.id)}
                    disabled={terkunci}
                    aria-current={aktif ? 'page' : undefined}
                    title={terkunci ? 'Perlu berkas notifikasi lebih dahulu' : n.ringkas}
                    className={clsx(
                      'mb-0.5 flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm transition-colors',
                      aktif
                        ? 'bg-white font-semibold text-biru-700'
                        : terkunci
                          ? 'cursor-not-allowed text-white/30'
                          : 'text-white/80 hover:bg-white/10 hover:text-white',
                    )}
                  >
                    <Icon name={n.ikon} size={18} className="shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{n.label}</span>
                    {terkunci && <Icon name="gembok" size={13} className="shrink-0 opacity-60" />}
                  </button>
                )
              })}
            </div>
          ))}
        </nav>

        <div className="border-t border-white/10 px-4 py-3 text-2xs leading-relaxed text-white/45">
          Seluruh angka dihitung dari berkas yang Anda unggah.
        </div>
      </aside>
    </>
  )
}

export function Header({
  onOpenSettings,
  onToggleMenu,
  menuTerbuka,
}: {
  onOpenSettings: () => void
  /** Buka/tutup sidebar navigasi. Tersedia di semua ukuran layar. */
  onToggleMenu?: () => void
  menuTerbuka?: boolean
}) {
  const notif = useStore((s) => s.notif)
  const order = useStore((s) => s.order)
  const analysis = useStore((s) => s.analysis)
  const analyzing = useStore((s) => s.analyzing)
  const m = analysis?.meta

  const status = (aktif: boolean, label: string, nilai: string) => (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={clsx('h-1.5 w-1.5 rounded-full', aktif ? 'bg-hijau-500' : 'bg-slate-300')}
        aria-hidden="true"
      />
      <span className="text-slate-500">{label}</span>
      <span className={clsx('font-semibold', aktif ? 'text-slate-800' : 'text-slate-400')}>{nilai}</span>
    </span>
  )

  return (
    <header className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-slate-200 bg-white/92 px-4 py-3 backdrop-blur sm:px-5">
      {/* Tombol menu hamburger, geser sidebar buka/tutup di semua ukuran layar. */}
      {onToggleMenu && (
        <button
          onClick={onToggleMenu}
          aria-label={menuTerbuka ? 'Tutup menu navigasi' : 'Buka menu navigasi'}
          aria-expanded={menuTerbuka}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-slate-300 bg-white text-slate-700 transition-colors hover:bg-slate-50"
        >
          <Icon name="menu" size={20} />
        </button>
      )}
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-5 gap-y-1.5 text-xs">
        {status(!!notif, 'Notifikasi', notif ? `${int(notif.summary.rows_unit)} baris` : 'belum ada')}
        {status(!!order, 'Order biaya', order ? `${int(order.summary.rows_unit)} baris` : 'belum ada')}
        {m && (
          <>
            <span className="hidden h-3.5 w-px bg-slate-200 sm:block" aria-hidden="true" />
            <span className="inline-flex items-center gap-1.5 text-slate-500">
              <Icon name="jam" size={14} className="text-slate-400" />
              Jendela
              <span className="font-mono font-medium text-slate-800">
                {m.t_start} sampai {m.t_end}
              </span>
              <span className="text-slate-300">|</span>
              <span className="font-mono font-medium text-slate-800">
                {int(m.t_obs_hours)} jam ({num(m.t_obs_days, 0)} hari)
              </span>
              <span className="text-slate-300">|</span>
              unit
              <span className="font-mono font-medium text-slate-800">{m.unit_prefix}</span>
            </span>
          </>
        )}
        {analyzing && (
          <span className="inline-flex items-center gap-1.5 text-biru-700">
            <Pemuat size={13} /> menghitung
          </span>
        )}
      </div>
      <button className="btn btn-garis btn-kecil" onClick={onOpenSettings}>
        <Icon name="penggeser" size={15} />
        Pengaturan metode
      </button>
    </header>
  )
}

/** Panel pengaturan metode, memuat seluruh parameter dari defaults.py. */
export function SettingsDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const cfg = useStore((s) => s.config)
  const defaults = useStore((s) => s.defaults)
  const setConfig = useStore((s) => s.setConfig)
  const reset = useStore((s) => s.resetConfig)
  const runAnalysis = useStore((s) => s.runAnalysis)
  const notif = useStore((s) => s.notif)
  const order = useStore((s) => s.order)
  const analyzing = useStore((s) => s.analyzing)
  const [berubah, setBerubah] = useState(false)

  if (!open) return null
  const d = defaults?.config ?? {}
  const pil = defaults?.pilihan

  const set = (patch: Record<string, unknown>) => {
    setConfig(patch)
    setBerubah(true)
  }
  const val = (k: string) => (cfg as any)[k] ?? d[k]

  const angka = (k: string, label: string, step = 1, min?: number, max?: number, bantuan?: string) => (
    <label key={k}>
      <span className="label">{label}</span>
      <input
        type="number"
        className="kolom"
        value={String(val(k) ?? '')}
        step={step}
        min={min}
        max={max}
        onChange={(e) => set({ [k]: Number(e.target.value) })}
      />
      {bantuan && <span className="mt-1 block text-2xs leading-snug text-slate-400">{bantuan}</span>}
    </label>
  )

  const bagian = (judul: string, isi: React.ReactNode) => (
    <section>
      <h3 className="mb-2.5 text-sm font-semibold text-slate-800">{judul}</h3>
      {isi}
    </section>
  )

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-label="Pengaturan metode"
    >
      <div className="absolute inset-0 bg-slate-900/30" onClick={onClose} />
      <div className="relative flex h-full w-[31rem] max-w-full animate-geser flex-col bg-white shadow-panel">
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Pengaturan metode</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Mengubah nilai di sini menghitung ulang seluruh modul.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
            aria-label="Tutup panel"
          >
            <Icon name="silang" size={18} />
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
          {bagian(
            'Estimator dan sumber β',
            <div className="space-y-3.5">
              <label>
                <span className="label">Sumber β untuk RBD</span>
                <select
                  className="kolom"
                  value={val('beta_source')}
                  onChange={(e) => set({ beta_source: e.target.value })}
                >
                  {pil?.beta_source?.map((o: any) => (
                    <option key={o.nilai} value={o.nilai}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <span className="mt-1 block text-2xs leading-snug text-slate-400">
                  {pil?.beta_source?.find((o: any) => o.nilai === val('beta_source'))?.keterangan}
                </span>
              </label>
              <label>
                <span className="label">Akhir jendela pengamatan</span>
                <select
                  className="kolom"
                  value={val('window_end')}
                  onChange={(e) => set({ window_end: e.target.value })}
                >
                  {pil?.window_end?.map((o: any) => (
                    <option key={o.nilai} value={o.nilai}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <span className="mt-1 block text-2xs leading-snug text-slate-400">
                  {pil?.window_end?.find((o: any) => o.nilai === val('window_end'))?.keterangan}
                </span>
              </label>
              <label>
                <span className="label">Prefix unit pada Functional Loc.</span>
                <input
                  className="kolom"
                  value={String(val('unit') ?? '')}
                  onChange={(e) => set({ unit: e.target.value })}
                />
                <span className="mt-1 block text-2xs leading-snug text-slate-400">
                  Unit 11 adalah CDU. Ubah untuk menganalisis unit lain pada berkas yang sama.
                </span>
              </label>
              <div className="grid grid-cols-2 gap-3">
                {angka('beta_kmin', 'Minimum kegagalan', 1, 1, 50, 'Batas agar tag memakai bentuk sendiri')}
                {angka('cred_m0', 'Kekuatan prior M₀', 1, 1, 100, 'Bobot kredibilitas w = m dibagi (m + M₀)')}
              </div>
              {angka('boot_b', 'Iterasi bootstrap', 50, 50, 5000)}
            </div>,
          )}

          {bagian(
            'Rasio biaya pemeliharaan',
            <>
              <div className="grid grid-cols-2 gap-3">
                {angka('cp', 'Biaya preventif Cp', 0.5, 0.01)}
                {angka('cf', 'Biaya korektif Cf', 0.5, 0.01)}
              </div>
              {order && (
                <p className="mt-2 text-2xs leading-snug text-kuning-600">
                  Berkas order sudah diunggah, sehingga Cp dan Cf per tag memakai biaya SAP yang sebenarnya
                  dan menggantikan nilai di atas.
                </p>
              )}
            </>,
          )}

          {bagian(
            'Simulasi Monte Carlo',
            <div className="grid grid-cols-3 gap-3">
              {angka('mc_reps', 'Replikasi', 50, 10, 20000)}
              {angka('mc_horizon', 'Horizon jam', 720, 24)}
              {angka('mc_seed', 'Seed', 1, 0)}
            </div>,
          )}

          {bagian(
            'Kekritisan dan strategi',
            <div className="grid grid-cols-2 gap-3">
              {angka(
                'red_credit',
                'Kredit redundansi',
                0.05,
                0,
                1,
                'Pengurangan konsekuensi bila ada cadangan',
              )}
              {angka(
                'iso_downtime',
                'Garis iso waktu henti',
                25,
                1,
                undefined,
                'Jam per tahun pada jack knife',
              )}
              {angka('beta_dfr', 'Batas kegagalan dini', 0.05, 0.1)}
              {angka('beta_wear', 'Batas mekanisme aus', 0.05, 0.1)}
              {angka('pm_min_saving', 'Penghematan minimum', 1, 0, 100, 'Persen agar TBM dipilih')}
              {angka('svc_level', 'Tingkat layanan spare', 0.01, 0.5, 0.999)}
              {angka('lead_months', 'Waktu tunggu bulan', 1, 0.5, 36)}
            </div>,
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-5 py-3.5">
          <button
            className="btn btn-halus btn-kecil"
            onClick={() => {
              reset()
              setBerubah(true)
            }}
          >
            <Icon name="segarkan" size={14} />
            Kembalikan bawaan
          </button>
          <button
            className="btn btn-utama"
            disabled={!notif || analyzing}
            onClick={async () => {
              await runAnalysis(true)
              setBerubah(false)
              onClose()
            }}
          >
            {analyzing ? <Pemuat size={15} /> : <Icon name="centang" size={16} />}
            {berubah ? 'Terapkan dan hitung ulang' : 'Hitung ulang'}
          </button>
        </div>
      </div>
    </div>
  )
}
