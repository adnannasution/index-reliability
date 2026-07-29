/**
 * Modul C / C2 / C3 / D: Weibull per kelas, per FS, per equipment, dan uji tren
 * Laplace. Grafik 5, 6, 7, 8.
 */
import { useState } from 'react'
import { PALET, num, nadaWilayah } from '../lib/format'
import { useStore } from '../store/useStore'
import { Callout, Card, Chip, DataTable, type Column } from '../components/ui'
import { Plot } from '../components/charts/Plot'
import { ExportButtons } from '../components/panels/ExportButtons'

const EQ_COLS: Column<any>[] = [
  { key: 'tag', header: 'Tag', width: '8rem' },
  { key: 'fs', header: 'FS', width: '4.5rem' },
  { key: 'kelas', header: 'Kelas', width: '5.5rem' },
  { key: 'n_cm', header: 'n_CM', numeric: true },
  { key: 'mtbf_hari', header: 'MTBF (hari)', numeric: true, render: (r) => num(r.mtbf_hari, 1) },
  {
    key: 'beta_mrr',
    header: 'β MRR',
    numeric: true,
    render: (r) => num(r.beta_mrr, 3),
    title: 'Median Rank Regression (Abernethy)',
  },
  { key: 'gof_r2', header: 'R²', numeric: true, render: (r) => num(r.gof_r2, 3) },
  {
    key: 'beta_mlec',
    header: 'β MLE†',
    numeric: true,
    render: (r) => num(r.beta_mlec, 3),
    title: 'MLE tersensor × faktor unbias Thoman-Bain-Antle',
  },
  {
    key: 'beta_crow_amsaa',
    header: 'β Crow',
    numeric: true,
    render: (r) => num(r.beta_crow_amsaa, 3),
    title: 'Crow-AMSAA: diagnostik tren, bukan untuk R(t)',
  },
  { key: 'prior_kelas', header: 'prior', numeric: true, render: (r) => num(r.prior_kelas, 3) },
  {
    key: 'bobot_w',
    header: 'w',
    numeric: true,
    render: (r) => num(r.bobot_w, 2),
    title: 'Bobot kredibilitas Bühlmann w = m/(m+M₀)',
  },
  {
    key: 'beta_final',
    header: 'β final',
    numeric: true,
    render: (r) => <strong>{num(r.beta_final, 3)}</strong>,
  },
  { key: 'eta_final_j', header: 'η (jam)', numeric: true, render: (r) => num(r.eta_final_j, 0) },
  {
    key: 'region',
    header: 'Wilayah',
    render: (r) => <Chip className={nadaWilayah(r.region)}>{r.region}</Chip>,
  },
]

function ProbPlotGrid({ fits, title }: { fits: any[]; title: string }) {
  const usable = fits.filter((f) => f.plot_x?.length > 1)
  if (!usable.length)
    return <p className="py-6 text-center text-xs text-slate-500">Data TBF belum cukup (perlu n ≥ 4).</p>
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {usable.map((f) => (
        <Plot
          key={f.nama}
          height={230}
          exportName={`weibull_${f.nama}`}
          ariaLabel={`Plot probabilitas Weibull ${f.nama}`}
          data={[
            {
              x: f.plot_x,
              y: f.plot_y,
              type: 'scatter',
              mode: 'markers',
              name: 'data',
              marker: { color: PALET.biru, size: 6 },
              hovertemplate: 'ln t = %{x:.3f}<br>y = %{y:.3f}<extra></extra>',
            },
            {
              x: f.plot_x,
              y: f.plot_yhat,
              type: 'scatter',
              mode: 'lines',
              name: 'regresi',
              line: { color: PALET.kuning, width: 2 },
              hoverinfo: 'skip',
            },
          ]}
          layout={{
            title: `${f.nama}: β=${num(f.beta, 2)}, R²=${num(f.gof_r2, 3)}, n=${f.n_tbf}`,
            showlegend: false,
            margin: { l: 50, r: 14, t: 30, b: 40 },
            xaxis: { title: 'ln(TBF)' },
            yaxis: { title: 'ln(−ln(1−F))' },
          }}
        />
      ))}
      <div className="col-span-full">
        <Callout tone="note" title={title}>
          Sumbu-x = ln(TBF), sumbu-y = ln(−ln(1−F)) dengan median rank Bernard F=(i−0,3)/(n+0,4). Pada skala
          ini distribusi Weibull menjadi garis lurus: <strong>kemiringan garis = β</strong> dan R² menyatakan
          kecocokan. Ref: Abernethy, <em>The New Weibull Handbook</em>.
        </Callout>
      </div>
    </div>
  )
}

export function WeibullPage() {
  const a = useStore((s) => s.analysis)!
  const [showMrr, setShowMrr] = useState(false)
  const ex = a.mrr_example

  const eqTop = a.weibull_equipment.filter((r: any) => r.beta_crow_amsaa !== null).slice(0, 12)

  return (
    <div className="space-y-5">
      <Card
        title="Grafik 5. Plot probabilitas Weibull per kelas peralatan"
        subtitle="Modul C: MLE dengan η ter-profil pada TBF gabungan tiap kelas (Nelson 1982)"
        actions={<ExportButtons table="C_WeibullKelas" />}
      >
        <ProbPlotGrid fits={a.weibull_class} title="Cara membaca plot probabilitas Weibull" />
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1fr_minmax(0,26rem)]">
        <Card title="Grafik 5b. Plot probabilitas per Functional System" subtitle="Modul C2">
          <ProbPlotGrid fits={a.weibull_fs} title="Plot per Functional System" />
        </Card>

        <Card
          title="Grafik 6. β per FS dengan CI 95%"
          subtitle="Apakah ketiga sistem sudah benar-benar memasuki fase aus?"
        >
          <Plot
            height={330}
            exportName="beta_fs_ci"
            ariaLabel="Beta Weibull per Functional System dengan selang kepercayaan 95 persen"
            data={[
              {
                x: a.weibull_fs.map((r: any) => r.nama),
                y: a.weibull_fs.map((r: any) => r.beta),
                error_y: {
                  type: 'data',
                  symmetric: false,
                  array: a.weibull_fs.map((r: any) => (r.beta_hi ?? r.beta) - r.beta),
                  arrayminus: a.weibull_fs.map((r: any) => r.beta - (r.beta_lo ?? r.beta)),
                  color: PALET.biru,
                  thickness: 1.6,
                  width: 8,
                },
                type: 'scatter',
                mode: 'markers',
                marker: { color: PALET.biru, size: 11 },
                hovertemplate: '%{x}<br>β = %{y:.3f}<extra></extra>',
              },
            ]}
            layout={{
              title: 'β Weibull (gabungan TBF dalam FS)',
              showlegend: false,
              margin: { l: 54, r: 20, t: 34, b: 44 },
              yaxis: { title: 'β' },
              shapes: [
                {
                  type: 'line',
                  xref: 'paper',
                  x0: 0,
                  x1: 1,
                  y0: 1,
                  y1: 1,
                  line: { color: PALET.kuning, width: 1.4, dash: 'dash' },
                },
              ],
              annotations: [
                {
                  xref: 'paper',
                  x: 1,
                  y: 1,
                  text: 'β = 1',
                  showarrow: false,
                  xanchor: 'left',
                  font: { size: 10, color: PALET.kuning },
                },
              ],
            }}
          />
          <Callout tone="info">
            Batas bawah CI di atas 1 berarti sistem itu <strong>sungguh</strong> memburuk (aus) secara
            statistik. Bila CI melingkupi 1, pola kegagalan belum dapat dibedakan dari acak: penggantian
            berkala belum tentu bermanfaat.
          </Callout>
        </Card>
      </div>

      {a.mrr_plots?.length > 0 && (
        <Card
          title="Grafik 7. Plot probabilitas Weibull per equipment"
          subtitle="Enam tag terkaya data; MRR dengan koreksi rank Johnson untuk sensor kanan"
        >
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {a.mrr_plots.map((p: any) => (
              <Plot
                key={p.tag}
                height={230}
                exportName={`weibull_${p.tag}`}
                ariaLabel={`Plot probabilitas Weibull ${p.tag}`}
                data={[
                  {
                    x: p.x,
                    y: p.y,
                    type: 'scatter',
                    mode: 'markers',
                    marker: { color: PALET.biru, size: 7 },
                    hovertemplate: 'ln t = %{x:.3f}<br>y = %{y:.3f}<extra></extra>',
                  },
                  {
                    x: p.fit_x,
                    y: p.fit_y,
                    type: 'scatter',
                    mode: 'lines',
                    line: { color: PALET.kuning, width: 2 },
                    hoverinfo: 'skip',
                  },
                ]}
                layout={{
                  title: `${p.tag}: β=${num(p.beta_mrr, 2)}, R²=${num(p.r2, 3)}`,
                  showlegend: false,
                  margin: { l: 50, r: 14, t: 30, b: 40 },
                  xaxis: { title: 'ln(TBF)' },
                  yaxis: { title: 'ln(−ln(1−F))' },
                }}
              />
            ))}
          </div>
        </Card>
      )}

      <Card
        title="Grafik 8. β renewal vs β Crow-AMSAA per equipment"
        subtitle="Dua cara membaca perilaku kegagalan: bentuk siklus perbaikan vs tren waktu kalender"
      >
        <Plot
          height={400}
          exportName="beta_renewal_vs_crow"
          ariaLabel="Perbandingan beta renewal dan beta Crow-AMSAA per peralatan"
          data={[
            {
              x: eqTop.map((r: any) => r.tag),
              y: eqTop.map((r: any) => r.beta_final),
              type: 'bar',
              name: 'β renewal (untuk R(t))',
              marker: { color: PALET.biru },
              hovertemplate: '%{x}<br>β renewal = %{y:.3f}<extra></extra>',
            },
            {
              x: eqTop.map((r: any) => r.tag),
              y: eqTop.map((r: any) => r.beta_crow_amsaa),
              type: 'bar',
              name: 'β Crow-AMSAA (tren)',
              marker: { color: PALET.kuning },
              hovertemplate: '%{x}<br>β Crow-AMSAA = %{y:.3f}<extra></extra>',
            },
          ]}
          layout={{
            title: 'β renewal dan β Crow-AMSAA',
            barmode: 'group',
            margin: { l: 56, r: 20, t: 34, b: 96 },
            xaxis: { tickangle: -45 },
            yaxis: { title: 'β' },
            shapes: [
              {
                type: 'line',
                xref: 'paper',
                x0: 0,
                x1: 1,
                y0: 1,
                y1: 1,
                line: { color: '#334155', width: 1.2, dash: 'dash' },
              },
            ],
          }}
        />
        <Callout tone="info">
          β renewal ≈ 1 berarti siklus perbaikan bersifat acak, tetapi β Crow-AMSAA &gt; 1 berarti{' '}
          <strong>kegagalan menggerus lebih cepat pada waktu kalender</strong>: sistem repairable sedang
          memburuk. Keduanya tidak saling menggantikan: β renewal dipakai untuk R(t), β Crow-AMSAA hanya
          sebagai diagnostik tren (Crow 1975; MIL-HDBK-189).
        </Callout>
      </Card>

      <Card
        title="Modul C3: β Weibull per equipment"
        subtitle="β final = w·β_MRR + (1−w)·prior kelas dengan w = m/(m+M₀) (kredibilitas Bühlmann); η = MTBF / Γ(1+1/β)"
        actions={<ExportButtons table="C3_BetaEquipment" />}
      >
        <DataTable
          columns={EQ_COLS}
          rows={a.weibull_equipment}
          maxHeight="32rem"
          searchable
          searchKeys={['tag', 'fs', 'kelas']}
          initialSort={{ key: 'n_cm', dir: 'desc' }}
        />
        <p className="mt-2 text-xs text-slate-500">
          † β MLE dikalikan faktor unbias sampel kecil Thoman-Bain-Antle (1969); kosong bila solusi menempel
          batas sehingga shape tidak teridentifikasi.
        </p>
      </Card>

      {ex?.rows?.length > 0 && (
        <Card
          title="Contoh perhitungan langkah demi langkah"
          subtitle={`Tag terkaya data: ${ex.tag}: transparansi akademik penuh`}
          actions={
            <button className="btn btn-garis btn-kecil" onClick={() => setShowMrr((v) => !v)}>
              {showMrr ? 'Sembunyikan' : 'Tampilkan'} tabel MRR
            </button>
          }
        >
          <div className="space-y-3">
            <p className="text-xs leading-relaxed text-slate-600">
              {ex.tag} memiliki <strong>{ex.n_cm}</strong> kegagalan sehingga terbentuk{' '}
              <strong>{ex.n_tbf}</strong> nilai TBF, ditambah satu sensor kanan (waktu sejak kegagalan
              terakhir sampai akhir jendela). Regresi Y atas X memberi β_MRR ={' '}
              <span className="font-mono font-semibold">{num(ex.beta_mrr, 4)}</span> dengan R² ={' '}
              <span className="font-mono">{num(ex.r2, 4)}</span>. Setelah pembobotan kredibilitas diperoleh β
              final = <span className="font-mono font-semibold">{num(ex.beta_final, 4)}</span> dan η ={' '}
              <span className="font-mono">{num(ex.eta_final, 0)}</span> jam. Sebagai pembanding, MLE tersensor
              terkoreksi = <span className="font-mono">{num(ex.beta_mlec, 4)}</span> dan Crow-AMSAA ={' '}
              <span className="font-mono">{num(ex.beta_crow, 4)}</span>.
            </p>
            {showMrr && (
              <div className="overflow-auto rounded-lg border border-slate-200">
                <table className="tabel">
                  <thead>
                    <tr>
                      <th>i</th>
                      <th className="text-right">TBF tᵢ (jam)</th>
                      <th className="text-right">adj-rank</th>
                      <th className="text-right">median rank</th>
                      <th className="text-right">x = ln t</th>
                      <th className="text-right">y = ln(−ln(1−MR))</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ex.rows.map((r: any) => (
                      <tr key={r.i}>
                        <td>{r.i}</td>
                        <td className="angka">{num(r.tbf_jam, 1)}</td>
                        <td className="angka">{num(r.adj_rank, 3)}</td>
                        <td className="angka">{num(r.median_rank, 4)}</td>
                        <td className="angka">{num(r.x_ln_t, 4)}</td>
                        <td className="angka">{num(r.y, 4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </Card>
      )}

      <Card
        title="Modul D: Uji tren Laplace"
        subtitle="U = (Σtᵢ − nT/2) / (T√(n/12)) ; p = erfc(|U|/√2). Ref: Ascher & Feingold (1984)"
        actions={<ExportButtons table="D_TrenLaplace" />}
      >
        <DataTable
          columns={[
            { key: 'tingkat', header: 'Tingkat', width: '6rem' },
            { key: 'nama', header: 'Nama', width: '8rem' },
            { key: 'n_gagal', header: 'n gagal', numeric: true },
            { key: 'u_laplace', header: 'U', numeric: true, render: (r) => num(r.u_laplace, 2) },
            { key: 'p_value', header: 'p-value', numeric: true, render: (r) => num(r.p_value, 3) },
            {
              key: 'tafsiran',
              header: 'Tafsiran',
              render: (r) => (
                <Chip
                  className={
                    r.tafsiran.includes('Memburuk')
                      ? 'bg-merah-50 text-merah-700'
                      : r.tafsiran.includes('Membaik')
                        ? 'bg-hijau-50 text-hijau-700'
                        : 'bg-slate-100 text-slate-600'
                  }
                >
                  {r.tafsiran}
                </Chip>
              ),
            },
          ]}
          rows={a.laplace}
          maxHeight="24rem"
        />
        <Callout tone="note">
          U &gt; +1,96 = laju kegagalan memburuk (IFR) · U &lt; −1,96 = membaik (DFR) · selainnya stasioner
          (CFR) pada taraf 5%.
        </Callout>
      </Card>
    </div>
  )
}
