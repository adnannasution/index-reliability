/**
 * Pemilih tag peralatan dengan pencarian, pengelompokan per Functional System,
 * dan pintasan pilih semua atau pilih bad actor.
 *
 * Hanya peralatan yang memiliki riwayat kegagalan korektif yang dapat dipilih,
 * karena peralatan tanpa kegagalan tidak memiliki parameter Weibull sehingga
 * kurva biaya dan keandalannya tidak dapat dihitung.
 */
import clsx from 'clsx'
import { useMemo, useState } from 'react'
import { num } from '../../lib/format'
import { useStore } from '../../store/useStore'
import { Icon, Tombol } from '../ui'

export function TagPicker({
  terpilih,
  onChange,
  maks = 40,
  label = 'Pilih peralatan',
}: {
  terpilih: string[]
  onChange: (tags: string[]) => void
  maks?: number
  label?: string
}) {
  const a = useStore((s) => s.analysis)
  const [cari, setCari] = useState('')
  const [buka, setBuka] = useState(true)

  const kandidat = useMemo(() => (a?.equipment ?? []).filter((r: any) => r.n_cm > 0), [a])

  const disaring = useMemo(() => {
    const q = cari.trim().toLowerCase()
    if (!q) return kandidat
    return kandidat.filter((r: any) =>
      [r.tag, r.fs, r.kelas, r.kritikalitas].some((v) =>
        String(v ?? '')
          .toLowerCase()
          .includes(q),
      ),
    )
  }, [kandidat, cari])

  const perFs = useMemo(() => {
    const g: Record<string, any[]> = {}
    for (const r of disaring) (g[r.fs] ??= []).push(r)
    return g
  }, [disaring])

  const toggle = (tag: string) => {
    if (terpilih.includes(tag)) onChange(terpilih.filter((t) => t !== tag))
    else if (terpilih.length < maks) onChange([...terpilih, tag])
  }

  /** Peralatan dengan kegagalan terbanyak pada masing-masing FS. */
  const badActor = useMemo(() => {
    const per: Record<string, any> = {}
    for (const r of kandidat) {
      if (!per[r.fs] || r.n_cm > per[r.fs].n_cm) per[r.fs] = r
    }
    return Object.values(per)
      .filter((r: any) => r.fs !== 'OTHER')
      .map((r: any) => r.tag)
  }, [kandidat])

  if (!a) return null

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-slate-700">{label}</span>
          <span className="lencana bg-biru-50 text-biru-700">
            {terpilih.length} dari {kandidat.length}
          </span>
          {terpilih.length >= maks && (
            <span className="lencana bg-kuning-50 text-kuning-600">batas {maks} tercapai</span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Tombol kecil varian="halus" onClick={() => onChange(badActor)}>
            Bad actor tiap FS
          </Tombol>
          <Tombol
            kecil
            varian="halus"
            onClick={() => onChange(disaring.slice(0, maks).map((r: any) => r.tag))}
          >
            Pilih semua terlihat
          </Tombol>
          <Tombol kecil varian="halus" ikon="silang" onClick={() => onChange([])}>
            Kosongkan
          </Tombol>
          <Tombol
            kecil
            varian="halus"
            ikon={buka ? 'panah-bawah' : 'panah-kanan'}
            onClick={() => setBuka((v) => !v)}
          >
            {buka ? 'Sembunyikan' : 'Tampilkan'} daftar
          </Tombol>
        </div>
      </div>

      {/* daftar tag terpilih sebagai lencana yang dapat dilepas */}
      {terpilih.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {terpilih.map((t) => (
            <button
              key={t}
              onClick={() => toggle(t)}
              className="inline-flex items-center gap-1 rounded-full border border-biru-200 bg-biru-50 px-2 py-0.5 text-2xs font-medium text-biru-700 transition-colors hover:border-merah-200 hover:bg-merah-50 hover:text-merah-700"
              title={`Lepas ${t}`}
            >
              {t}
              <Icon name="silang" size={11} strokeWidth={2.4} />
            </button>
          ))}
        </div>
      )}

      {buka && (
        <div className="space-y-2.5 rounded-md border border-slate-200 bg-slate-50/60 p-3">
          <div className="relative max-w-xs">
            <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400">
              <Icon name="cari" size={16} />
            </span>
            <input
              className="kolom pl-8"
              placeholder="Cari tag, sistem, atau kelas"
              value={cari}
              onChange={(e) => setCari(e.target.value)}
              aria-label="Cari peralatan"
            />
          </div>

          <div className="grid max-h-72 gap-3 overflow-y-auto sm:grid-cols-2 xl:grid-cols-4">
            {['FS-1', 'FS-2', 'FS-3', 'OTHER'].map((fs) =>
              (perFs[fs] ?? []).length === 0 ? null : (
                <div key={fs}>
                  <p className="sticky top-0 mb-1 bg-slate-50/95 pb-1 text-2xs font-semibold text-slate-500 backdrop-blur">
                    {fs} ({perFs[fs].length})
                  </p>
                  <div className="space-y-0.5">
                    {perFs[fs]
                      .slice()
                      .sort((x: any, y: any) => y.n_cm - x.n_cm)
                      .map((r: any) => {
                        const aktif = terpilih.includes(r.tag)
                        const penuh = !aktif && terpilih.length >= maks
                        return (
                          <button
                            key={r.tag}
                            onClick={() => toggle(r.tag)}
                            disabled={penuh}
                            title={
                              penuh
                                ? `Batas ${maks} peralatan sudah tercapai`
                                : `${r.kelas}, ${r.n_cm} kegagalan, MTBF ${num(r.mtbf_hari, 1)} hari`
                            }
                            className={clsx(
                              'flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left text-2xs transition-colors',
                              aktif
                                ? 'bg-biru-700 font-semibold text-white'
                                : penuh
                                  ? 'cursor-not-allowed text-slate-300'
                                  : 'text-slate-600 hover:bg-white',
                            )}
                          >
                            <span
                              className={clsx(
                                'flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border',
                                aktif ? 'border-white bg-white/20' : 'border-slate-300 bg-white',
                              )}
                              aria-hidden="true"
                            >
                              {aktif && <Icon name="centang" size={9} strokeWidth={3.4} />}
                            </span>
                            <span className="min-w-0 flex-1 truncate font-mono">
                              {r.tag.replace(a.meta.unit_prefix, '')}
                            </span>
                            <span className={clsx('shrink-0', aktif ? 'text-white/70' : 'text-slate-400')}>
                              {r.n_cm}
                            </span>
                            {r.spof && (
                              <span
                                className={clsx('shrink-0', aktif ? 'text-white' : 'text-merah-500')}
                                title="Titik kegagalan tunggal"
                              >
                                <Icon name="peringatan" size={10} strokeWidth={2.4} />
                              </span>
                            )}
                          </button>
                        )
                      })}
                  </div>
                </div>
              ),
            )}
          </div>
          <p className="text-2xs leading-relaxed text-slate-500">
            Angka di kanan tiap tag adalah jumlah kegagalan korektif pada jendela pengamatan. Peralatan tanpa
            kegagalan tidak ditampilkan karena parameter Weibull dan biaya kegagalannya tidak dapat
            diperkirakan.
          </p>
        </div>
      )}
    </div>
  )
}
