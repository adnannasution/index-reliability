/** Modul B: keandalan per equipment + Pareto (grafik 1). */
import { PALET, num, nadaWilayah } from '../lib/format'
import { useStore } from '../store/useStore'
import { Callout, Card, Chip, DataTable, type Column } from '../components/ui'
import { Plot } from '../components/charts/Plot'
import { ExportButtons } from '../components/panels/ExportButtons'

const COLS: Column<any>[] = [
  { key: 'tag', header: 'Tag', width: '8rem' },
  { key: 'fs', header: 'Sistem', width: '5rem' },
  { key: 'kelas', header: 'Kelas', width: '6rem' },
  {
    key: 'kritikalitas',
    header: 'Krit.',
    width: '4rem',
    render: (r) => <span className="font-mono">{r.kritikalitas || '-'}</span>,
  },
  { key: 'n_cm', header: 'n_CM', numeric: true, title: 'Jumlah kegagalan korektif (M1+M2)' },
  { key: 'n_pm', header: 'n_PM', numeric: true, title: 'Jumlah notifikasi preventif (M3)' },
  {
    key: 'mtbf_hari',
    header: 'MTBF (hari)',
    numeric: true,
    title: 'MTBF = T_obs / n_CM (ISO 14224)',
    render: (r) => (r.mtbf_hari === null ? '∞' : num(r.mtbf_hari, 1)),
  },
  {
    key: 'gagal_per_thn',
    header: 'Gagal/thn',
    numeric: true,
    title: 'Ekspektasi kegagalan per tahun = 8760 · λ',
    render: (r) => num(r.gagal_per_thn, 1),
  },
  { key: 'mdt_jam', header: 'MDT (jam)', numeric: true, render: (r) => num(r.mdt_jam, 0) },
  {
    key: 'flags',
    header: 'Catatan',
    render: (r) => (
      <span className="flex gap-1">
        {r.spof && <Chip className="bg-merah-50 text-merah-700">SPOF</Chip>}
        {r.redundan && <Chip className="bg-hijau-50 text-hijau-700">redundan</Chip>}
      </span>
    ),
  },
]

export function EquipmentPage() {
  const a = useStore((s) => s.analysis)!
  const setFocus = useStore((s) => s.setFocus)

  const top = a.pareto.equipment.slice(0, 15)
  const cut80 = a.pareto.equipment.findIndex((r: any) => r.kumulatif_pct >= 80) + 1

  return (
    <div className="space-y-5">
      <Card
        title="Grafik 1. Pareto peralatan"
        subtitle="Peralatan mana yang paling sering gagal (aturan 80/20)"
        actions={<ExportButtons table="B_Equipment" />}
      >
        <Plot
          height={420}
          exportName="pareto_equipment"
          ariaLabel="Diagram Pareto jumlah kegagalan korektif per peralatan"
          data={[
            {
              x: top.map((r: any) => r.tag),
              y: top.map((r: any) => r.n_cm),
              type: 'bar',
              name: 'Kegagalan korektif',
              marker: { color: PALET.biru },
              hovertemplate: '%{x}<br>%{y} kegagalan<extra></extra>',
            },
            {
              x: top.map((r: any) => r.tag),
              y: top.map((r: any) => r.kumulatif_pct),
              type: 'scatter',
              mode: 'lines+markers',
              name: 'Kumulatif (%)',
              yaxis: 'y2',
              line: { color: PALET.kuning, width: 2.2 },
              marker: { size: 6 },
              hovertemplate: '%{x}<br>kumulatif %{y:.1f}%<extra></extra>',
            },
          ]}
          layout={{
            title: 'Peralatan mana yang paling sering gagal',
            margin: { l: 56, r: 62, t: 34, b: 96 },
            xaxis: { tickangle: -45, title: '' },
            yaxis: { title: 'Jumlah kegagalan korektif' },
            yaxis2: {
              title: 'Kumulatif (%)',
              overlaying: 'y',
              side: 'right',
              range: [0, 105],
              gridcolor: 'rgba(0,0,0,0)',
            },
            shapes: [
              {
                type: 'line',
                xref: 'paper',
                x0: 0,
                x1: 1,
                yref: 'y2',
                y0: 80,
                y1: 80,
                line: { color: PALET.abu, width: 1.2, dash: 'dash' },
              },
            ],
            annotations: [
              {
                xref: 'paper',
                x: 1,
                yref: 'y2',
                y: 80,
                text: '80%',
                showarrow: false,
                xanchor: 'left',
                font: { size: 10, color: PALET.abu },
              },
            ],
          }}
        />
        <Callout tone="info">
          {cut80 > 0 ? (
            <>
              <strong>{cut80} peralatan</strong> dari {a.equipment.filter((e: any) => e.n_cm > 0).length} yang
              pernah gagal sudah menyumbang 80% dari total {a.pareto.total_cm} kegagalan korektif. Menangani
              kelompok kecil ini memberi dampak terbesar.
            </>
          ) : (
            'Distribusi kegagalan relatif merata sehingga aturan 80/20 tidak menonjol.'
          )}
        </Callout>
      </Card>

      <Card
        title="Modul B: Keandalan per equipment"
        subtitle="MTBF = T_obs / n_CM · λ = n_CM / T_obs · gagal/tahun = 8760 λ (ISO 14224:2016). Klik baris untuk membuka detail."
      >
        <DataTable
          columns={COLS}
          rows={a.equipment}
          maxHeight="34rem"
          searchable
          searchKeys={['tag', 'fs', 'kelas', 'kritikalitas']}
          initialSort={{ key: 'n_cm', dir: 'desc' }}
          onRowClick={(r) => void setFocus(r.tag)}
          highlightRow={(r) => r.spof && r.n_cm > 0}
        />
        <p className="mt-2 text-xs text-slate-500">
          Baris bersorot kuning = single point of failure yang pernah gagal. MTBF ∞ berarti peralatan tidak
          memiliki kegagalan korektif pada jendela ini.
        </p>
      </Card>

      <Card title="Sebaran kelas peralatan" subtitle="Kelas diturunkan dari pola tag (port tagType MATLAB)">
        <div className="grid gap-4 md:grid-cols-2">
          <Plot
            height={300}
            exportName="kegagalan_per_kelas"
            ariaLabel="Jumlah kegagalan menurut kelas peralatan"
            data={[
              {
                labels: a.weibull_class.map((r: any) => r.nama),
                values: a.crosstab.classes.map((_c: string, i: number) =>
                  a.crosstab.values.reduce((s: number, row: number[]) => s + row[i], 0),
                ),
                type: 'pie',
                hole: 0.45,
                marker: {
                  colors: [PALET.merah, PALET.biru, PALET.hijau, PALET.kuning, PALET.gelap, PALET.abu],
                },
                textinfo: 'label+percent',
                hovertemplate: '%{label}<br>%{value} kegagalan (%{percent})<extra></extra>',
              },
            ]}
            layout={{ title: 'Pangsa kegagalan menurut kelas', showlegend: false, margin: { t: 34, b: 20 } }}
          />
          <div className="overflow-auto">
            <table className="tabel">
              <thead>
                <tr>
                  <th>Kelas</th>
                  <th className="text-right">n TBF</th>
                  <th className="text-right">β</th>
                  <th className="text-right">η (jam)</th>
                  <th>Wilayah</th>
                </tr>
              </thead>
              <tbody>
                {a.weibull_class.map((r: any) => (
                  <tr key={r.nama}>
                    <td className="font-medium">{r.nama}</td>
                    <td className="angka">{r.n_tbf}</td>
                    <td className="angka">{num(r.beta, 3)}</td>
                    <td className="angka">{num(r.eta_jam, 0)}</td>
                    <td>
                      <Chip className={nadaWilayah(r.region)}>{r.region}</Chip>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>
    </div>
  )
}
