/**
 * Diagram Reliability Block Diagram interaktif.
 *
 * Dua mode tampilan:
 *   1. "cdu"        keseluruhan sistem, START ke FS-1, FS-2, FS-3, lalu END,
 *                   ketiganya tersusun seri;
 *   2. "fs1|2|3"    satu Functional System dengan seluruh stage dan bloknya.
 *
 * Semantik visual:
 *   stage seri      blok berderet pada satu garis alir;
 *   stage paralel   blok bertumpuk di antara dua rel percabangan, menandakan
 *                   cukup satu jalur yang beroperasi;
 *   warna blok      mengikuti kelas kritikalitas SAP;
 *   blok SPOF       bergaris tepi merah tebal dengan penanda di sudut.
 *
 * Tiap blok memuat ilustrasi teknis peralatannya (lihat EquipmentArt) supaya
 * jenis peralatan langsung dikenali tanpa perlu membaca tag.
 *
 * Interaksi: klik memilih satu blok, Ctrl atau Shift dan klik menambah blok ke
 * seleksi, lalu keandalan gabungan dihitung ulang seketika oleh backend.
 */
import clsx from 'clsx'
import { useMemo } from 'react'
import { LABEL_KRITIS, WARNA_KRITIS, num, sci } from '../../lib/format'
import { useStore } from '../../store/useStore'
import { Icon } from '../ui/Icon'
import { EquipmentArt, NAMA_KELAS, type KelasPeralatan } from './EquipmentArt'

/** Tinggi blok, dipakai juga untuk menempatkan rel paralel dan terminal. */
const TINGGI_BLOK = 104

export type RbdMode = 'cdu' | 'fs1' | 'fs2' | 'fs3'

// ------------------------------------------------------------------- Blok
function Blok({ b }: { b: any }) {
  const terpilih = useStore((s) => s.selected.includes(b.tag))
  const fokusTag = useStore((s) => s.focusTag)
  const pilih = useStore((s) => s.toggleSelect)
  const setFokus = useStore((s) => s.setFocus)

  const warna = WARNA_KRITIS[b.kritikalitas] ?? WARNA_KRITIS.Z
  const fokus = fokusTag === b.tag
  const belumGagal = !b.pernah_gagal
  const namaKelas =
    NAMA_KELAS[(b.kelas as KelasPeralatan) in NAMA_KELAS ? (b.kelas as KelasPeralatan) : 'other']

  const tip = [
    `${b.tag}, ${namaKelas}`,
    `Kritikalitas SAP ${b.kritikalitas || 'tidak tercatat'} (${LABEL_KRITIS[b.kritikalitas] ?? 'tidak diketahui'})`,
    belumGagal
      ? 'Tidak pernah gagal pada jendela ini, sehingga R = 1 dan A = 1'
      : `Kegagalan korektif ${b.n_cm}, MTBF ${num(b.mtbf_hari, 1)} hari`,
    belumGagal ? '' : `Bentuk β ${num(b.beta, 3)}, skala η ${num(b.eta_jam, 0)} jam`,
    belumGagal ? '' : `A_inh ${num(b.a_inh, 4)}, A_op ${num(b.a_op, 4)}, MDT ${num(b.mdt_jam, 0)} jam`,
    belumGagal ? '' : `Keandalan 30 hari ${num(b.r_30hari, 4)}`,
    b.spof ? 'Titik kegagalan tunggal: seri tanpa redundansi' : '',
    b.redundan ? 'Berada pada stage paralel, tersedia unit cadangan' : '',
  ]
    .filter(Boolean)
    .join('\n')

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={terpilih}
      aria-label={`Blok ${b.tag}, ${namaKelas}${b.spof ? ', titik kegagalan tunggal' : ''}`}
      title={tip}
      style={{ height: TINGGI_BLOK, borderColor: b.spof ? WARNA_KRITIS.H : '#e2e8f0' }}
      onClick={(e) => {
        if (e.ctrlKey || e.metaKey || e.shiftKey) pilih(b.tag, true)
        else {
          void setFokus(b.tag)
          pilih(b.tag, false)
        }
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          const tambah = e.ctrlKey || e.metaKey || e.shiftKey
          pilih(b.tag, tambah)
          if (!tambah) void setFokus(b.tag)
        }
      }}
      className={clsx(
        'group relative flex w-[138px] shrink-0 cursor-pointer flex-col items-center overflow-hidden rounded-lg border bg-white',
        'transition-all duration-200 hover:-translate-y-px hover:border-slate-300 hover:shadow-naik',
        b.spof && 'border-[1.5px]',
        terpilih && 'ring-2 ring-biru-700 ring-offset-1',
        fokus && !terpilih && 'ring-2 ring-slate-400 ring-offset-1',
        belumGagal && 'opacity-65',
      )}
    >
      {/* pita warna kritikalitas */}
      <span className="absolute inset-x-0 top-0 h-[3px]" style={{ background: warna }} aria-hidden="true" />

      {/* ilustrasi peralatan */}
      <div className="flex h-[46px] items-end pt-2.5" style={{ color: warna }}>
        <EquipmentArt kelas={b.kelas} width={60} />
      </div>

      <span className="mt-1 truncate px-1.5 text-sm font-bold leading-none text-slate-800">{b.label}</span>
      <span className="mt-0.5 truncate px-1 text-2xs text-slate-400">{namaKelas}</span>
      <span className="mt-1 font-mono text-2xs leading-none text-slate-500">
        {belumGagal ? 'belum pernah gagal' : `β ${num(b.beta, 2)} · ${b.n_cm} kegagalan`}
      </span>

      {b.spof && (
        <span
          className="absolute right-1 top-[6px] flex h-4 w-4 items-center justify-center rounded-full bg-merah-500 text-white"
          title="Titik kegagalan tunggal"
          aria-hidden="true"
        >
          <Icon name="peringatan" size={11} strokeWidth={2.4} />
        </span>
      )}
      {terpilih && (
        <span
          className="absolute left-1 top-[6px] flex h-4 w-4 items-center justify-center rounded-full bg-biru-700 text-white"
          aria-hidden="true"
        >
          <Icon name="centang" size={11} strokeWidth={3} />
        </span>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ Stage
function Stage({ st }: { st: any }) {
  const pilihBanyak = useStore((s) => s.selectMany)
  const terpilih = useStore((s) => s.selected)
  const paralel = st.tipe === 'par' && st.blocks.length > 1
  const semuaTerpilih = st.blocks.length > 0 && st.blocks.every((b: any) => terpilih.includes(b.tag))

  if (st.kosong) {
    return (
      <div className="flex flex-col items-center gap-2">
        <div
          style={{ height: TINGGI_BLOK }}
          className="flex w-[138px] flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-slate-300 bg-slate-50/70 px-3 text-center"
          title="Stage tanpa tag pada mapping, diperlakukan R = 1 sehingga tidak menurunkan keandalan sistem"
        >
          <span className="text-slate-300">
            <Icon name="lapisan" size={22} />
          </span>
          <span className="text-2xs leading-snug text-slate-400">
            tanpa tag
            <br />R = 1
          </span>
        </div>
        <KeteranganStage st={st} />
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div className={clsx('relative flex items-center', paralel && 'px-5')}>
        {paralel && (
          <>
            {/* rel percabangan dan penyatuan */}
            <span
              className="absolute left-0 w-px bg-slate-300"
              style={{ top: TINGGI_BLOK / 2, bottom: TINGGI_BLOK / 2 }}
              aria-hidden="true"
            />
            <span
              className="absolute right-0 w-px bg-slate-300"
              style={{ top: TINGGI_BLOK / 2, bottom: TINGGI_BLOK / 2 }}
              aria-hidden="true"
            />
          </>
        )}
        <div className={clsx('flex gap-2.5', paralel ? 'flex-col' : 'flex-row items-center')}>
          {st.blocks.map((b: any, i: number) => (
            <div key={b.tag} className="relative flex items-center">
              {paralel && (
                <span
                  className="h-px w-5 shrink-0 bg-slate-300"
                  style={{ marginLeft: -20 }}
                  aria-hidden="true"
                />
              )}
              <Blok b={b} />
              {paralel && (
                <span
                  className="h-px w-5 shrink-0 bg-slate-300"
                  style={{ marginRight: -20 }}
                  aria-hidden="true"
                />
              )}
              {!paralel && i < st.blocks.length - 1 && (
                <span className="h-px w-2.5 shrink-0 bg-slate-300" aria-hidden="true" />
              )}
            </div>
          ))}
        </div>
      </div>

      <KeteranganStage st={st} />

      {st.blocks.length > 1 && (
        <button
          className="rounded-full px-2 py-0.5 text-2xs font-medium text-biru-700 transition-colors hover:bg-biru-50"
          onClick={() =>
            pilihBanyak(
              semuaTerpilih
                ? terpilih.filter((t) => !st.blocks.some((b: any) => b.tag === t))
                : Array.from(new Set([...terpilih, ...st.blocks.map((b: any) => b.tag)])),
            )
          }
        >
          {semuaTerpilih ? 'batalkan stage ini' : 'pilih seluruh stage'}
        </button>
      )}
    </div>
  )
}

function KeteranganStage({ st }: { st: any }) {
  return (
    <div className="w-[172px] text-center">
      <p className="text-xs font-semibold leading-snug text-slate-700" title={st.nama}>
        {st.nama}
      </p>
      <div className="mt-1 flex justify-center">
        <span
          className={clsx(
            'lencana px-2',
            st.tipe === 'par' ? 'bg-hijau-50 text-hijau-700' : 'bg-slate-100 text-slate-600',
          )}
        >
          {st.notasi}
        </span>
      </div>
      <p className="mt-1 font-mono text-2xs text-slate-400">
        R₃₀ {sci(st.r_30hari, 3)} · A_op {num(st.a_op, 3)}
      </p>
    </div>
  )
}

/** Penghubung beralir antar stage yang tersusun seri. */
function Alir() {
  return (
    <div
      className="flex shrink-0 items-center self-start"
      style={{ paddingTop: TINGGI_BLOK / 2 - 4 }}
      aria-hidden="true"
    >
      <span className="h-px w-6 bg-slate-300" />
      <svg width="7" height="8" viewBox="0 0 7 8" className="-ml-px">
        <path d="M0 0l7 4-7 4z" fill="#cbd5e1" />
      </svg>
    </div>
  )
}

function Terminal({ label, judul }: { label: string; judul: string }) {
  return (
    <div
      title={judul}
      className="flex h-10 w-10 shrink-0 items-center justify-center self-start rounded-full bg-biru-700 text-sm font-bold text-white"
      style={{ marginTop: TINGGI_BLOK / 2 - 20 }}
    >
      {label}
    </div>
  )
}

// ---------------------------------------------------------------- Diagram
export function RbdDiagram({ mode }: { mode: RbdMode }) {
  const diagram = useStore((s) => s.diagram)
  const pilihBanyak = useStore((s) => s.selectMany)

  const daftarFs = useMemo(() => {
    if (!diagram) return []
    if (mode === 'cdu') return diagram.fs
    const n = Number(mode.replace('fs', ''))
    return diagram.fs.filter((f: any) => f.fs === n)
  }, [diagram, mode])

  if (!diagram) return null

  // ---- Mode keseluruhan CDU: tiga FS sebagai blok ringkas, tersusun seri ----
  if (mode === 'cdu') {
    const warnaFs = ['#0B2F9F', '#1F9D68', '#DD8B16']
    return (
      <div className="space-y-4">
        <div className="overflow-x-auto pb-1">
          <div className="flex min-w-max items-start gap-1 px-1 py-2">
            <Terminal label="S" judul="Awal jalur, umpan crude masuk" />
            {daftarFs.map((f: any, i: number) => (
              <div key={f.fs} className="flex items-start">
                <Alir />
                <div className="flex flex-col items-center gap-2">
                  <div
                    className="w-[232px] overflow-hidden rounded-lg border bg-white transition-all hover:-translate-y-px hover:shadow-naik"
                    style={{ borderColor: '#e2e8f0', minHeight: TINGGI_BLOK }}
                  >
                    <span className="block h-[3px]" style={{ background: warnaFs[i] }} aria-hidden="true" />
                    <div className="px-3.5 py-2.5">
                      <p className="text-base font-bold leading-none" style={{ color: warnaFs[i] }}>
                        {f.kode}
                      </p>
                      <p className="mt-1 text-2xs leading-snug text-slate-500">
                        {f.nama.replace(/^FS-\d\s*[:,]?\s*/, '')}
                      </p>
                      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-0.5 font-mono text-2xs">
                        <dt className="text-slate-400">R(30 hari)</dt>
                        <dd className="text-right font-semibold text-slate-700">{num(f.r_30hari, 4)}</dd>
                        <dt className="text-slate-400">A_op</dt>
                        <dd className="text-right font-semibold text-slate-700">{num(f.a_op, 4)}</dd>
                        <dt className="text-slate-400">kegagalan</dt>
                        <dd className="text-right text-slate-700">{f.n_cm}</dd>
                        <dt className="text-slate-400">stage</dt>
                        <dd className="text-right text-slate-700">{f.stages.length}</dd>
                      </dl>
                    </div>
                  </div>
                  <button
                    className="rounded-full px-2 py-0.5 text-2xs font-medium text-biru-700 transition-colors hover:bg-biru-50"
                    onClick={() => pilihBanyak(f.stages.flatMap((s: any) => s.blocks.map((b: any) => b.tag)))}
                  >
                    pilih seluruh {f.kode}
                  </button>
                </div>
              </div>
            ))}
            <Alir />
            <Terminal label="E" judul="Akhir jalur, produk keluar" />
          </div>
        </div>

        <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-relaxed text-slate-600">
          Ketiga Functional System tersusun <strong className="text-slate-800">seri</strong>. Kegagalan pada
          salah satunya menghentikan seluruh jalur CDU, sehingga{' '}
          <span className="font-mono text-slate-800">R_CDU(t) = R_FS1 × R_FS2 × R_FS3</span>. Pada misi 30
          hari diperoleh <strong className="font-mono text-slate-900">{num(diagram.cdu.r_30hari, 4)}</strong>{' '}
          dengan ketersediaan operasional gabungan{' '}
          <strong className="font-mono text-slate-900">{num(diagram.cdu.a_op, 4)}</strong>.
        </div>
      </div>
    )
  }

  // ---- Mode per Functional System ----
  return (
    <div className="space-y-6">
      {daftarFs.map((f: any) => (
        <div key={f.fs} className="space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-200 pb-2">
            <h4 className="text-base font-semibold text-slate-900">
              {f.kode}
              <span className="ml-2 text-sm font-normal text-slate-500">
                {f.nama.replace(/^FS-\d\s*[:,]?\s*/, '')}
              </span>
            </h4>
            <p className="font-mono text-2xs text-slate-500">
              R(24 jam) {num(f.r_24j, 4)} · R(30 hari) {num(f.r_30hari, 4)} · A_inh {num(f.a_inh, 4)} · A_op{' '}
              {num(f.a_op, 4)}
            </p>
          </div>
          <div className="overflow-x-auto pb-1">
            <div className="flex min-w-max items-start gap-1 px-1 py-2">
              <Terminal label="S" judul="Masuk ke sistem" />
              {f.stages.map((st: any, i: number) => (
                <div key={i} className="flex items-start">
                  <Alir />
                  <Stage st={st} />
                </div>
              ))}
              <Alir />
              <Terminal label="E" judul="Keluar dari sistem" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ----------------------------------------------------------------- Legenda
export function RbdLegend() {
  const diagram = useStore((s) => s.diagram)
  if (!diagram) return null
  const kelas: KelasPeralatan[] = ['heater', 'column', 'exchanger', 'pump', 'vessel', 'injection']
  return (
    <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50/70 px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-600">
        <span className="font-semibold text-slate-700">Kritikalitas SAP</span>
        {diagram.legend.kritikalitas.map((k: any) => (
          <span key={k.kode} className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: k.warna }} aria-hidden="true" />
            {k.label}
            <span className="text-slate-400">({k.kode})</span>
          </span>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-600">
        <span className="font-semibold text-slate-700">Notasi</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="lencana bg-slate-100 px-2 text-slate-600">seri</span>
          semua harus beroperasi
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="lencana bg-hijau-50 px-2 text-hijau-700">paralel</span>
          cukup satu beroperasi
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-merah-500 text-white">
            <Icon name="peringatan" size={10} strokeWidth={2.6} />
          </span>
          titik kegagalan tunggal
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-slate-200 pt-2.5 text-xs text-slate-600">
        <span className="font-semibold text-slate-700">Jenis peralatan</span>
        {kelas.map((k) => (
          <span key={k} className="inline-flex items-center gap-1.5 text-slate-500">
            <span className="text-slate-400">
              <EquipmentArt kelas={k} width={30} />
            </span>
            {NAMA_KELAS[k]}
          </span>
        ))}
      </div>
    </div>
  )
}
