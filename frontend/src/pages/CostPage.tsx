/**
 * Analisis biaya dan keandalan.
 *
 * Tiga bagian:
 *   1. biaya Cp dan Cf per tag hasil agregasi berkas order SAP;
 *   2. pencarian titik optimal dengan sumbu tegak ganda (biaya dan keandalan
 *      terhadap interval), pada lingkup satu peralatan atau satu Functional
 *      System, beserta rekomendasi bernalar;
 *   3. Pareto front NSGA-II yang dapat dijalankan pada lingkup CDU, satu
 *      Functional System, atau sekumpulan peralatan pilihan.
 */
import clsx from 'clsx'
import { useEffect, useState } from 'react'
import { PALET, num, pct, rupiah } from '../lib/format'
import { useStore } from '../store/useStore'
import {
  Callout,
  Card,
  Chip,
  DataTable,
  EmptyState,
  Icon,
  Loading,
  SectionTitle,
  Tombol,
  type Column,
} from '../components/ui'
import { Plot } from '../components/charts/Plot'
import { OptimumChart, OptimumSummary } from '../components/charts/OptimumChart'
import { TagPicker } from '../components/panels/TagPicker'

const KOLOM_BIAYA: Column<any>[] = [
  { key: 'tag', header: 'Tag', width: '8rem' },
  { key: 'n_korektif', header: 'Order korektif', numeric: true },
  { key: 'n_preventif', header: 'Order preventif', numeric: true },
  { key: 'cp', header: 'Cp preventif', numeric: true, render: (r) => rupiah(r.cp) },
  { key: 'cf', header: 'Cf korektif', numeric: true, render: (r) => rupiah(r.cf) },
  {
    key: 'rasio',
    header: 'Cf dibagi Cp',
    numeric: true,
    render: (r) => (
      <span className={r.rasio_ekstrem ? 'font-semibold text-merah-700' : ''}>{num(r.rasio, 2)}</span>
    ),
  },
  { key: 'asal', header: 'Asal nilai', render: (r) => <Chip>{r.asal}</Chip> },
]

/** Pemilih lingkup analisis untuk NSGA-II. */
function PilihLingkup() {
  const lingkup = useStore((s) => s.lingkup)
  const setLingkup = useStore((s) => s.setLingkup)
  const fs = useStore((s) => s.lingkupFs)
  const setFs = useStore((s) => s.setLingkupFs)
  const tags = useStore((s) => s.lingkupTags)
  const setTags = useStore((s) => s.setLingkupTags)

  const pilihan: { id: 'cdu' | 'fs' | 'equipment'; label: string; ket: string }[] = [
    { id: 'cdu', label: 'Seluruh CDU', ket: 'ketiga Functional System tersusun seri' },
    { id: 'fs', label: 'Per Functional System', ket: 'satu sistem saja' },
    { id: 'equipment', label: 'Per peralatan', ket: 'sekumpulan tag pilihan' },
  ]

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Lingkup analisis">
        {pilihan.map((p) => (
          <button
            key={p.id}
            role="tab"
            aria-selected={lingkup === p.id}
            onClick={() => setLingkup(p.id)}
            title={p.ket}
            className={clsx(
              'rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors',
              lingkup === p.id
                ? 'border-biru-700 bg-biru-700 text-white'
                : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50',
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      {lingkup === 'fs' && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500">Functional System</span>
          {[1, 2, 3].map((n) => (
            <button
              key={n}
              onClick={() => setFs(n)}
              className={clsx(
                'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                fs === n
                  ? 'border-slate-800 bg-slate-800 text-white'
                  : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50',
              )}
            >
              FS-{n}
            </button>
          ))}
        </div>
      )}

      {lingkup === 'equipment' && (
        <TagPicker terpilih={tags} onChange={setTags} maks={20} label="Peralatan yang dioptimasi" />
      )}
    </div>
  )
}

/** Bagian pencarian titik optimal bersumbu tegak ganda. */
function BagianOptimum() {
  const sasaran = useStore((s) => s.sasaran)
  const setSasaran = useStore((s) => s.setSasaran)
  const rTarget = useStore((s) => s.rTarget)
  const setRTarget = useStore((s) => s.setRTarget)
  const optimum = useStore((s) => s.optimum)
  const memuat = useStore((s) => s.optimumLoading)
  const muat = useStore((s) => s.loadOptimum)
  const a = useStore((s) => s.analysis)!

  const kandidat = (a.equipment ?? []).filter((r: any) => r.n_cm > 0)

  useEffect(() => {
    if (!optimum && !memuat) void muat()
  }, [optimum, memuat, muat])

  return (
    <div className="space-y-5">
      <Card
        title="Titik optimal: biaya dan keandalan terhadap waktu"
        subtitle="Sumbu mendatar adalah interval penggantian. Sumbu tegak kiri laju biaya tahunan, sumbu tegak kanan keandalan dan ketersediaan."
        actions={
          <Tombol kecil varian="utama" ikon="sebaran" memuat={memuat} onClick={() => void muat(true)}>
            Hitung titik optimal
          </Tombol>
        }
      >
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
          <div className="space-y-3">
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => setSasaran({ scope: 'fs', fs: sasaran.fs ?? 1 })}
                className={clsx(
                  'rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors',
                  sasaran.scope === 'fs'
                    ? 'border-biru-700 bg-biru-700 text-white'
                    : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50',
                )}
              >
                Per Functional System
              </button>
              <button
                onClick={() => setSasaran({ scope: 'equipment', tag: sasaran.tag ?? kandidat[0]?.tag })}
                className={clsx(
                  'rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors',
                  sasaran.scope === 'equipment'
                    ? 'border-biru-700 bg-biru-700 text-white'
                    : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50',
                )}
              >
                Per peralatan
              </button>
            </div>

            {sasaran.scope === 'fs' ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-slate-500">Sistem</span>
                {[1, 2, 3].map((n) => (
                  <button
                    key={n}
                    onClick={() => setSasaran({ scope: 'fs', fs: n })}
                    className={clsx(
                      'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                      sasaran.fs === n
                        ? 'border-slate-800 bg-slate-800 text-white'
                        : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50',
                    )}
                  >
                    FS-{n}
                  </button>
                ))}
              </div>
            ) : (
              <label className="block max-w-sm">
                <span className="label">Peralatan</span>
                <select
                  className="kolom"
                  value={sasaran.tag ?? ''}
                  onChange={(e) => setSasaran({ scope: 'equipment', tag: e.target.value })}
                >
                  {kandidat.map((r: any) => (
                    <option key={r.tag} value={r.tag}>
                      {r.tag} ({r.fs}, {r.kelas}, {r.n_cm} kegagalan)
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>

          <label className="lg:w-56">
            <span className="label">Target keandalan minimum</span>
            <input
              type="range"
              min={0.5}
              max={0.99}
              step={0.01}
              value={rTarget}
              onChange={(e) => setRTarget(Number(e.target.value))}
              className="w-full accent-[#0B2F9F]"
            />
            <span className="mt-1 block font-mono text-sm font-semibold text-slate-800">
              R = {num(rTarget, 2)}
            </span>
            <span className="mt-0.5 block text-2xs leading-snug text-slate-500">
              Peluang minimum peralatan mencapai umur penggantian tanpa gagal yang masih diterima.
            </span>
          </label>
        </div>
      </Card>

      {memuat && !optimum && (
        <Card title="Menghitung titik optimal">
          <Loading label="Menyusun kurva biaya, keandalan, dan ketersediaan pada rentang interval" rows={5} />
        </Card>
      )}

      {optimum && (
        <>
          <Card
            title={`Grafik titik optimal ${optimum.label}`}
            subtitle={
              optimum.lingkup === 'fs'
                ? `Interval bersama untuk ${optimum.n_peralatan} peralatan, kebijakan block replacement`
                : `β ${num(optimum.parameter.beta, 3)}, η ${num(optimum.parameter.eta_jam, 0)} jam, MDT ${num(optimum.parameter.mdt_jam, 0)} jam`
            }
          >
            <div className="space-y-4">
              <OptimumSummary data={optimum} />
              <OptimumChart data={optimum} />
              <Callout tone="note">{optimum.catatan_sumbu}</Callout>
            </div>
          </Card>

          <Card
            title="Rekomendasi"
            subtitle="Urutan penalaran mengikuti SAE JA1011, yaitu uji kelayakan tugas lebih dahulu lalu optimasi"
          >
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3 rounded-md border border-biru-100 bg-biru-50/60 px-4 py-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-biru-700 text-white">
                  <Icon name="papan-periksa" size={18} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-base font-bold text-slate-900">{optimum.rekomendasi.ringkas}</p>
                  <p className="mt-0.5 text-xs text-slate-600">
                    Dasar keputusan: {optimum.rekomendasi.dasar_keputusan}. Pola kegagalan:{' '}
                    {optimum.rekomendasi.wilayah_laju_kegagalan}.
                  </p>
                </div>
              </div>

              <div>
                <p className="mb-2 text-sm font-semibold text-slate-800">Alasan</p>
                <ol className="space-y-2">
                  {optimum.rekomendasi.alasan.map((s: string, i: number) => (
                    <li key={i} className="flex gap-2.5 text-xs leading-relaxed text-slate-600">
                      <span className="mt-px flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-slate-200 text-2xs font-semibold text-slate-600">
                        {i + 1}
                      </span>
                      <span className="min-w-0 flex-1">{s}</span>
                    </li>
                  ))}
                </ol>
              </div>

              <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="mb-1 text-sm font-semibold text-slate-800">Tindakan</p>
                <p className="text-xs leading-relaxed text-slate-600">{optimum.rekomendasi.tindakan}</p>
              </div>

              {optimum.peralatan?.length > 1 && (
                <DataTable
                  columns={[
                    { key: 'tag', header: 'Tag', width: '8rem' },
                    { key: 'kelas', header: 'Kelas' },
                    { key: 'n_cm', header: 'Kegagalan', numeric: true },
                    { key: 'beta', header: 'β', numeric: true, render: (r) => num(r.beta, 3) },
                    { key: 'eta_jam', header: 'η (jam)', numeric: true, render: (r) => num(r.eta_jam, 0) },
                    { key: 'mdt_jam', header: 'MDT (jam)', numeric: true, render: (r) => num(r.mdt_jam, 0) },
                    { key: 'cp', header: 'Cp', numeric: true, render: (r) => rupiah(r.cp) },
                    { key: 'cf', header: 'Cf', numeric: true, render: (r) => rupiah(r.cf) },
                  ]}
                  rows={optimum.peralatan}
                  maxHeight="18rem"
                />
              )}

              <details className="rounded-md border border-slate-200 bg-white px-4 py-3">
                <summary className="cursor-pointer text-sm font-semibold text-slate-800">
                  Rujukan rumus yang dipakai
                </summary>
                <ul className="mt-2 space-y-1.5">
                  {optimum.referensi.map((r: string, i: number) => (
                    <li key={i} className="text-2xs leading-relaxed text-slate-600">
                      {r}
                    </li>
                  ))}
                </ul>
              </details>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}

export function CostPage() {
  const order = useStore((s) => s.order)
  const costs = useStore((s) => s.costs)
  const opt = useStore((s) => s.opt)
  const loading = useStore((s) => s.optLoading)
  const runOpt = useStore((s) => s.runCostOptimize)
  const loadCosts = useStore((s) => s.loadCosts)
  const setConfig = useStore((s) => s.setConfig)
  const cfg = useStore((s) => s.config)
  const defaults = useStore((s) => s.defaults)
  const lingkup = useStore((s) => s.lingkup)
  const [dipilih, setDipilih] = useState<number | null>(null)

  useEffect(() => {
    if (!costs) void loadCosts()
  }, [costs, loadCosts])

  const d = defaults?.config ?? {}
  const ga = {
    pop: cfg.ga_pop_size ?? d.ga_pop_size ?? 60,
    gen: cfg.ga_generations ?? d.ga_generations ?? 60,
    cx: cfg.ga_crossover_prob ?? d.ga_crossover_prob ?? 0.9,
    mut: cfg.ga_mutation_eta ?? d.ga_mutation_eta ?? 20,
    seed: cfg.ga_seed ?? d.ga_seed ?? 7,
    lo: cfg.ga_tau_min_days ?? d.ga_tau_min_days ?? 7,
    hi: cfg.ga_tau_max_days ?? d.ga_tau_max_days ?? 730,
  }

  const sol = opt && dipilih !== null ? opt.pareto.find((p: any) => p.id === dipilih) : null

  return (
    <div className="space-y-5">
      {!order && (
        <Callout tone="warning" title="Berkas order belum diunggah">
          Modul ini berjalan dengan rasio biaya bawaan, yaitu Cp {d.cp ?? 1} berbanding Cf {d.cf ?? 10}.
          Unggah berkas order SAP pada halaman Data dan unggah agar biaya yang dipakai adalah biaya
          sebenarnya. Tanpa berkas order, bentuk kurva tetap benar tetapi nilai rupiahnya relatif.
        </Callout>
      )}

      {costs?.tersedia && (
        <Card
          title="Biaya pemeliharaan dari berkas order"
          subtitle="Cp dan Cf per tag hasil agregasi. Penggolongan korektif dan preventif memakai tautan nomor notifikasi."
        >
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { l: 'Order unit', v: num(costs.n_order, 0) },
                {
                  l: 'Tertaut notifikasi',
                  v: `${num(costs.n_tertaut_notifikasi, 0)} dari ${num(costs.n_order, 0)}`,
                },
                { l: 'Cp rata rata', v: rupiah(costs.cp_global) },
                { l: 'Cf rata rata', v: rupiah(costs.cf_global) },
              ].map((m) => (
                <div key={m.l} className="rounded-md border border-biru-100 bg-biru-50/60 px-3 py-2">
                  <p className="text-2xs font-medium text-slate-500">{m.l}</p>
                  <p className="mt-0.5 font-mono text-sm font-bold text-biru-800">{m.v}</p>
                </div>
              ))}
            </div>
            <div className="space-y-1.5">
              {costs.catatan?.map((c: string, i: number) => (
                <Callout key={i} tone={c.includes('sangat tinggi') ? 'warning' : 'note'}>
                  {c}
                </Callout>
              ))}
            </div>
            <DataTable
              columns={KOLOM_BIAYA}
              rows={costs.per_tag}
              maxHeight="20rem"
              searchable
              searchKeys={['tag', 'asal']}
              initialSort={{ key: 'rasio', dir: 'desc' }}
              highlightRow={(r) => r.rasio_ekstrem}
            />
          </div>
        </Card>
      )}

      <SectionTitle hint="Barlow dan Hunter (1960), Ebeling, serta teorema pembaharuan">
        Pencarian titik optimal
      </SectionTitle>
      <BagianOptimum />

      <SectionTitle hint="Deb, Pratap, Agarwal, dan Meyarivan (2002) melalui pymoo">
        Optimasi multi objektif NSGA-II
      </SectionTitle>

      <Card
        title="Lingkup dan konfigurasi algoritma genetika"
        subtitle="Pareto front dapat dicari untuk seluruh CDU, satu Functional System, atau sekumpulan peralatan pilihan"
        actions={
          <Tombol kecil varian="utama" ikon="jalan" memuat={loading} onClick={() => void runOpt()}>
            Jalankan optimasi
          </Tombol>
        }
      >
        <div className="space-y-4">
          <PilihLingkup />
          <div className="grid gap-3 border-t border-slate-200 pt-4 sm:grid-cols-3 lg:grid-cols-7">
            {[
              { k: 'ga_pop_size', l: 'Ukuran populasi', v: ga.pop, min: 8, max: 500, step: 1 },
              { k: 'ga_generations', l: 'Generasi', v: ga.gen, min: 5, max: 1000, step: 1 },
              { k: 'ga_crossover_prob', l: 'Peluang crossover', v: ga.cx, min: 0, max: 1, step: 0.05 },
              { k: 'ga_mutation_eta', l: 'η mutasi', v: ga.mut, min: 1, max: 100, step: 1 },
              { k: 'ga_seed', l: 'Seed', v: ga.seed, min: 0, max: 99999, step: 1 },
              { k: 'ga_tau_min_days', l: 'τ minimum (hari)', v: ga.lo, min: 1, max: 365, step: 1 },
              { k: 'ga_tau_max_days', l: 'τ maksimum (hari)', v: ga.hi, min: 30, max: 3650, step: 10 },
            ].map((f) => (
              <label key={f.k}>
                <span className="label">{f.l}</span>
                <input
                  type="number"
                  className="kolom"
                  value={f.v}
                  min={f.min}
                  max={f.max}
                  step={f.step}
                  onChange={(e) => setConfig({ [f.k]: Number(e.target.value) })}
                />
              </label>
            ))}
          </div>
        </div>
      </Card>

      {loading && !opt && (
        <Card title="Menjalankan NSGA-II">
          <Loading
            label={`Mengevaluasi ${ga.pop} solusi selama ${ga.gen} generasi, setiap solusi menghitung ulang RBD`}
            rows={5}
          />
        </Card>
      )}

      {!opt && !loading && (
        <EmptyState
          ikon="sebaran"
          title="Pareto front belum dihitung"
          message="Pilih lingkup analisis lalu tekan Jalankan optimasi untuk mencari kebijakan interval yang menyeimbangkan biaya pemeliharaan tahunan terhadap ketersediaan sistem."
        />
      )}

      {opt && (
        <>
          <Card
            title={`Pareto front biaya terhadap ketersediaan, lingkup ${opt.lingkup?.label ?? 'CDU'}`}
            subtitle={`${opt.pareto.length} solusi non dominated atas ${opt.variabel.length} variabel interval. Klik titik untuk melihat kebijakannya.`}
          >
            <Plot
              height={440}
              exportName={`pareto_front_${lingkup}`}
              ariaLabel="Pareto front biaya pemeliharaan tahunan terhadap ketersediaan sistem"
              onClickPoint={(e: any) => {
                const p = e?.points?.[0]
                if (p && p.curveNumber === 0) setDipilih(opt.pareto[p.pointNumber].id)
              }}
              data={[
                {
                  x: opt.pareto.map((p: any) => p.biaya_tahunan),
                  y: opt.pareto.map((p: any) => p.a_op_sistem),
                  type: 'scatter',
                  mode: 'lines+markers',
                  name: 'Pareto front',
                  line: { color: PALET.biru, width: 1.4 },
                  marker: {
                    color: opt.pareto.map((p: any) => (p.id === dipilih ? PALET.merah : PALET.biru)),
                    size: opt.pareto.map((p: any) => (p.id === dipilih ? 14 : 8)),
                    line: { color: '#fff', width: 1 },
                  },
                  hovertemplate: 'biaya %{x:,.0f}<br>A_op %{y:.5f}<br>klik untuk rinci<extra></extra>',
                },
                {
                  x: [opt.garis_dasar.biaya_tahunan],
                  y: [opt.garis_dasar.a_op_sistem],
                  type: 'scatter',
                  mode: 'markers',
                  name: 'Kebijakan saat ini, run to failure',
                  marker: {
                    color: PALET.kuning,
                    size: 15,
                    symbol: 'diamond',
                    line: { color: '#fff', width: 1.5 },
                  },
                  hovertemplate: 'kebijakan saat ini<br>biaya %{x:,.0f}<br>A_op %{y:.5f}<extra></extra>',
                },
              ]}
              layout={{
                title: `Biaya pemeliharaan tahunan terhadap ketersediaan, ${opt.lingkup?.label ?? 'CDU'}`,
                margin: { l: 78, r: 24, t: 34, b: 66 },
                xaxis: { title: 'Total biaya pemeliharaan tahunan', exponentformat: 'SI' },
                yaxis: { title: 'Ketersediaan operasional', tickformat: '.4f' },
              }}
            />
            <div className="mt-2 space-y-2">
              <Callout tone="info">{opt.catatan}</Callout>
              {opt.lingkup?.objektif_ketersediaan && (
                <Callout tone="note">
                  Objektif ketersediaan pada lingkup ini: {opt.lingkup.objektif_ketersediaan}.
                </Callout>
              )}
            </div>
          </Card>

          <div className="grid gap-5 xl:grid-cols-2">
            <Card
              title="Kurva trade off biaya terhadap ketersediaan"
              subtitle={`Peralatan penyumbang waktu henti terbesar pada lingkup ini: ${opt.tradeoff.tag}, β ${num(opt.tradeoff.beta, 3)}`}
            >
              <Plot
                height={380}
                exportName={`tradeoff_${opt.tradeoff.tag}`}
                ariaLabel="Kurva trade off biaya pemeliharaan terhadap ketersediaan"
                data={[
                  {
                    x: opt.tradeoff.biaya_tahunan,
                    y: opt.tradeoff.a_op,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Kurva kebijakan',
                    line: { color: PALET.hijau, width: 2.4 },
                    customdata: opt.tradeoff.tau_hari,
                    hovertemplate:
                      'τ %{customdata:.0f} hari<br>biaya %{x:,.0f}<br>A_op %{y:.4f}<extra></extra>',
                  },
                  {
                    x: [opt.tradeoff.biaya_opt],
                    y: [opt.tradeoff.a_op_opt],
                    type: 'scatter',
                    mode: 'markers+text',
                    name: 'Biaya minimum',
                    marker: { color: PALET.merah, size: 13 },
                    text: [`τ* ${num(opt.tradeoff.tau_opt_hari, 0)} hari`],
                    textposition: 'top center',
                    textfont: { size: 10 },
                    hovertemplate: 'titik biaya minimum<extra></extra>',
                  },
                ]}
                layout={{
                  title: 'Biaya tahunan terhadap ketersediaan menurut interval',
                  showlegend: false,
                  margin: { l: 66, r: 20, t: 34, b: 56 },
                  xaxis: { title: 'Biaya pemeliharaan tahunan', exponentformat: 'SI' },
                  yaxis: { title: 'Ketersediaan peralatan', tickformat: '.4f' },
                }}
              />
            </Card>

            <Card
              title="Kebijakan interval pada solusi terpilih"
              subtitle={
                sol
                  ? `Solusi nomor ${sol.id}, biaya ${rupiah(sol.biaya_tahunan)} per tahun, ketersediaan ${num(sol.a_op_sistem, 5)}`
                  : 'Klik salah satu titik pada Pareto front'
              }
            >
              {!sol && (
                <p className="py-10 text-center text-xs leading-relaxed text-slate-500">
                  Belum ada solusi dipilih. Klik titik pada grafik Pareto front untuk menampilkan interval per
                  peralatan beserta estimasi penghematannya.
                </p>
              )}
              {sol && (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      {
                        l: 'Selisih biaya',
                        v: pct(sol.delta_biaya_pct),
                        nada: sol.delta_biaya_pct < 0 ? 'text-hijau-700' : 'text-merah-700',
                      },
                      {
                        l: 'Selisih ketersediaan',
                        v: (sol.delta_availability >= 0 ? '+' : '') + num(sol.delta_availability, 5),
                        nada: sol.delta_availability >= 0 ? 'text-hijau-700' : 'text-merah-700',
                      },
                      {
                        l: 'Waktu henti',
                        v: `${num(sol.downtime_hari_thn, 1)} hari/thn`,
                        nada: 'text-slate-900',
                      },
                    ].map((m) => (
                      <div key={m.l} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                        <p className="text-2xs font-medium text-slate-500">{m.l}</p>
                        <p className={`mt-0.5 font-mono text-sm font-bold ${m.nada}`}>{m.v}</p>
                      </div>
                    ))}
                  </div>
                  <DataTable
                    columns={[
                      { key: 'tag', header: 'Tag', width: '8rem' },
                      {
                        key: 'tau_hari',
                        header: 'τ optimal (hari)',
                        numeric: true,
                        render: (r) => num(r.tau_hari, 1),
                      },
                      { key: 'beta', header: 'β', numeric: true, render: (r) => num(r.beta, 3) },
                      {
                        key: 'mdt_jam',
                        header: 'MDT (jam)',
                        numeric: true,
                        render: (r) => num(r.mdt_jam, 0),
                      },
                      {
                        key: 'cf',
                        header: 'Cf dibagi Cp',
                        numeric: true,
                        render: (r) => num(r.cf / r.cp, 2),
                      },
                      { key: 'sumber_biaya', header: 'Sumber biaya' },
                    ]}
                    rows={sol.interval}
                    maxHeight="22rem"
                    initialSort={{ key: 'tau_hari', dir: 'asc' }}
                  />
                </div>
              )}
            </Card>
          </div>

          <Card title="Garis dasar dan konfigurasi yang dipakai">
            <div className="grid gap-5 md:grid-cols-2">
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <dt className="col-span-2 mb-1 text-sm font-semibold text-slate-800">Garis dasar</dt>
                <dt className="text-slate-500">Kebijakan</dt>
                <dd className="text-right">{opt.garis_dasar.kebijakan}</dd>
                <dt className="text-slate-500">Biaya tahunan</dt>
                <dd className="text-right font-mono">{rupiah(opt.garis_dasar.biaya_tahunan)}</dd>
                <dt className="text-slate-500">Ketersediaan</dt>
                <dd className="text-right font-mono">{num(opt.garis_dasar.a_op_sistem, 5)}</dd>
                <dt className="text-slate-500">Waktu henti</dt>
                <dd className="text-right font-mono">{num(opt.garis_dasar.downtime_hari_thn, 1)} hari/thn</dd>
              </dl>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <dt className="col-span-2 mb-1 text-sm font-semibold text-slate-800">
                  Konfigurasi algoritma
                </dt>
                {Object.entries(opt.konfigurasi_ga).map(([k, v]) => (
                  <div key={k} className="col-span-2 grid grid-cols-2">
                    <dt className="text-slate-500">{k.replace(/_/g, ' ')}</dt>
                    <dd className="text-right font-mono">{String(v)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
