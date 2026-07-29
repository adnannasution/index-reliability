/**
 * Komponen dasar antarmuka.
 *
 * Gaya visual mengikuti pertamina.com: permukaan putih dengan garis tepi tipis,
 * judul dalam huruf normal (bukan kapital seluruhnya), tombol berbentuk pill,
 * dan ikon garis alih alih emoji.
 */
import clsx from 'clsx'
import { useMemo, useState, type ReactNode } from 'react'
import { int, num } from '../../lib/format'
import { useStore } from '../../store/useStore'
import { Icon, Pemuat, type NamaIkon } from './Icon'

export { Icon, Pemuat } from './Icon'
export type { NamaIkon } from './Icon'

// ------------------------------------------------------------------ Kartu
export function Card({
  title,
  subtitle,
  actions,
  children,
  className,
  bodyClass,
  padat = false,
}: {
  title?: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
  bodyClass?: string
  padat?: boolean
}) {
  return (
    <section className={clsx('kartu animate-masuk', className)}>
      {(title || actions) && (
        <header className={clsx('kartu-kepala', padat && 'py-3')}>
          <div className="min-w-0">
            {title && <h3 className="kartu-judul">{title}</h3>}
            {subtitle && <p className="kartu-sub">{subtitle}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={clsx('kartu-isi', bodyClass)}>{children}</div>
    </section>
  )
}

// ------------------------------------------------------------------ Tombol
export function Tombol({
  children,
  varian = 'garis',
  ikon,
  kecil = false,
  memuat = false,
  className,
  ...rest
}: {
  children?: ReactNode
  varian?: 'utama' | 'garis' | 'halus' | 'merah'
  ikon?: NamaIkon
  kecil?: boolean
  memuat?: boolean
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={clsx('btn', `btn-${varian}`, kecil && 'btn-kecil', className)}
      disabled={rest.disabled || memuat}
      {...rest}
    >
      {memuat ? <Pemuat size={kecil ? 13 : 15} /> : ikon ? <Icon name={ikon} size={kecil ? 14 : 16} /> : null}
      {children}
    </button>
  )
}

// --------------------------------------------------------------- Pemuatan
/** Keadaan sedang menghitung, untuk komputasi berat. */
export function Loading({ label, rows = 4 }: { label: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3.5">
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <Pemuat className="text-biru-700" />
        <span>{label}</span>
      </div>
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="rangka h-8" style={{ width: `${100 - i * 8}%` }} />
        ))}
      </div>
    </div>
  )
}

// ------------------------------------------------------------ Keadaan kosong
export function EmptyState({
  title,
  message,
  action,
  ikon = 'berkas',
}: {
  title: string
  message: string
  action?: ReactNode
  ikon?: NamaIkon
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-400">
        <Icon name={ikon} size={22} />
      </span>
      <h4 className="text-lg font-semibold text-slate-800">{title}</h4>
      <p className="max-w-lg text-sm leading-relaxed text-slate-500">{message}</p>
      {action}
    </div>
  )
}

// ------------------------------------------------------------- Kartu angka
const AKSEN: Record<string, string> = {
  biru: 'text-biru-700',
  merah: 'text-merah-500',
  kuning: 'text-kuning-500',
  hijau: 'text-hijau-500',
}

export function KpiCard({
  judul,
  nilai,
  satuan,
  keterangan,
  tone = 'biru',
  ikon,
}: {
  judul: string
  nilai: string
  satuan?: string
  keterangan?: string
  tone?: string
  /** Nama ikon dikirim backend sebagai teks, jadi diterima longgar lalu dipetakan. */
  ikon?: string
}) {
  return (
    <div className="kartu group px-4 py-3.5 transition-colors hover:border-slate-300">
      <div className="flex items-start justify-between gap-2">
        <p className="label-kecil">{judul}</p>
        {ikon && (
          <span
            className={clsx('shrink-0 opacity-45 transition-opacity group-hover:opacity-80', AKSEN[tone])}
          >
            <Icon name={ikon as NamaIkon} size={17} />
          </span>
        )}
      </div>
      <p className="mt-1.5 text-2xl font-bold leading-none tracking-tight text-slate-900">
        {nilai}
        {satuan && <span className="ml-1 text-base font-medium text-slate-400">{satuan}</span>}
      </p>
      {keterangan && <p className="mt-1.5 text-xs leading-snug text-slate-500">{keterangan}</p>}
    </div>
  )
}

// ---------------------------------------------------------------- Lencana
export function Chip({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={clsx('lencana', className ?? 'bg-slate-100 text-slate-600')}>{children}</span>
}

// ------------------------------------------------------------------ Tabel
export type Column<T> = {
  key: string
  header: string
  render?: (row: T) => ReactNode
  numeric?: boolean
  sortValue?: (row: T) => number | string
  width?: string
  title?: string
}

/**
 * Isi sel bawaan. Boolean diubah menjadi teks karena React tidak merender
 * nilai boolean, sehingga kolom seperti `is_fail` akan tampak kosong.
 */
function selBiasa(v: unknown): ReactNode {
  if (typeof v === 'boolean') return v ? 'ya' : 'tidak'
  if (v === null || v === undefined || v === '') return '-'
  return v as ReactNode
}

/**
 * Isi sel numerik bawaan. Nilai bulat ditulis tanpa desimal supaya jumlah tag
 * tampil "2" dan bukan "2,00"; nilai pecahan memakai dua desimal.
 */
function selAngka(v: unknown): ReactNode {
  if (v === null || v === undefined || v === '') return '-'
  const n = Number(v)
  if (!Number.isFinite(n)) return '-'
  return Number.isInteger(n) ? int(n) : num(n, 2)
}

export function DataTable<T extends Record<string, any>>({
  columns,
  rows,
  maxHeight = '30rem',
  searchable = false,
  searchKeys,
  initialSort,
  emptyMessage = 'Tidak ada baris untuk ditampilkan.',
  onRowClick,
  highlightRow,
}: {
  columns: Column<T>[]
  rows: T[]
  maxHeight?: string
  searchable?: boolean
  searchKeys?: string[]
  initialSort?: { key: string; dir: 'asc' | 'desc' }
  emptyMessage?: string
  onRowClick?: (row: T) => void
  highlightRow?: (row: T) => boolean
}) {
  const [sort, setSort] = useState(initialSort)
  const [q, setQ] = useState('')

  const disaring = useMemo(() => {
    if (!q.trim()) return rows
    const cari = q.toLowerCase()
    const kunci = searchKeys ?? columns.map((c) => c.key)
    return rows.filter((r) =>
      kunci.some((k) =>
        String(r[k] ?? '')
          .toLowerCase()
          .includes(cari),
      ),
    )
  }, [rows, q, searchKeys, columns])

  const terurut = useMemo(() => {
    if (!sort) return disaring
    const kolom = columns.find((c) => c.key === sort.key)
    const ambil = kolom?.sortValue ?? ((r: T) => r[sort.key])
    const out = [...disaring].sort((a, b) => {
      const va = ambil(a)
      const vb = ambil(b)
      const na = typeof va === 'number' ? va : Number.NaN
      const nb = typeof vb === 'number' ? vb : Number.NaN
      if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb
      return String(va ?? '').localeCompare(String(vb ?? ''), 'id')
    })
    return sort.dir === 'desc' ? out.reverse() : out
  }, [disaring, sort, columns])

  return (
    <div className="space-y-2.5">
      {searchable && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative max-w-xs flex-1">
            <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400">
              <Icon name="cari" size={16} />
            </span>
            <input
              className="kolom pl-8"
              placeholder="Cari tag, sistem, atau kelas"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              aria-label="Cari dalam tabel"
            />
          </div>
          <span className="text-xs text-slate-500">
            {int(terurut.length)} dari {int(rows.length)} baris
          </span>
        </div>
      )}
      <div className="overflow-auto rounded-md border border-slate-200" style={{ maxHeight }}>
        <table className="tabel">
          <thead>
            <tr>
              {columns.map((c) => {
                const aktif = sort?.key === c.key
                return (
                  <th
                    key={c.key}
                    style={{ width: c.width }}
                    title={c.title ?? c.header}
                    className={clsx(
                      'cursor-pointer select-none hover:text-slate-900',
                      c.numeric && 'text-right',
                    )}
                    aria-sort={aktif ? (sort!.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
                    onClick={() =>
                      setSort((s) =>
                        s?.key === c.key
                          ? { key: c.key, dir: s.dir === 'asc' ? 'desc' : 'asc' }
                          : { key: c.key, dir: 'desc' },
                      )
                    }
                  >
                    <span className={clsx('inline-flex items-center gap-1', c.numeric && 'flex-row-reverse')}>
                      {c.header}
                      <span
                        className={clsx(
                          'transition-opacity',
                          aktif
                            ? 'text-biru-700 opacity-100'
                            : 'text-slate-300 opacity-0 group-hover:opacity-100',
                        )}
                        style={{ fontSize: 9 }}
                      >
                        {aktif ? (sort!.dir === 'asc' ? '▴' : '▾') : '▾'}
                      </span>
                    </span>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {terurut.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-10 text-center text-slate-500">
                  {emptyMessage}
                </td>
              </tr>
            )}
            {terurut.map((r, i) => (
              <tr
                key={i}
                onClick={onRowClick ? () => onRowClick(r) : undefined}
                className={clsx(onRowClick && 'cursor-pointer', highlightRow?.(r) && 'bg-kuning-50/70')}
              >
                {columns.map((c) => (
                  <td key={c.key} className={clsx(c.numeric && 'angka')}>
                    {c.render ? c.render(r) : c.numeric ? selAngka(r[c.key]) : selBiasa(r[c.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// -------------------------------------------------------------- Notifikasi
const GAYA_TOAST: Record<string, { garis: string; ikon: NamaIkon; warna: string }> = {
  error: { garis: 'bg-merah-500', ikon: 'peringatan', warna: 'text-merah-500' },
  warning: { garis: 'bg-kuning-500', ikon: 'peringatan', warna: 'text-kuning-600' },
  success: { garis: 'bg-hijau-500', ikon: 'centang', warna: 'text-hijau-600' },
  info: { garis: 'bg-biru-700', ikon: 'informasi', warna: 'text-biru-700' },
}

export function Toasts() {
  const toasts = useStore((s) => s.toasts)
  const tutup = useStore((s) => s.dismissToast)
  if (!toasts.length) return null
  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex w-[27rem] max-w-[calc(100vw-2.5rem)] flex-col gap-2.5">
      {toasts.map((t) => {
        const g = GAYA_TOAST[t.tone] ?? GAYA_TOAST.info
        return (
          <div
            key={t.id}
            role="alert"
            className="pointer-events-auto relative animate-geser overflow-hidden rounded-lg border border-slate-200 bg-white px-4 py-3 pl-5 shadow-panel"
          >
            <span className={clsx('absolute inset-y-0 left-0 w-[3px]', g.garis)} aria-hidden="true" />
            <div className="flex items-start gap-2.5">
              <span className={clsx('mt-px shrink-0', g.warna)}>
                <Icon name={g.ikon} size={17} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-slate-800">{t.title}</p>
                {t.message && <p className="mt-0.5 text-xs leading-relaxed text-slate-600">{t.message}</p>}
              </div>
              <button
                onClick={() => tutup(t.id)}
                className="shrink-0 rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
                aria-label="Tutup notifikasi"
              >
                <Icon name="silang" size={15} />
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ----------------------------------------------------------------- Catatan
export function Callout({
  tone = 'info',
  title,
  children,
}: {
  tone?: 'info' | 'warning' | 'note'
  title?: string
  children: ReactNode
}) {
  const gaya = {
    info: { kotak: 'border-biru-100 bg-biru-50/70', ikon: 'informasi' as NamaIkon, warna: 'text-biru-700' },
    warning: {
      kotak: 'border-kuning-100 bg-kuning-50/80',
      ikon: 'peringatan' as NamaIkon,
      warna: 'text-kuning-600',
    },
    note: { kotak: 'border-slate-200 bg-slate-50', ikon: 'titik' as NamaIkon, warna: 'text-slate-400' },
  }[tone]
  return (
    <div className={clsx('flex gap-2.5 rounded-md border px-3.5 py-3', gaya.kotak)}>
      <span className={clsx('mt-px shrink-0', gaya.warna)}>
        <Icon name={gaya.ikon} size={16} />
      </span>
      <div className="min-w-0 text-xs leading-relaxed text-slate-600">
        {title && <p className="mb-0.5 text-sm font-semibold text-slate-800">{title}</p>}
        {children}
      </div>
    </div>
  )
}

/** Judul bagian di dalam halaman, untuk memecah daftar kartu yang panjang. */
export function SectionTitle({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2 pt-1">
      <h2 className="text-xl font-semibold text-slate-900">{children}</h2>
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  )
}
