/**
 * Panel samping diagram RBD.
 *
 * `EquipmentPanel` menampilkan rincian satu peralatan beserta kurva keandalannya.
 * `SelectionPanel` menghitung keandalan gabungan beberapa blok terpilih dan
 * memperbarui hasilnya seketika setiap seleksi berubah.
 */
import { LABEL_KRITIS, PALET, WARNA_KRITIS, num, sci } from '../../lib/format'
import { useStore } from '../../store/useStore'
import { Callout, Chip, DataTable, Loading, Tombol, type Column } from '../ui'
import { Plot } from '../charts/Plot'
import { EquipmentArt, NAMA_KELAS, type KelasPeralatan } from './EquipmentArt'

function Baris({ k, v, mono = true }: { k: string; v: React.ReactNode; mono?: boolean }) {
  return (
    <>
      <dt className="text-slate-500">{k}</dt>
      <dd className={mono ? 'text-right font-mono text-slate-800' : 'text-right text-slate-800'}>{v}</dd>
    </>
  )
}

export function EquipmentPanel() {
  const fokus = useStore((s) => s.focus)
  const memuat = useStore((s) => s.focusLoading)
  const fokusTag = useStore((s) => s.focusTag)

  if (memuat) return <Loading label={`Memuat rincian ${fokusTag ?? 'peralatan'}`} rows={5} />
  if (!fokus)
    return (
      <p className="py-8 text-center text-sm leading-relaxed text-slate-500">
        Klik salah satu blok pada diagram untuk melihat parameter Weibull, MTBF, ketersediaan, dan kurva
        keandalannya.
      </p>
    )

  const d = fokus.detail
  const w = fokus.weibull
  const kelas = (d.kelas in NAMA_KELAS ? d.kelas : 'other') as KelasPeralatan
  const warna = WARNA_KRITIS[d.kritikalitas] ?? WARNA_KRITIS.Z

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <span
          className="flex h-14 w-16 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-slate-50"
          style={{ color: warna }}
        >
          <EquipmentArt kelas={d.kelas} width={52} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h4 className="text-lg font-bold leading-tight text-slate-900">{d.tag}</h4>
            <div className="flex shrink-0 gap-1">
              {d.spof && <Chip className="bg-merah-50 text-merah-700">titik tunggal</Chip>}
              {d.redundan && <Chip className="bg-hijau-50 text-hijau-700">redundan</Chip>}
            </div>
          </div>
          <p className="mt-0.5 text-xs leading-snug text-slate-500">
            {NAMA_KELAS[kelas]}, {d.fs}
          </p>
          <p className="text-xs leading-snug text-slate-400">{d.stage ?? 'di luar jalur RBD'}</p>
        </div>
      </div>

      {!d.pernah_gagal && (
        <Callout tone="note">
          Peralatan ini tidak memiliki notifikasi kegagalan korektif pada jendela pengamatan, sehingga
          diperlakukan <span className="font-mono">R = 1</span> dan <span className="font-mono">A = 1</span>,
          sama seperti perlakuan MATLAB untuk unit cadangan yang tidak pernah gagal.
        </Callout>
      )}

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <Baris
          k="Kritikalitas"
          v={`${d.kritikalitas || KOSONG_TEKS} (${LABEL_KRITIS[d.kritikalitas] ?? 'tidak diketahui'})`}
          mono={false}
        />
        <Baris k="Kegagalan korektif" v={d.n_cm} />
        <Baris k="MTBF" v={`${num(d.mtbf_hari, 1)} hari`} />
        <Baris k="Bentuk β" v={num(d.beta, 4)} />
        <Baris k="Skala η" v={`${num(d.eta_jam, 0)} jam`} />
        <Baris k="MTTR inheren" v={`${num(d.mttr_jam, 0)} jam`} />
        <Baris k="MDT operasional" v={`${num(d.mdt_jam, 0)} jam`} />
        <Baris k="Ketersediaan inheren" v={num(d.a_inh, 4)} />
        <Baris k="Ketersediaan operasional" v={num(d.a_op, 4)} />
        <Baris k="Keandalan 30 hari" v={num(d.r_30hari, 4)} />
      </dl>

      {w && (
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3.5 py-3">
          <p className="mb-2 text-sm font-semibold text-slate-800">Estimasi bentuk pada modul C3</p>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <Baris k="β median rank regression" v={num(w.beta_mrr, 4)} />
            <Baris k="Kecocokan R²" v={num(w.gof_r2, 4)} />
            <Baris k="β MLE terkoreksi" v={num(w.beta_mlec, 4)} />
            <Baris k="β Crow-AMSAA" v={num(w.beta_crow_amsaa, 4)} />
            <Baris k="Prior kelas" v={num(w.prior_kelas, 4)} />
            <Baris k="Bobot kredibilitas" v={num(w.bobot_w, 3)} />
            <Baris k="β final" v={num(w.beta_final, 4)} />
          </dl>
          <p className="mt-2.5 text-2xs leading-relaxed text-slate-500">
            β final dihitung sebagai w kali β median rank regression ditambah (1 kurang w) kali prior kelas,
            dengan w sama dengan m dibagi (m tambah M₀) menurut kredibilitas Bühlmann. Sumber nilai:{' '}
            {w.sumber}. Wilayah laju kegagalan: <strong className="text-slate-700">{w.region}</strong>.
          </p>
        </div>
      )}

      {d.pernah_gagal && (
        <Plot
          height={220}
          exportName={`keandalan_${d.tag}`}
          ariaLabel={`Kurva keandalan ${d.tag}`}
          data={[
            {
              x: fokus.kurva.t_hari,
              y: fokus.kurva.r,
              type: 'scatter',
              mode: 'lines',
              line: { color: warna, width: 2.2 },
              fill: 'tozeroy',
              fillcolor: `${warna}14`,
              hovertemplate: 'hari %{x:.0f}, R = %{y:.4f}<extra></extra>',
            },
          ]}
          layout={{
            title: `Keandalan ${d.tag}`,
            margin: { l: 50, r: 14, t: 30, b: 38 },
            showlegend: false,
            xaxis: { title: 'Waktu misi (hari)' },
            yaxis: { title: 'R(t)', range: [0, 1.02] },
            shapes: [
              {
                type: 'line',
                x0: 30,
                x1: 30,
                y0: 0,
                y1: 1.02,
                line: { color: '#cbd5e1', width: 1, dash: 'dot' },
              },
            ],
          }}
        />
      )}
    </div>
  )
}

const KOSONG_TEKS = 'tidak tercatat'

const KOLOM_SELEKSI: Column<any>[] = [
  { key: 'tag', header: 'Tag', width: '7.5rem' },
  { key: 'fs', header: 'FS', width: '4rem' },
  {
    key: 'kelas',
    header: 'Jenis',
    render: (r) => NAMA_KELAS[(r.kelas in NAMA_KELAS ? r.kelas : 'other') as KelasPeralatan],
  },
  { key: 'n_cm', header: 'Kegagalan', numeric: true },
  { key: 'beta', header: 'β', numeric: true, render: (r) => num(r.beta, 3) },
  { key: 'mtbf_hari', header: 'MTBF hari', numeric: true, render: (r) => num(r.mtbf_hari, 1) },
  { key: 'a_op', header: 'A_op', numeric: true, render: (r) => num(r.a_op, 4) },
  { key: 'r_30hari', header: 'R 30 hari', numeric: true, render: (r) => num(r.r_30hari, 4) },
]

export function SelectionPanel() {
  const sel = useStore((s) => s.selection)
  const terpilih = useStore((s) => s.selected)
  const memuat = useStore((s) => s.selectionLoading)
  const kosongkan = useStore((s) => s.clearSelection)

  if (terpilih.length === 0)
    return (
      <div className="py-8 text-center">
        <p className="text-sm leading-relaxed text-slate-500">
          Tahan{' '}
          <kbd className="rounded border border-slate-300 bg-slate-100 px-1.5 py-0.5 font-sans text-2xs font-medium text-slate-600">
            Ctrl
          </kbd>{' '}
          lalu klik beberapa blok, atau pakai tombol pilih seluruh stage, untuk menghitung keandalan gabungan
          dari kombinasi tersebut.
        </p>
      </div>
    )

  if (memuat && !sel) return <Loading label="Menghitung keandalan gabungan" rows={4} />
  if (!sel) return null

  const r30 = sel.horizon.find((h: any) => h.hari === 30)?.r

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-600">
          <strong className="text-slate-900">{sel.n_terpilih}</strong> peralatan terpilih dengan total{' '}
          <strong className="text-slate-900">{sel.n_cm_total}</strong> kegagalan
          {memuat && <span className="ml-2 text-slate-400">menghitung</span>}
        </p>
        <Tombol kecil varian="halus" ikon="silang" onClick={kosongkan}>
          Kosongkan
        </Tombol>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {[
          { l: 'Keandalan 30 hari', v: sci(r30, 4) },
          { l: 'A inheren', v: num(sel.a_inh, 4) },
          { l: 'A operasional', v: num(sel.a_op, 4) },
        ].map((m) => (
          <div key={m.l} className="rounded-md border border-biru-100 bg-biru-50/60 px-3 py-2">
            <p className="text-2xs font-medium text-slate-500">{m.l}</p>
            <p className="mt-0.5 font-mono text-base font-bold text-biru-800">{m.v}</p>
          </div>
        ))}
      </div>

      <Plot
        height={240}
        exportName="keandalan_seleksi"
        ariaLabel="Kurva keandalan gabungan peralatan terpilih"
        data={[
          {
            x: sel.kurva.t_hari,
            y: sel.kurva.r,
            type: 'scatter',
            mode: 'lines',
            line: { color: PALET.kuning, width: 2.4 },
            fill: 'tozeroy',
            fillcolor: 'rgba(221,139,22,.11)',
            hovertemplate: 'hari %{x:.0f}, R = %{y:.4f}<extra></extra>',
          },
        ]}
        layout={{
          title: 'Keandalan gabungan seleksi',
          margin: { l: 50, r: 14, t: 30, b: 38 },
          showlegend: false,
          xaxis: { title: 'Waktu misi (hari)' },
          yaxis: { title: 'R(t)', range: [0, 1.02] },
        }}
      />

      <div>
        <p className="mb-2 text-sm font-semibold text-slate-800">Cara penggabungan</p>
        <ul className="space-y-1.5 text-xs">
          {sel.kelompok.map((g: any, i: number) => (
            <li key={i} className="flex items-start gap-2">
              <Chip
                className={
                  g.digabung.includes('paralel')
                    ? 'bg-hijau-50 text-hijau-700'
                    : 'bg-slate-100 text-slate-600'
                }
              >
                {g.digabung}
              </Chip>
              <span className="min-w-0 flex-1 text-slate-600">
                <span className="font-medium text-slate-800">{g.stage}</span>{' '}
                <span className="text-slate-400">({g.fs})</span> berisi {g.tags.join(', ')} dengan{' '}
                <span className="font-mono text-slate-600">R₃₀ {num(g.r_30hari, 4)}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <DataTable columns={KOLOM_SELEKSI} rows={sel.tabel} maxHeight="15rem" />

      <div className="overflow-hidden rounded-md border border-slate-200">
        <table className="tabel">
          <thead>
            <tr>
              <th>Horizon misi</th>
              {sel.horizon.map((h: any) => (
                <th key={h.hari} className="text-right">
                  {h.hari} hari
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="font-medium text-slate-700">Keandalan gabungan</td>
              {sel.horizon.map((h: any) => (
                <td key={h.hari} className="angka">
                  {sci(h.r, 4)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <Callout tone="note">{sel.catatan}</Callout>
    </div>
  )
}
