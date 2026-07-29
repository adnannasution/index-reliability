/** Modul F: Monte Carlo ketersediaan sistem (grafik 12). */
import { useEffect } from 'react'
import { PALET, num } from '../lib/format'
import { useStore } from '../store/useStore'
import { Callout, Card, DataTable, Loading, Tombol, type Column } from '../components/ui'
import { Plot } from '../components/charts/Plot'

const COLS: Column<any>[] = [
  { key: 'sistem', header: 'Sistem', width: '8rem' },
  { key: 'a_mean', header: 'A rata-rata', numeric: true, render: (r) => num(r.a_mean, 4) },
  {
    key: 'a_p10',
    header: 'P10',
    numeric: true,
    title: 'Skenario buruk yang masih wajar',
    render: (r) => num(r.a_p10, 4),
  },
  { key: 'a_p50', header: 'P50', numeric: true, render: (r) => num(r.a_p50, 4) },
  { key: 'a_p90', header: 'P90', numeric: true, render: (r) => num(r.a_p90, 4) },
  {
    key: 'downtime_hari_thn',
    header: 'Waktu henti (hari/thn)',
    numeric: true,
    render: (r) => num(r.downtime_hari_thn, 1),
  },
  {
    key: 'downtime_p10_hari_thn',
    header: 'Waktu henti pada P10',
    numeric: true,
    render: (r) => num(r.downtime_p10_hari_thn, 1),
  },
  {
    key: 'a_op_analitik',
    header: 'A_op analitik',
    numeric: true,
    title: 'Pembanding silang dari modul E',
    render: (r) => (r.a_op_analitik === null ? '-' : num(r.a_op_analitik, 4)),
  },
]

export function MonteCarloPage() {
  const mc = useStore((s) => s.mc)
  const loading = useStore((s) => s.mcLoading)
  const run = useStore((s) => s.runMonteCarlo)
  const cfg = useStore((s) => s.config)
  const defaults = useStore((s) => s.defaults)

  useEffect(() => {
    if (!mc && !loading) void run()
  }, [mc, loading, run])

  const reps = cfg.mc_reps ?? defaults?.config?.mc_reps ?? 400

  return (
    <div className="space-y-5">
      <Card
        title="Modul F: Monte Carlo ketersediaan tingkat sistem"
        subtitle={`${reps} replikasi · TTF Weibull, waktu perbaikan lognormal (rerata = MDT), digabung mengikuti logika seri-paralel RBD`}
        actions={
          <Tombol kecil ikon="segarkan" memuat={loading} onClick={() => void run()}>
            Jalankan ulang
          </Tombol>
        }
      >
        {loading && !mc && (
          <Loading label={`Menjalankan ${reps} simulasi satu tahun operasi, jam demi jam…`} rows={5} />
        )}
        {mc && (
          <div className="space-y-4">
            <DataTable columns={COLS} rows={mc.tabel} maxHeight="18rem" />
            <Callout tone="info">
              <strong>P10 adalah nilai yang dipakai untuk perencanaan.</strong> Pada satu dari sepuluh tahun
              operasi, ketersediaan dapat turun sampai nilai tersebut: itulah dasar penentuan tingkat
              persediaan suku cadang dan cadangan produksi. Perencanaan yang hanya memakai rata-rata berarti
              hanya siap untuk tahun yang normal.
            </Callout>
            <Callout tone="note">
              Kolom terakhir adalah A_op analitik dari modul E sebagai <em>pemeriksaan silang</em>: kedua
              metode dihitung dengan cara yang sama sekali berbeda, sehingga kedekatan nilainya menguatkan
              keduanya. Seed simulasi = {mc.seed} sehingga hasil dapat direproduksi persis.
            </Callout>
          </div>
        )}
      </Card>

      {mc && (
        <Card
          title="Grafik 12. Sebaran ketersediaan tahunan"
          subtitle={`Histogram dari ${mc.reps} putaran simulasi; puncak sempit = hasil konsisten`}
        >
          <Plot
            height={430}
            exportName="histogram_availability_mc"
            ariaLabel="Histogram ketersediaan tahunan hasil simulasi Monte Carlo"
            data={[
              { name: 'FS-1', key: 'FS-1', color: PALET.fs[0] },
              { name: 'FS-2', key: 'FS-2', color: PALET.fs[1] },
              { name: 'FS-3', key: 'FS-3', color: PALET.fs[2] },
              { name: 'Gabungan CDU', key: 'CDU', color: '#64748b' },
            ].map((s) => ({
              x: mc.sampel[s.key],
              type: 'histogram',
              name: s.name,
              nbinsx: 30,
              marker: { color: s.color, line: { width: 0 } },
              opacity: 0.6,
              hovertemplate: `${s.name}<br>A ≈ %{x:.3f}<br>%{y} replikasi<extra></extra>`,
            }))}
            layout={{
              title: `Sebaran ketersediaan tahunan dari ${mc.reps} kali simulasi`,
              barmode: 'overlay',
              margin: { l: 58, r: 20, t: 34, b: 62 },
              xaxis: { title: 'Ketersediaan tahunan' },
              yaxis: { title: 'Jumlah replikasi' },
              shapes: mc.tabel
                .filter((r: any) => r.sistem !== 'CDU total')
                .map((r: any, i: number) => ({
                  type: 'line',
                  x0: r.a_p10,
                  x1: r.a_p10,
                  yref: 'paper',
                  y0: 0,
                  y1: 1,
                  line: { color: PALET.fs[i], width: 1.2, dash: 'dot' },
                })),
            }}
          />
          <p className="mt-1 text-xs text-slate-500">Garis putus-putus menandai P10 masing-masing sistem.</p>
        </Card>
      )}
    </div>
  )
}
