/**
 * Modul G: optimasi interval pemeliharaan preventif.
 *
 * Menyajikan tabel bad actor tiap Functional System (reproduksi modul G MATLAB)
 * dan kurva laju biaya untuk peralatan mana pun yang dipilih pengguna.
 */
import { useEffect } from 'react'
import { PALET, nadaWilayah, num, pct } from '../lib/format'
import { useStore } from '../store/useStore'
import { Callout, Card, Chip, DataTable, EmptyState, Loading, Tombol, type Column } from '../components/ui'
import { Plot } from '../components/charts/Plot'
import { TagPicker } from '../components/panels/TagPicker'

const KOLOM_G: Column<any>[] = [
  { key: 'sistem', header: 'Sistem', width: '5.5rem' },
  { key: 'bad_actor', header: 'Bad actor', width: '8rem' },
  { key: 'beta', header: 'β', numeric: true, render: (r) => num(r.beta, 2) },
  { key: 'eta_jam', header: 'η (jam)', numeric: true, render: (r) => num(r.eta_jam, 0) },
  {
    key: 'tau_opt_hari',
    header: 'τ* (hari)',
    numeric: true,
    render: (r) => <strong>{num(r.tau_opt_hari, 0)}</strong>,
  },
  {
    key: 'penghematan_pct',
    header: 'Penghematan',
    numeric: true,
    title: 'Nilai bertanda terhadap run to failure',
    render: (r) => (
      <span className={r.penghematan_pct > 0.05 ? 'text-hijau-700' : 'text-slate-500'}>
        {pct(r.penghematan_pct)}
      </span>
    ),
  },
  {
    key: 'penghematan_efektif_pct',
    header: 'Dapat direalisasikan',
    numeric: true,
    render: (r) => pct(r.penghematan_efektif_pct),
  },
  { key: 'sumber_biaya', header: 'Sumber biaya', render: (r) => <Chip>{r.sumber_biaya}</Chip> },
  { key: 'rekomendasi', header: 'Rekomendasi' },
]

const KOLOM_KURVA: Column<any>[] = [
  { key: 'tag', header: 'Tag', width: '8rem' },
  { key: 'kelas', header: 'Kelas', width: '6rem' },
  { key: 'n_cm', header: 'Kegagalan', numeric: true },
  { key: 'beta', header: 'β', numeric: true, render: (r) => num(r.beta, 3) },
  {
    key: 'wilayah',
    header: 'Pola kegagalan',
    render: (r) => <Chip className={nadaWilayah(r.wilayah)}>{r.wilayah}</Chip>,
  },
  { key: 'mtbf_hari', header: 'MTBF (hari)', numeric: true, render: (r) => num(r.mtbf_hari, 1) },
  {
    key: 'tau_opt_hari',
    header: 'τ* (hari)',
    numeric: true,
    render: (r) => (
      <span className={r.optimum_di_batas ? 'text-slate-400' : 'font-semibold text-slate-900'}>
        {num(r.tau_opt_hari, 0)}
        {r.optimum_di_batas ? '*' : ''}
      </span>
    ),
  },
  { key: 'r_pada_tau_opt', header: 'R pada τ*', numeric: true, render: (r) => num(r.r_pada_tau_opt, 4) },
  {
    key: 'penghematan_pct',
    header: 'Penghematan',
    numeric: true,
    render: (r) => (
      <span className={r.penghematan_pct > 0.05 ? 'text-hijau-700' : 'text-slate-500'}>
        {pct(r.penghematan_pct)}
      </span>
    ),
  },
]

export function PmPage() {
  const pm = useStore((s) => s.pm)
  const loading = useStore((s) => s.pmLoading)
  const run = useStore((s) => s.runPmOptimize)

  const pmTags = useStore((s) => s.pmTags)
  const setPmTags = useStore((s) => s.setPmTags)
  const curves = useStore((s) => s.pmCurves)
  const curvesLoading = useStore((s) => s.pmCurvesLoading)
  const loadCurves = useStore((s) => s.loadPmCurves)

  useEffect(() => {
    if (!pm && !loading) void run()
  }, [pm, loading, run])

  // Pilihan awal: bad actor tiap Functional System, sama seperti modul G.
  useEffect(() => {
    if (pmTags.length === 0 && pm?.tabel?.length) {
      setPmTags(pm.tabel.map((r: any) => r.bad_actor))
    }
  }, [pm, pmTags.length, setPmTags])

  useEffect(() => {
    if (pmTags.length > 0 && !curves && !curvesLoading) void loadCurves()
  }, [pmTags, curves, curvesLoading, loadCurves])

  return (
    <div className="space-y-5">
      <Card
        title="Modul G: bad actor tiap Functional System"
        subtitle="Model age replacement Barlow dan Hunter (1960), yaitu C(τ) sama dengan Cp·R(τ) ditambah Cf·(1−R(τ)), dibagi integral R(t)dt dari 0 sampai τ"
        actions={
          <Tombol kecil ikon="segarkan" memuat={loading} onClick={() => void run()}>
            Hitung ulang
          </Tombol>
        }
      >
        {loading && !pm && <Loading label="Menghitung kurva laju biaya untuk setiap bad actor" rows={4} />}
        {pm && (
          <div className="space-y-4">
            <DataTable columns={KOLOM_G} rows={pm.tabel} maxHeight="16rem" />
            <Callout tone="warning" title="Cara membaca kolom penghematan">
              {pm.catatan}
            </Callout>
          </div>
        )}
      </Card>

      <Card
        title="Pilih peralatan yang ingin ditampilkan kurvanya"
        subtitle="Kurva dapat dibuat untuk peralatan mana pun yang memiliki riwayat kegagalan, tidak terbatas pada bad actor"
        actions={
          <Tombol
            kecil
            varian="utama"
            ikon="grafik-garis"
            memuat={curvesLoading}
            disabled={pmTags.length === 0}
            onClick={() => void loadCurves(true)}
          >
            Tampilkan kurva
          </Tombol>
        }
      >
        <TagPicker terpilih={pmTags} onChange={setPmTags} maks={24} label="Peralatan" />
      </Card>

      {pmTags.length === 0 && (
        <EmptyState
          ikon="grafik-garis"
          title="Belum ada peralatan dipilih"
          message="Pilih satu atau beberapa peralatan pada panel di atas untuk menampilkan kurva laju biaya terhadap interval penggantiannya."
        />
      )}

      {curvesLoading && !curves && (
        <Card title="Menyiapkan kurva">
          <Loading label={`Menghitung kurva untuk ${pmTags.length} peralatan`} rows={4} />
        </Card>
      )}

      {curves?.kurva?.length > 0 && (
        <>
          <Card
            title={`Kurva laju biaya terhadap interval, ${curves.kurva.length} peralatan`}
            subtitle="Titik menandai biaya terendah, garis putus putus menandai laju biaya run to failure"
          >
            <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
              {curves.kurva.map((c: any) => (
                <Plot
                  key={c.tag}
                  height={290}
                  exportName={`interval_${c.tag}`}
                  ariaLabel={`Kurva laju biaya terhadap interval untuk ${c.tag}`}
                  data={[
                    {
                      x: c.tau_hari,
                      y: c.biaya_tahunan,
                      type: 'scatter',
                      mode: 'lines',
                      name: 'C(τ)',
                      line: { color: PALET.biru, width: 2.2 },
                      hovertemplate: 'τ %{x:.0f} hari<br>biaya %{y:,.0f}<extra></extra>',
                    },
                    {
                      x: [c.tau_hari[0], c.tau_hari[c.tau_hari.length - 1]],
                      y: [c.biaya_rtf_tahunan, c.biaya_rtf_tahunan],
                      type: 'scatter',
                      mode: 'lines',
                      name: 'run to failure',
                      line: { color: PALET.kuning, width: 1.5, dash: 'dash' },
                      hoverinfo: 'skip',
                    },
                    {
                      x: [c.tau_opt_hari],
                      y: [c.biaya_opt_tahunan],
                      type: 'scatter',
                      mode: 'markers',
                      name: 'τ*',
                      marker: { color: PALET.merah, size: 11, line: { color: '#fff', width: 1.4 } },
                      hovertemplate: 'τ* %{x:.0f} hari<br>biaya %{y:,.0f}<extra></extra>',
                    },
                  ]}
                  layout={{
                    title:
                      `${c.tag}<br><span style="font-size:10px;color:#64748b">β ${num(c.beta, 2)}, ` +
                      `${c.wilayah}, τ* ${num(c.tau_opt_hari, 0)} hari, hemat ${num(c.penghematan_pct, 1)}%</span>`,
                    showlegend: false,
                    margin: { l: 66, r: 16, t: 52, b: 44 },
                    xaxis: { title: 'Interval τ (hari)' },
                    yaxis: { title: 'Laju biaya tahunan', exponentformat: 'SI' },
                  }}
                />
              ))}
            </div>
            <Callout tone="info">{curves.catatan}</Callout>
          </Card>

          <Card
            title="Ringkasan interval per peralatan"
            subtitle="Tanda bintang pada τ* menandakan minimum berada di batas rentang, sehingga optimum sesungguhnya berada di luar rentang yang ditinjau"
          >
            <DataTable
              columns={KOLOM_KURVA}
              rows={curves.kurva}
              maxHeight="26rem"
              searchable
              searchKeys={['tag', 'kelas', 'wilayah']}
              initialSort={{ key: 'penghematan_pct', dir: 'desc' }}
              highlightRow={(r) => r.penghematan_pct >= 10}
            />
            <Callout tone="note">
              Baris bersorot adalah peralatan yang penjadwalan penggantiannya benar benar memberi penghematan
              di atas ambang. Untuk peralatan lain kurva biaya hampir datar sehingga pemilihan interval tidak
              berpengaruh. Rentang interval di sini mengikuti modul G, yaitu 0,05η sampai 3η, agar nilai τ*
              sebanding dengan tabel di atas. Untuk pencarian titik optimal pada rentang yang lebih lebar
              beserta kurva keandalannya, buka halaman Biaya dan keandalan.
            </Callout>
          </Card>
        </>
      )}
    </div>
  )
}
