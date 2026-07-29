/**
 * Modul E + fitur unggulan §6: RBD interaktif, R(t) linear & log, ketersediaan.
 * Grafik 9, 10, 11, 16.
 */
import clsx from 'clsx'
import { useEffect, useState } from 'react'
import { PALET, num, sci } from '../lib/format'
import { useStore } from '../store/useStore'
import { Callout, Card, DataTable, Loading, type Column } from '../components/ui'
import { Plot } from '../components/charts/Plot'
import { RbdDiagram, RbdLegend, type RbdMode } from '../components/rbd/RbdDiagram'
import { EquipmentPanel, SelectionPanel } from '../components/rbd/Panels'
import { ExportButtons } from '../components/panels/ExportButtons'

const MODES: { id: RbdMode; label: string }[] = [
  { id: 'cdu', label: 'Keseluruhan CDU' },
  { id: 'fs1', label: 'FS-1' },
  { id: 'fs2', label: 'FS-2' },
  { id: 'fs3', label: 'FS-3' },
]

const STAGE_COLS: Column<any>[] = [
  { key: 'sistem', header: 'Sistem', width: '5rem' },
  { key: 'stage', header: 'Stage', width: '16rem' },
  { key: 'konfig', header: 'Konfig', width: '5rem' },
  { key: 'n_tag', header: 'n tag', numeric: true },
  { key: 'r_24j', header: 'R(24 jam)', numeric: true, render: (r) => num(r.r_24j, 6) },
  { key: 'r_1bln', header: 'R(1 bulan)', numeric: true, render: (r) => num(r.r_1bln, 6) },
  { key: 'r_1thn', header: 'R(1 tahun)', numeric: true, render: (r) => sci(r.r_1thn, 6) },
  { key: 'a_inh', header: 'A_inh', numeric: true, render: (r) => num(r.a_inh, 6) },
  { key: 'a_op', header: 'A_op', numeric: true, render: (r) => num(r.a_op, 6) },
]

const SYS_COLS: Column<any>[] = [
  { key: 'sistem', header: 'Sistem', width: '12rem' },
  { key: 'n_cm', header: 'n_CM', numeric: true },
  {
    key: 'mtbf_seri_hari',
    header: 'MTBF seri (hari)',
    numeric: true,
    render: (r) => num(r.mtbf_seri_hari, 1),
  },
  { key: 'r_24j', header: 'R(24 jam)', numeric: true, render: (r) => num(r.r_24j, 4) },
  { key: 'r_1bln', header: 'R(1 bulan)', numeric: true, render: (r) => num(r.r_1bln, 4) },
  { key: 'r_1thn', header: 'R(1 tahun)', numeric: true, render: (r) => sci(r.r_1thn, 4) },
  {
    key: 'r_1bln_seripenuh',
    header: 'R(1 bln) seri penuh',
    numeric: true,
    title: 'Batas bawah konservatif: seluruh tag FS dianggap seri (redundansi diabaikan)',
    render: (r) => (r.r_1bln_seripenuh === null ? '-' : num(r.r_1bln_seripenuh, 4)),
  },
  { key: 'a_inh', header: 'A_inh', numeric: true, render: (r) => num(r.a_inh, 4) },
  { key: 'a_op', header: 'A_op', numeric: true, render: (r) => num(r.a_op, 4) },
]

export function RbdPage() {
  const a = useStore((s) => s.analysis)!
  const diagram = useStore((s) => s.diagram)
  const loading = useStore((s) => s.diagramLoading)
  const loadDiagram = useStore((s) => s.loadDiagram)
  const selected = useStore((s) => s.selected)
  const [mode, setMode] = useState<RbdMode>('cdu')
  const [logScale, setLogScale] = useState(false)
  const [tab, setTab] = useState<'detail' | 'seleksi'>('detail')

  useEffect(() => {
    void loadDiagram()
  }, [loadDiagram])

  useEffect(() => {
    if (selected.length > 1) setTab('seleksi')
  }, [selected.length])

  const c = a.reliability_curve
  const barH = a.reliability_horizons.filter((r: any) => [1, 7, 30, 90].includes(r.hari))

  return (
    <div className="space-y-5">
      <Card
        title="Grafik 16. Diagram RBD interaktif"
        subtitle="Klik blok untuk detail · Ctrl/⌘/Shift+klik untuk memilih beberapa blok sekaligus"
        actions={
          <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Mode diagram RBD">
            {MODES.map((m) => (
              <button
                key={m.id}
                role="tab"
                aria-selected={mode === m.id}
                onClick={() => setMode(m.id)}
                className={clsx(
                  'rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors',
                  mode === m.id
                    ? 'border-biru-700 bg-biru-700 text-white'
                    : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50',
                )}
              >
                {m.label}
              </button>
            ))}
          </div>
        }
      >
        {loading && <Loading label="Membangun diagram RBD dan menghitung metrik tiap blok…" rows={5} />}
        {!loading && !diagram && (
          <p className="py-6 text-center text-sm text-slate-500">Diagram belum tersedia.</p>
        )}
        {diagram && (
          <div className="space-y-4">
            <RbdLegend />
            <div className="rounded-xl border border-slate-200 bg-gradient-to-b from-slate-50/80 to-white p-3">
              <RbdDiagram mode={mode} />
            </div>
          </div>
        )}
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1fr_minmax(0,27rem)]">
        <Card
          title="Grafik 9. Keandalan sistem R(t)"
          subtitle="FS-1/2/3 dan gabungan CDU; penanda R=0,9, R=0,5, dan misi 30 hari"
          actions={
            <label className="flex items-center gap-1.5 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={logScale}
                onChange={(e) => setLogScale(e.target.checked)}
                className="h-3.5 w-3.5 accent-[#2E5C8A]"
              />
              Skala logaritmik
            </label>
          }
        >
          <Plot
            height={400}
            exportName={`Rt_sistem_${logScale ? 'log' : 'linear'}`}
            ariaLabel="Kurva keandalan sistem terhadap waktu misi"
            data={[
              { name: 'FS-1', y: c.fs1, color: PALET.fs[0], dash: 'solid' },
              { name: 'FS-2', y: c.fs2, color: PALET.fs[1], dash: 'solid' },
              { name: 'FS-3', y: c.fs3, color: PALET.fs[2], dash: 'solid' },
              { name: 'Gabungan CDU', y: c.cdu, color: PALET.cdu, dash: 'dash' },
            ].map((s) => ({
              x: c.t_hari,
              y: logScale ? s.y.map((v) => Math.max(v ?? 1e-30, 1e-30)) : s.y,
              type: 'scatter',
              mode: 'lines',
              name: s.name,
              line: { color: s.color, width: 2.4, dash: s.dash },
              hovertemplate: `${s.name}<br>hari %{x:.0f} · R = %{y:.4g}<extra></extra>`,
            }))}
            layout={{
              title: logScale ? 'Keandalan sistem (skala logaritmik)' : 'Keandalan sistem (skala linear)',
              margin: { l: 62, r: 24, t: 34, b: 64 },
              xaxis: { title: 'Waktu misi (hari)', range: [0, 365] },
              yaxis: logScale
                ? { title: 'R(t): skala log', type: 'log', range: [-12, 0.11], exponentformat: 'power' }
                : { title: 'Keandalan R(t)', range: [0, 1.02] },
              shapes: logScale
                ? [
                    {
                      type: 'line',
                      x0: 30,
                      x1: 30,
                      yref: 'paper',
                      y0: 0,
                      y1: 1,
                      line: { color: '#94a3b8', width: 1, dash: 'dot' },
                    },
                  ]
                : [
                    {
                      type: 'line',
                      x0: 0,
                      x1: 365,
                      y0: 0.9,
                      y1: 0.9,
                      line: { color: PALET.abu, width: 1, dash: 'dot' },
                    },
                    {
                      type: 'line',
                      x0: 0,
                      x1: 365,
                      y0: 0.5,
                      y1: 0.5,
                      line: { color: PALET.abu, width: 1, dash: 'dot' },
                    },
                    {
                      type: 'line',
                      x0: 30,
                      x1: 30,
                      y0: 0,
                      y1: 1.02,
                      line: { color: '#94a3b8', width: 1, dash: 'dot' },
                    },
                  ],
              annotations: logScale
                ? []
                : [
                    {
                      x: 365,
                      y: 0.9,
                      text: 'R=0,9',
                      showarrow: false,
                      xanchor: 'right',
                      yanchor: 'bottom',
                      font: { size: 10, color: PALET.abu },
                    },
                    {
                      x: 365,
                      y: 0.5,
                      text: 'R=0,5',
                      showarrow: false,
                      xanchor: 'right',
                      yanchor: 'bottom',
                      font: { size: 10, color: PALET.abu },
                    },
                    {
                      x: 30,
                      y: 0.03,
                      text: 'misi 30 hari',
                      showarrow: false,
                      xanchor: 'left',
                      font: { size: 10, color: '#64748b' },
                    },
                  ],
            }}
          />
          <Callout tone="note">
            R(1 tahun) mendekati nol adalah <strong>benar</strong>, bukan galat: itu peluang sistem melewati
            setahun penuh <em>tanpa satu pun</em> kegagalan, padahal gangguan terjadi tiap 10-25 hari. Untuk
            indikator tahunan gunakan ketersediaan (A_op) dan ekspektasi jumlah kegagalan.
          </Callout>
        </Card>

        <Card
          title={tab === 'detail' ? 'Detail peralatan' : 'Keandalan gabungan seleksi'}
          actions={
            <div className="flex gap-1.5" role="tablist">
              {(['detail', 'seleksi'] as const).map((t) => (
                <button
                  key={t}
                  role="tab"
                  aria-selected={tab === t}
                  onClick={() => setTab(t)}
                  className={clsx(
                    'rounded-lg border px-2.5 py-1 text-xs font-medium capitalize',
                    tab === t
                      ? 'border-biru-700 bg-biru-700 text-white'
                      : 'border-slate-300 bg-white text-slate-600',
                  )}
                >
                  {t}
                  {t === 'seleksi' && selected.length > 0 && (
                    <span className="ml-1 rounded-full bg-white/25 px-1.5 text-2xs">{selected.length}</span>
                  )}
                </button>
              ))}
            </div>
          }
        >
          {tab === 'detail' ? <EquipmentPanel /> : <SelectionPanel />}
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card
          title="Grafik 10. Ketersediaan inheren vs operasional"
          subtitle="A_inh = MTBF/(MTBF+MTTR) · A_op = MTBF/(MTBF+MDT): ISO 14224; Blanchard & Fabrycky"
        >
          <Plot
            height={340}
            exportName="ketersediaan_fs"
            ariaLabel="Perbandingan ketersediaan inheren dan operasional per sistem"
            data={[
              {
                x: a.availability.map((r: any) => r.sistem),
                y: a.availability.map((r: any) => r.a_inh),
                type: 'bar',
                name: 'Ketersediaan inheren',
                marker: { color: PALET.biru },
                text: a.availability.map((r: any) => num(r.a_inh, 3)),
                textposition: 'outside',
                hovertemplate: '%{x}<br>A_inh = %{y:.4f}<extra></extra>',
              },
              {
                x: a.availability.map((r: any) => r.sistem),
                y: a.availability.map((r: any) => r.a_op),
                type: 'bar',
                name: 'Ketersediaan operasional',
                marker: { color: PALET.kuning },
                text: a.availability.map((r: any) => num(r.a_op, 3)),
                textposition: 'outside',
                hovertemplate: '%{x}<br>A_op = %{y:.4f}<extra></extra>',
              },
            ]}
            layout={{
              title: 'Selisih ketersediaan inheren dan operasional',
              barmode: 'group',
              margin: { l: 56, r: 20, t: 34, b: 58 },
              yaxis: { title: 'Ketersediaan A', range: [0.5, 1.03] },
            }}
          />
          <Callout tone="info">
            Selisih kedua batang adalah temuan terpenting: waktu yang hilang <strong>bukan</strong> karena
            lamanya pekerjaan bengkel (MTTR), melainkan karena menunggu suku cadang, izin kerja, dan
            penjadwalan (MDT). Memperbaiki proses administrasi memberi hasil lebih besar daripada mempercepat
            pekerjaan bengkel.
          </Callout>
        </Card>

        <Card title="Grafik 11. Keandalan pada beberapa pilihan lama misi" subtitle="Modul E3">
          <Plot
            height={340}
            exportName="keandalan_horizon"
            ariaLabel="Keandalan sistem pada beberapa horizon misi"
            data={[
              { name: 'FS-1', key: 'r_fs1', color: PALET.fs[0] },
              { name: 'FS-2', key: 'r_fs2', color: PALET.fs[1] },
              { name: 'FS-3', key: 'r_fs3', color: PALET.fs[2] },
              { name: 'Gabungan (CDU)', key: 'r_gabungan', color: PALET.cdu },
            ].map((s) => ({
              x: barH.map((r: any) => r.horizon),
              y: barH.map((r: any) => r[s.key]),
              type: 'bar',
              name: s.name,
              marker: { color: s.color },
              hovertemplate: `${s.name}<br>%{x} · R = %{y:.4f}<extra></extra>`,
            }))}
            layout={{
              title: 'Keandalan per horizon misi',
              barmode: 'group',
              margin: { l: 56, r: 20, t: 34, b: 58 },
              yaxis: { title: 'Keandalan R(t)', range: [0, 1.05] },
            }}
          />
        </Card>
      </div>

      <Card
        title="Modul E1: Stage RBD"
        subtitle="Keandalan & ketersediaan tiap stage"
        actions={<ExportButtons table="E1_StageRBD" />}
      >
        <DataTable
          columns={STAGE_COLS}
          rows={a.rbd_stages}
          maxHeight="28rem"
          searchable
          searchKeys={['sistem', 'stage', 'konfig']}
        />
      </Card>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card
          title="Modul E2: Sistem RBD per FS dan CDU total"
          actions={<ExportButtons table="E2_SistemRBD" />}
        >
          <DataTable columns={SYS_COLS} rows={a.rbd_system} maxHeight="20rem" />
        </Card>

        <Card title="Modul E4: Umur keandalan" subtitle="Hari sampai R turun ke tingkat tertentu">
          <div className="overflow-auto rounded-lg border border-slate-200">
            <table className="tabel">
              <thead>
                <tr>
                  <th>Sistem</th>
                  {Object.keys(a.reliability_life[0] ?? {})
                    .filter((k) => k !== 'sistem')
                    .map((k) => (
                      <th key={k} className="text-right">
                        R = 0,{k.replace('t_R', '').replace('_hari', '')}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody>
                {a.reliability_life.map((r: any) => (
                  <tr key={r.sistem}>
                    <td className="font-medium">{r.sistem}</td>
                    {Object.keys(r)
                      .filter((k) => k !== 'sistem')
                      .map((k) => (
                        <td key={k} className="angka">
                          {r[k] === null ? '-' : num(r[k], 1)}
                        </td>
                      ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Callout tone="note">
            Contoh pembacaan: kolom “R = 0,90” berisi jumlah hari sampai peluang beroperasi tanpa gangguan
            turun menjadi 90%.
          </Callout>
        </Card>
      </div>

      <Card
        title="Dampak pilihan sumber β terhadap hasil"
        subtitle="β per-equipment (modul C3) vs β konstanta workbook, pada misi 1 bulan"
      >
        <div className="overflow-auto rounded-lg border border-slate-200">
          <table className="tabel">
            <thead>
              <tr>
                <th>Sistem</th>
                <th className="text-right">R(30 hari) β kelas</th>
                <th className="text-right">R(30 hari) β equipment</th>
                <th className="text-right">A_op β kelas</th>
                <th className="text-right">A_op β equipment</th>
              </tr>
            </thead>
            <tbody>
              {a.beta_comparison.map((r: any) => (
                <tr key={r.sistem}>
                  <td className="font-medium">{r.sistem}</td>
                  <td className="angka">{num(r.r30_kelas, 4)}</td>
                  <td className="num font-semibold">{num(r.r30_equip, 4)}</td>
                  <td className="angka">{num(r.aop_kelas, 4)}</td>
                  <td className="angka">{num(r.aop_equip, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Callout tone="info">
          Ketersediaan <strong>tidak</strong> bergantung pada β (hanya MTBF dan MDT), sehingga kedua kolom
          A_op identik. Sebaliknya R(t) sangat peka terhadap β: memakai β per-equipment menghasilkan keandalan
          lebih rendah karena banyak peralatan justru menunjukkan pola kegagalan dini (β &lt; 1), yang tidak
          tertangkap oleh konstanta kelas.
        </Callout>
      </Card>
    </div>
  )
}
