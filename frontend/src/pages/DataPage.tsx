/** Halaman "Data & Upload": Fase 1: unggah, pratinjau, kartu kualitas data. */
import clsx from 'clsx'
import { useCallback, useRef, useState } from 'react'
import { int, num } from '../lib/format'
import { useStore } from '../store/useStore'
import {
  Callout,
  Card,
  DataTable,
  EmptyState,
  Icon,
  KpiCard,
  Loading,
  Pemuat,
  type Column,
} from '../components/ui'

function Dropzone() {
  const uploadFile = useStore((s) => s.uploadFile)
  const uploading = useStore((s) => s.uploading)
  const [over, setOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handle = useCallback(
    async (files: FileList | null) => {
      if (!files) return
      // Berurutan agar pesan toast tidak tumpang tindih dan urutan analisis jelas.
      for (const f of Array.from(files)) await uploadFile(f)
    },
    [uploadFile],
  )

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        void handle(e.dataTransfer.files)
      }}
      className={clsx(
        'flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 transition-colors',
        over ? 'border-biru-700 bg-biru-700/[0.06]' : 'border-slate-300 bg-slate-50/60',
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xlsm"
        multiple
        className="hidden"
        onChange={(e) => void handle(e.target.files)}
      />
      <span
        className="flex h-12 w-12 items-center justify-center rounded-full bg-biru-50 text-biru-700"
        aria-hidden="true"
      >
        {uploading ? <Pemuat size={22} /> : <Icon name="unggah" size={22} />}
      </span>
      <div className="text-center">
        <p className="text-sm font-semibold text-slate-700">
          {uploading ? 'Membaca berkas…' : 'Tarik berkas Excel ke sini'}
        </p>
        <p className="mt-1 max-w-lg text-xs leading-relaxed text-slate-500">
          Jenis berkas dideteksi otomatis dari <strong>nama kolom</strong>, bukan nama berkas. Berkas{' '}
          <em>notifikasi</em> dikenali dari kolom <code>Notifictn type</code>; berkas <em>order/biaya</em>{' '}
          dari kolom <code>TotalPlnndCosts</code>. Keduanya boleh diunggah sekaligus.
        </p>
      </div>
      <button className="btn btn-utama" onClick={() => inputRef.current?.click()} disabled={uploading}>
        Pilih berkas…
      </button>
    </div>
  )
}

function FileCard({ kind }: { kind: 'notification' | 'order' }) {
  const ds = useStore((s) => (kind === 'notification' ? s.notif : s.order))
  const clear = useStore((s) => s.clearDataset)
  if (!ds) return null
  const s = ds.summary
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-biru-800">{ds.filename}</p>
          <p className="text-2xs text-slate-500">
            {kind === 'notification' ? 'Notifikasi (analisis keandalan)' : 'Order (optimasi biaya)'} · sheet{' '}
            <code>{ds.sheet_name}</code>
          </p>
        </div>
        <button className="btn btn-garis btn-kecil" onClick={() => clear(kind)}>
          Hapus
        </button>
      </div>
      <dl className="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <dt className="text-slate-500">Baris di berkas</dt>
        <dd className="text-right font-mono">{int(s.rows_in_file)}</dd>
        <dt className="text-slate-500">Baris unit {s.unit_prefix}</dt>
        <dd className="text-right font-mono">{int(s.rows_unit)}</dd>
        {kind === 'notification' ? (
          <>
            <dt className="text-slate-500">Tag unik</dt>
            <dd className="text-right font-mono">{int(s.n_tags)}</dd>
            <dt className="text-slate-500">Kegagalan korektif</dt>
            <dd className="text-right font-mono">{int(s.n_fail)}</dd>
            <dt className="text-slate-500">Jendela</dt>
            <dd className="text-right font-mono">
              {s.t_start} → {s.t_end}
            </dd>
            <dt className="text-slate-500">T_obs</dt>
            <dd className="text-right font-mono">
              {int(s.t_obs_hours)} jam ({num(s.t_obs_days, 0)} hari)
            </dd>
          </>
        ) : (
          <>
            <dt className="text-slate-500">Tag unik</dt>
            <dd className="text-right font-mono">{int(s.n_tags)}</dd>
            <dt className="text-slate-500">Biaya rencana</dt>
            <dd className="text-right font-mono">{int(s.planned_cost_total)}</dd>
            <dt className="text-slate-500">Biaya aktual</dt>
            <dd className="text-right font-mono">{int(s.actual_cost_total)}</dd>
          </>
        )}
      </dl>
    </div>
  )
}

export function DataPage() {
  const notif = useStore((s) => s.notif)
  const order = useStore((s) => s.order)
  const analysis = useStore((s) => s.analysis)
  const analyzing = useStore((s) => s.analyzing)

  const previewCols: Column<any>[] = notif
    ? Object.keys(notif.preview[0] ?? {}).map((k) => ({ key: k, header: k }))
    : []

  return (
    <div className="space-y-5">
      <Card
        title="Unggah berkas ekspor SAP"
        subtitle="Berkas notifikasi wajib untuk analisis keandalan; berkas order mengaktifkan modul optimasi biaya."
      >
        <div className="space-y-4">
          <Dropzone />
          {(notif || order) && (
            <div className="grid gap-3 md:grid-cols-2">
              <FileCard kind="notification" />
              <FileCard kind="order" />
            </div>
          )}
        </div>
      </Card>

      {!notif && (
        <EmptyState
          ikon="grafik-garis"
          title="Belum ada berkas notifikasi"
          message="Unggah 20260531_Notification_RU_Balongan.xlsx (atau berkas berformat sama) untuk memulai analisis. Seluruh angka pada aplikasi ini dihitung dari berkas yang Anda unggah: tidak ada nilai contoh yang ditanam di kode."
        />
      )}

      {analyzing && !analysis && (
        <Card title="Menjalankan analisis">
          <Loading
            label="Menghitung modul A sampai E: kualitas data, MTBF, Weibull, Laplace, dan RBD…"
            rows={6}
          />
        </Card>
      )}

      {analysis && (
        <>
          <div>
            <h2 className="mb-2.5 text-sm font-semibold text-slate-500">Ringkasan utama</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              {analysis.kpi.map((k) => (
                <KpiCard key={k.judul} {...k} />
              ))}
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-[minmax(0,22rem)_1fr]">
            <Card title="Modul A: Kualitas data & rekap" subtitle="ISO 14224:2016 (periode surveilans)">
              <table className="tabel">
                <tbody>
                  {analysis.data_quality.map((r) => (
                    <tr key={r.metrik}>
                      <td className="text-slate-600">{r.metrik}</td>
                      <td className="num font-semibold text-biru-800">{int(r.nilai)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-3 space-y-2">
                <Callout tone="note">
                  Jendela pengamatan dihitung sebagai{' '}
                  <span className="font-mono">T_obs = tanggal_akhir − tanggal_awal</span> mengikuti ISO 14224
                  (periode surveilans, bukan jarak antar-kejadian). Mode{' '}
                  <strong>{analysis.meta.window_end}</strong> memakai{' '}
                  {analysis.meta.window_end === 'cutoff'
                    ? 'tanggal terakhir di seluruh berkas (tanggal ekspor SAP)'
                    : 'notifikasi unit terakhir'}
                  .
                </Callout>
                {analysis.meta.n_unmapped > 0 && (
                  <Callout tone="warning" title={`${analysis.meta.n_unmapped} tag tanpa mapping FS`}>
                    Tag berikut tidak ada pada mapping Functional System sehingga diperlakukan sebagai OTHER:{' '}
                    {analysis.meta.unmapped_tags.slice(0, 10).join(', ')}
                    {analysis.meta.unmapped_tags.length > 10 ? ', …' : ''}. Analisis tetap berjalan.
                  </Callout>
                )}
              </div>
            </Card>

            <Card
              title="Pratinjau data ternormalisasi"
              subtitle={`25 baris pertama unit ${analysis.meta.unit_prefix} setelah pembersihan tanggal dan pengurutan`}
            >
              {notif && <DataTable columns={previewCols} rows={notif.preview} maxHeight="26rem" searchable />}
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
