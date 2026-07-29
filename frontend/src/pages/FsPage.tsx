/** Modul B2/B3/B4: rekap Functional System, heatmap, Pareto per FS (grafik 2, 3, 4). */
import { PALET, num, pct } from '../lib/format'
import { useStore } from '../store/useStore'
import { Callout, Card, DataTable, type Column } from '../components/ui'
import { Plot } from '../components/charts/Plot'
import { ExportButtons } from '../components/panels/ExportButtons'

const COLS: Column<any>[] = [
  { key: 'sistem', header: 'Sistem', width: '6rem' },
  { key: 'n_tag', header: 'n tag', numeric: true },
  { key: 'n_cm', header: 'n_CM', numeric: true },
  { key: 'n_pm', header: 'n_PM', numeric: true },
  { key: 'share_cm_pct', header: 'Pangsa CM', numeric: true, render: (r) => pct(r.share_cm_pct) },
  {
    key: 'lambda_seri_perjam',
    header: 'λ seri (/jam)',
    numeric: true,
    render: (r) => (r.lambda_seri_perjam ? r.lambda_seri_perjam.toExponential(3).replace('.', ',') : '-'),
  },
  { key: 'mtbf_seri_jam', header: 'MTBF seri (jam)', numeric: true, render: (r) => num(r.mtbf_seri_jam, 1) },
  {
    key: 'mtbf_seri_hari',
    header: 'MTBF seri (hari)',
    numeric: true,
    render: (r) => num(r.mtbf_seri_hari, 1),
  },
  { key: 'e_gagal_per_thn', header: 'E[gagal/thn]', numeric: true, render: (r) => num(r.e_gagal_per_thn, 1) },
]

export function FsPage() {
  const a = useStore((s) => s.analysis)!
  const fs123 = a.functional_system.filter((r: any) => r.fs !== 0)
  const names = fs123.map((r: any) => r.sistem)

  const worst = fs123.reduce((m: any, r: any) => (r.n_cm > m.n_cm ? r : m), fs123[0])

  return (
    <div className="space-y-5">
      <Card
        title="Grafik 2. Perbandingan antar Functional System"
        subtitle="Beban kegagalan, jarak antar gangguan, dan perkiraan gangguan tahunan"
        actions={<ExportButtons table="B2_FunctionalSystem" />}
      >
        <div className="grid gap-3 lg:grid-cols-3">
          <Plot
            height={310}
            exportName="fs_jumlah_kegagalan"
            ariaLabel="Jumlah kegagalan korektif per Functional System"
            data={[
              {
                x: names,
                y: fs123.map((r: any) => r.n_cm),
                type: 'bar',
                marker: { color: PALET.biru },
                text: fs123.map((r: any) => String(r.n_cm)),
                textposition: 'outside',
                hovertemplate: '%{x}<br>%{y} kegagalan<extra></extra>',
              },
            ]}
            layout={{
              title: 'Pembagian beban kegagalan',
              showlegend: false,
              yaxis: { title: 'Kegagalan korektif' },
              margin: { l: 52, r: 16, t: 34, b: 42 },
            }}
          />
          <Plot
            height={310}
            exportName="fs_mtbf"
            ariaLabel="MTBF sistem per Functional System dalam hari"
            data={[
              {
                x: names,
                y: fs123.map((r: any) => r.mtbf_seri_hari),
                type: 'bar',
                marker: { color: PALET.hijau },
                text: fs123.map((r: any) => num(r.mtbf_seri_hari, 1)),
                textposition: 'outside',
                hovertemplate: '%{x}<br>MTBF %{y:.1f} hari<extra></extra>',
              },
            ]}
            layout={{
              title: 'Jarak rata-rata antar gangguan',
              showlegend: false,
              yaxis: { title: 'MTBF sistem (hari)' },
              margin: { l: 52, r: 16, t: 34, b: 42 },
            }}
          />
          <Plot
            height={310}
            exportName="fs_gagal_per_tahun"
            ariaLabel="Perkiraan kegagalan per tahun per Functional System"
            data={[
              {
                x: names,
                y: fs123.map((r: any) => r.e_gagal_per_thn),
                type: 'bar',
                marker: { color: PALET.kuning },
                text: fs123.map((r: any) => num(r.e_gagal_per_thn, 1)),
                textposition: 'outside',
                hovertemplate: '%{x}<br>%{y:.1f} kejadian/tahun<extra></extra>',
              },
            ]}
            layout={{
              title: 'Perkiraan gangguan tiap tahun',
              showlegend: false,
              yaxis: { title: 'Kegagalan per tahun' },
              margin: { l: 52, r: 16, t: 34, b: 42 },
            }}
          />
        </div>
        <Callout tone="info">
          <strong>{worst.sistem}</strong> menanggung {worst.n_cm} dari {a.pareto.total_cm} kegagalan (
          {pct(worst.share_cm_pct)}) dengan MTBF sistem {num(worst.mtbf_seri_hari, 1)} hari.{' '}
          <span className="text-slate-500">
            MTBF_seri = T_obs / Σn_CM(FS) adalah jarak rata-rata antar kegagalan APA PUN di dalam sistem itu:
            bukan MTBF satu peralatan.
          </span>
        </Callout>
      </Card>

      <Card title="Modul B2: Rekap per Functional System">
        <DataTable columns={COLS} rows={a.functional_system} maxHeight="18rem" />
      </Card>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card
          title="Grafik 3. Peta panas FS × kelas peralatan"
          subtitle="Di mana kegagalan menumpuk, menurut sistem dan jenis peralatan"
        >
          <Plot
            height={340}
            exportName="heatmap_fs_kelas"
            ariaLabel="Peta panas jumlah kegagalan menurut Functional System dan kelas peralatan"
            data={[
              {
                z: a.crosstab.values,
                x: a.crosstab.classes,
                y: a.crosstab.rows,
                type: 'heatmap',
                colorscale: [
                  [0, '#f8fafc'],
                  [0.35, '#c7d7e8'],
                  [0.7, '#5b86b5'],
                  [1, '#1F3864'],
                ],
                showscale: true,
                colorbar: { title: 'n_CM', thickness: 12, len: 0.8 },
                hovertemplate: '%{y} · %{x}<br>%{z} kegagalan<extra></extra>',
              },
              {
                z: a.crosstab.values,
                x: a.crosstab.classes,
                y: a.crosstab.rows,
                type: 'scatter',
                mode: 'text',
                text: a.crosstab.values.flat().map(String),
                hoverinfo: 'skip',
                showlegend: false,
                visible: false,
              },
            ]}
            layout={{
              title: 'Konsentrasi kegagalan',
              margin: { l: 62, r: 16, t: 34, b: 76 },
              xaxis: { tickangle: -25, title: '' },
              yaxis: { title: '', autorange: 'reversed' },
              annotations: a.crosstab.rows.flatMap((row: string, i: number) =>
                a.crosstab.classes.map((col: string, j: number) => ({
                  x: col,
                  y: row,
                  text: a.crosstab.values[i][j] > 0 ? String(a.crosstab.values[i][j]) : '',
                  showarrow: false,
                  font: {
                    size: 11,
                    color:
                      a.crosstab.values[i][j] > Math.max(...a.crosstab.values.flat()) * 0.55
                        ? '#fff'
                        : '#1e293b',
                  },
                })),
              ),
            }}
          />
        </Card>

        <Card
          title="Grafik 4. Pareto per Functional System"
          subtitle="Delapan penyumbang teratas tiap sistem"
        >
          <div className="space-y-2">
            {(['FS-1', 'FS-2', 'FS-3'] as const).map((key, idx) => {
              const rows = (a.pareto.per_fs[key] ?? []).slice(0, 8).reverse()
              return (
                <Plot
                  key={key}
                  height={150}
                  exportName={`pareto_${key}`}
                  ariaLabel={`Pareto peralatan pada ${key}`}
                  data={[
                    {
                      x: rows.map((r: any) => r.n_cm),
                      y: rows.map((r: any) => r.tag.replace(a.meta.unit_prefix, '')),
                      type: 'bar',
                      orientation: 'h',
                      marker: { color: PALET.fs[idx] },
                      hovertemplate: '%{y}<br>%{x} kegagalan<extra></extra>',
                    },
                  ]}
                  layout={{
                    title: `${key}: ${fs123.find((f: any) => f.sistem === key)?.n_cm ?? 0} kegagalan korektif`,
                    showlegend: false,
                    margin: { l: 72, r: 16, t: 26, b: 30 },
                    xaxis: { title: '' },
                    yaxis: { title: '', tickfont: { size: 9.5 } },
                  }}
                />
              )
            })}
          </div>
        </Card>
      </div>
    </div>
  )
}
