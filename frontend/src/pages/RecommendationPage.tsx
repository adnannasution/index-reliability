/** Modul J: kekritisan, strategi RCM, jack-knife, suku cadang (grafik 14, 15). */
import { useEffect, useState } from 'react'
import { PALET, NADA_RISIKO, warnaPita, num } from '../lib/format'
import { useStore } from '../store/useStore'
import { Callout, Card, Chip, DataTable, Icon, Loading, Tombol, type Column } from '../components/ui'
import { Plot } from '../components/charts/Plot'

const KRIT_COLS: Column<any>[] = [
  { key: 'tag', header: 'Tag', width: '8rem' },
  { key: 'fs', header: 'FS', width: '4.5rem' },
  { key: 'kelas', header: 'Kelas', width: '5.5rem' },
  { key: 'kritikalitas', header: 'Krit.', width: '4rem' },
  { key: 'n_cm', header: 'n_CM', numeric: true },
  { key: 'gagal_per_thn', header: 'Gagal/thn', numeric: true, render: (r) => num(r.gagal_per_thn, 1) },
  { key: 'mdt_jam', header: 'MDT (jam)', numeric: true, render: (r) => num(r.mdt_jam, 0) },
  {
    key: 'downtime_jam_thn',
    header: 'Downtime (jam/thn)',
    numeric: true,
    render: (r) => num(r.downtime_jam_thn, 0),
  },
  { key: 'redundan', header: 'Redundan', width: '5.5rem' },
  { key: 'indeks_frekuensi', header: 'Li', numeric: true, title: 'Indeks frekuensi 1-5 (PoF)' },
  { key: 'indeks_konsekuensi', header: 'Ci', numeric: true, title: 'Indeks konsekuensi 1-5 (CoF)' },
  {
    key: 'skor_risiko',
    header: 'Risiko',
    numeric: true,
    render: (r) => (
      <span className="inline-flex items-center gap-1.5">
        <span className="font-mono font-semibold">{r.skor_risiko}</span>
        <Chip className={NADA_RISIKO[r.pita_risiko]}>{r.pita_risiko}</Chip>
      </span>
    ),
  },
]

const STRAT_COLS: Column<any>[] = [
  { key: 'tag', header: 'Tag', width: '8rem' },
  { key: 'fs', header: 'FS', width: '4.5rem' },
  { key: 'beta', header: 'β', numeric: true, render: (r) => num(r.beta, 2) },
  {
    key: 'tren',
    header: 'Tren',
    render: (r) => (
      <Chip
        className={
          r.tren === 'memburuk'
            ? 'bg-merah-50 text-merah-700'
            : r.tren === 'membaik'
              ? 'bg-hijau-50 text-hijau-700'
              : 'bg-slate-100 text-slate-600'
        }
      >
        {r.tren}
      </Chip>
    ),
  },
  {
    key: 'risiko',
    header: 'Risiko',
    render: (r) => <Chip className={NADA_RISIKO[r.risiko]}>{r.risiko}</Chip>,
  },
  { key: 'strategi', header: 'Strategi', width: '17rem' },
  { key: 'interval', header: 'Interval', width: '11rem' },
  {
    key: 'downtime_dihindarkan_jam_thn',
    header: 'Dihindarkan (jam/thn)',
    numeric: true,
    render: (r) => num(r.downtime_dihindarkan_jam_thn, 0),
  },
]

export function RecommendationPage() {
  const j = useStore((s) => s.crit)
  const loading = useStore((s) => s.critLoading)
  const run = useStore((s) => s.runCriticality)
  const [openNarasi, setOpenNarasi] = useState<number | null>(0)

  useEffect(() => {
    if (!j && !loading) void run()
  }, [j, loading, run])

  if (loading && !j)
    return (
      <Card title="Menilai kekritisan dan menyusun strategi">
        <Loading
          label="Menghitung matriks risiko, memilih strategi RCM, dan menghitung kebutuhan suku cadang…"
          rows={6}
        />
      </Card>
    )
  if (!j) return null

  const rg = j.ringkasan
  const jk = j.jackknife

  return (
    <div className="space-y-5">
      <Card
        title="Ringkasan portofolio pemeliharaan"
        subtitle="Modul J: logika RCM (SAE JA1011), matriks risiko API 580/581, jack-knife Knights (2001)"
        actions={
          <Tombol kecil ikon="segarkan" memuat={loading} onClick={() => void run()}>
            Hitung ulang
          </Tombol>
        }
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[
            { l: 'Peralatan dinilai', v: num(rg.n_dinilai, 0), tone: 'text-biru-800' },
            { l: 'Risiko ekstrem', v: num(rg.n_ekstrem, 0), tone: 'text-merah-700' },
            { l: 'Risiko tinggi', v: num(rg.n_tinggi, 0), tone: 'text-kuning-600' },
            {
              l: 'Downtime terproyeksi',
              v: `${num(rg.total_downtime_jam_thn / 24, 0)} hari/thn`,
              tone: 'text-biru-800',
            },
            {
              l: 'Potensi dihindarkan',
              v: `${num(rg.total_dihindarkan_jam_thn / 24, 0)} hari (${num(rg.persen_dihindarkan, 0)}%)`,
              tone: 'text-hijau-700',
            },
          ].map((m) => (
            <div key={m.l} className="rounded-lg bg-slate-50 px-3 py-2.5">
              <p className="text-2xs font-medium text-slate-500">{m.l}</p>
              <p className={`mt-0.5 font-mono text-base font-semibold ${m.tone}`}>{m.v}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(rg.strategi_terpilih).map(([k, v]) => (
            <Chip key={k} className="bg-biru-50 text-biru-700">
              {k}: <strong>{String(v)}</strong> peralatan
            </Chip>
          ))}
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card
          title="Grafik 14. Diagram jack-knife (kronis vs akut)"
          subtitle={`Sumbu log-log; garis merah = iso-downtime ${num(jk.iso_downtime, 0)} jam/tahun. Ref: Knights (2001)`}
        >
          <Plot
            height={420}
            exportName="jackknife"
            ariaLabel="Diagram jack-knife frekuensi kegagalan terhadap lama henti per kejadian"
            data={[
              {
                x: jk.titik.map((p: any) => p.gagal_per_thn),
                y: jk.titik.map((p: any) => p.mdt_jam),
                type: 'scatter',
                mode: 'markers+text',
                text: jk.titik.map((p: any, i: number) => (i < 10 ? p.tag.replace(/^\d+-/, '') : '')),
                textposition: 'top right',
                textfont: { size: 9, color: PALET.gelap },
                marker: {
                  size: 10,
                  color: jk.titik.map((p: any) => warnaPita(p.pita_risiko)),
                  line: { color: PALET.gelap, width: 1 },
                },
                hovertemplate:
                  '%{customdata[0]}<br>%{x:.2f} kejadian/thn<br>%{y:.0f} jam/kejadian<br>%{customdata[1]} jam henti/thn<extra></extra>',
                customdata: jk.titik.map((p: any) => [p.tag, Math.round(p.downtime_jam_thn)]),
              },
              {
                x: [0.05, 20],
                y: [jk.iso_downtime / 0.05, jk.iso_downtime / 20],
                type: 'scatter',
                mode: 'lines',
                name: 'iso-downtime',
                line: { color: PALET.merah, width: 1.6 },
                hoverinfo: 'skip',
              },
            ]}
            layout={{
              title: 'Kronis vs akut',
              showlegend: false,
              margin: { l: 62, r: 22, t: 34, b: 56 },
              xaxis: { title: 'Seberapa sering gagal (kejadian per tahun)', type: 'log' },
              yaxis: { title: 'Lama henti tiap kejadian (jam)', type: 'log' },
              shapes: [
                {
                  type: 'line',
                  x0: jk.median_frekuensi,
                  x1: jk.median_frekuensi,
                  yref: 'paper',
                  y0: 0,
                  y1: 1,
                  line: { color: PALET.abu, width: 1.2, dash: 'dash' },
                },
                {
                  type: 'line',
                  xref: 'paper',
                  x0: 0,
                  x1: 1,
                  y0: jk.median_durasi,
                  y1: jk.median_durasi,
                  line: { color: PALET.abu, width: 1.2, dash: 'dash' },
                },
              ],
            }}
          />
          <Callout tone="note">
            <strong>Akut</strong> = jarang gagal tetapi tiap kejadian lama · <strong>Kronis</strong> = sering
            gagal dengan durasi pendek · <strong>Akut-kronis</strong> (kanan atas) = sering DAN lama,
            prioritas tertinggi. Titik di atas garis merah menyumbang lebih dari {num(jk.iso_downtime, 0)} jam
            henti per tahun.
          </Callout>
        </Card>

        <Card
          title="Matriks risiko 5×5"
          subtitle="Risk = indeks frekuensi (PoF) × indeks konsekuensi (CoF): API 580/581"
        >
          <Plot
            height={420}
            exportName="matriks_risiko"
            ariaLabel="Matriks risiko frekuensi terhadap konsekuensi"
            data={[
              {
                z: Array.from({ length: 5 }, (_, ci) =>
                  Array.from({ length: 5 }, (_, li) => (li + 1) * (ci + 1)),
                ),
                x: [1, 2, 3, 4, 5],
                y: [1, 2, 3, 4, 5],
                type: 'heatmap',
                colorscale: [
                  [0, '#eef0f2'],
                  [0.16, '#c9e5de'],
                  [0.36, '#f4d9bb'],
                  [0.6, '#e5b4b4'],
                  [1, '#cf9a9a'],
                ],
                showscale: false,
                hovertemplate: 'Li %{x} × Ci %{y} = %{z}<extra></extra>',
              },
              {
                x: j.matriks_risiko.map((p: any) => p.li + (Math.random() - 0.5) * 0.34),
                y: j.matriks_risiko.map((p: any) => p.ci + (Math.random() - 0.5) * 0.34),
                type: 'scatter',
                mode: 'markers',
                marker: { size: 9, color: '#fff', line: { color: PALET.gelap, width: 1.3 } },
                text: j.matriks_risiko.map((p: any) => p.tag),
                hovertemplate: '%{text}<extra></extra>',
              },
            ]}
            layout={{
              title: 'Peta risiko peralatan',
              showlegend: false,
              margin: { l: 62, r: 22, t: 34, b: 62 },
              xaxis: {
                title: 'Indeks frekuensi (1 = jarang, 5 = sangat sering)',
                dtick: 1,
                range: [0.5, 5.5],
              },
              yaxis: { title: 'Indeks konsekuensi (1 = ringan, 5 = berat)', dtick: 1, range: [0.5, 5.5] },
            }}
          />
          <p className="mt-1 text-xs text-slate-500">
            Titik digeser sedikit secara acak (jitter) agar peralatan dengan indeks sama tidak saling
            menutupi.
          </p>
        </Card>
      </div>

      <Card
        title="J1: Peringkat kekritisan"
        subtitle="Diurutkan menurut skor risiko, lalu potensi manfaat perbaikan"
      >
        <DataTable
          columns={KRIT_COLS}
          rows={j.kekritisan}
          maxHeight="30rem"
          searchable
          searchKeys={['tag', 'fs', 'kelas', 'pita_risiko']}
          highlightRow={(r) => r.pita_risiko === 'Ekstrem'}
        />
      </Card>

      <Card
        title="J2: Strategi pemeliharaan terpilih"
        subtitle="Urutan logika RCM: kegagalan dini → RCA · aus + hemat → TBM · degradasi terpantau → CBM · risiko rendah + redundan → RTF · selainnya inspeksi"
      >
        <DataTable
          columns={STRAT_COLS}
          rows={j.strategi}
          maxHeight="30rem"
          searchable
          searchKeys={['tag', 'fs', 'strategi', 'tren']}
        />
      </Card>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card
          title="Grafik 15. Kebutuhan suku cadang"
          subtitle="Kuantil Poisson pada tingkat layanan; ROP memakai lead time pengadaan"
        >
          {j.suku_cadang.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-500">
              Tidak ada peralatan yang melampaui ambang laju kegagalan untuk masuk daftar suku cadang.
            </p>
          ) : (
            <>
              <Plot
                height={360}
                exportName="kebutuhan_suku_cadang"
                ariaLabel="Kebutuhan stok minimum suku cadang per peralatan"
                data={[
                  {
                    y: j.suku_cadang.slice(0, 14).map((r: any) => r.tag),
                    x: j.suku_cadang.slice(0, 14).map((r: any) => r.stok_minimum),
                    type: 'bar',
                    orientation: 'h',
                    name: 'Stok minimum (12 bulan)',
                    marker: { color: PALET.biru },
                    hovertemplate: '%{y}<br>stok minimum %{x}<extra></extra>',
                  },
                  {
                    y: j.suku_cadang.slice(0, 14).map((r: any) => r.tag),
                    x: j.suku_cadang.slice(0, 14).map((r: any) => r.titik_pesan_ulang),
                    type: 'bar',
                    orientation: 'h',
                    name: 'Titik pesan ulang',
                    marker: { color: PALET.kuning },
                    hovertemplate: '%{y}<br>ROP %{x}<extra></extra>',
                  },
                ]}
                layout={{
                  title: 'Stok minimum & titik pesan ulang',
                  barmode: 'group',
                  margin: { l: 92, r: 20, t: 34, b: 56 },
                  xaxis: { title: 'Jumlah unit' },
                  yaxis: { title: '', autorange: 'reversed', tickfont: { size: 10 } },
                }}
              />
              <Callout tone="note">
                Dihitung dari ekspektasi jumlah kegagalan memakai kuantil Poisson pada tingkat layanan{' '}
                {j.suku_cadang[0]?.tingkat_layanan}. Angka ini berbasis <strong>data notifikasi nyata</strong>
                , bukan sensor sintetis.
              </Callout>
            </>
          )}
        </Card>

        <Card title="J3: Tabel kebutuhan suku cadang">
          <DataTable
            columns={[
              { key: 'tag', header: 'Tag', width: '8rem' },
              { key: 'fs', header: 'FS', width: '4.5rem' },
              { key: 'kelas', header: 'Kelas' },
              {
                key: 'ekspektasi_gagal_12bln',
                header: 'E[gagal 12 bln]',
                numeric: true,
                render: (r) => num(r.ekspektasi_gagal_12bln, 1),
              },
              { key: 'stok_minimum', header: 'Stok minimum', numeric: true },
              { key: 'titik_pesan_ulang', header: 'ROP', numeric: true },
            ]}
            rows={j.suku_cadang}
            maxHeight="24rem"
          />
        </Card>
      </div>

      <Card
        title="J4: Daftar tindakan berprioritas"
        subtitle="Rekomendasi naratif bergaya laporan reliability engineer, lengkap dengan KPI target"
      >
        <div className="space-y-2">
          {j.tindakan.map((t: any, i: number) => (
            <div key={t.prioritas} className="overflow-hidden rounded-lg border border-slate-200">
              <button
                onClick={() => setOpenNarasi(openNarasi === i ? null : i)}
                className="flex w-full items-center justify-between gap-3 bg-slate-50 px-4 py-2.5 text-left hover:bg-slate-100"
                aria-expanded={openNarasi === i}
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-biru-700 text-2xs font-bold text-white">
                    {t.prioritas}
                  </span>
                  <span className="truncate text-sm font-semibold text-biru-800">{t.tag}</span>
                  <Chip className={NADA_RISIKO[t.risiko]}>{t.risiko}</Chip>
                  <span className="hidden truncate text-xs text-slate-600 sm:inline">{t.strategi}</span>
                </span>
                <span className="shrink-0 text-slate-400">
                  <Icon name={openNarasi === i ? 'panah-bawah' : 'panah-kanan'} size={16} />
                </span>
              </button>
              {openNarasi === i && (
                <pre className="animate-masuk whitespace-pre-wrap px-4 py-3 font-sans text-xs leading-relaxed text-slate-700">
                  {t.narasi}
                </pre>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Callout tone="warning" title="Modul sensor sintetis (H & I pada MATLAB) tidak ditampilkan">
        Skrip MATLAB memuat modul deteksi anomali (autoencoder) dan prediksi sisa umur pakai (LSTM) yang
        berjalan di atas <strong>sensor sintetis</strong>: bukan pengukuran nyata. Modul tersebut sengaja
        TIDAK ditampilkan di sini agar tidak ada angka yang tampak seperti hasil pengukuran padahal bukan.
        Antarmuka backend sudah disiapkan sehingga data historian/DCS yang sebenarnya dapat dipasang kemudian;
        seluruh angka pada halaman ini dihitung dari notifikasi SAP nyata.
      </Callout>
    </div>
  )
}
