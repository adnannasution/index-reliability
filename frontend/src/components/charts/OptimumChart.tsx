/**
 * Grafik pencari titik optimal dengan sumbu tegak ganda.
 *
 *   sumbu mendatar : interval penggantian tau, dalam hari
 *   sumbu tegak kiri  : laju biaya pemeliharaan tahunan C(tau)
 *   sumbu tegak kanan : keandalan R(tau) dan ketersediaan A_op(tau), skala 0..1
 *
 * Penanda:
 *   titik biaya minimum       interval paling ekonomis tau*
 *   garis target keandalan    interval terpanjang yang masih memenuhi R_target
 *   garis run to failure      laju biaya bila tidak ada jadwal sama sekali
 *
 * Landasan: Barlow & Hunter (1960) untuk C(tau); Rausand & Hoyland untuk R(t);
 * teorema pembaharuan (Barlow & Proschan) untuk laju kegagalan efektif yang
 * menjadi dasar A_op(tau); Ebeling untuk interval berbasis target keandalan.
 */
import { PALET, num, rupiah } from '../../lib/format'
import { Plot } from './Plot'

export function OptimumChart({ data, height = 460 }: { data: any; height?: number }) {
  const k = data.kurva
  const ob = data.optimal_biaya
  const ok = data.optimal_keandalan
  const dasar = data.garis_dasar
  const rTarget = data.rekomendasi?.target_keandalan ?? 0.9

  const xMin = k.tau_hari[0]
  const xMax = k.tau_hari[k.tau_hari.length - 1]

  const bentuk: any[] = [
    // laju biaya run to failure sebagai pembanding
    {
      type: 'line',
      xref: 'x',
      x0: xMin,
      x1: xMax,
      yref: 'y',
      y0: dasar.biaya_tahunan,
      y1: dasar.biaya_tahunan,
      line: { color: PALET.abu, width: 1.3, dash: 'dash' },
    },
    // ambang target keandalan pada sumbu kanan
    {
      type: 'line',
      xref: 'x',
      x0: xMin,
      x1: xMax,
      yref: 'y2',
      y0: rTarget,
      y1: rTarget,
      line: { color: PALET.hijau, width: 1.1, dash: 'dot' },
    },
    // interval biaya minimum
    {
      type: 'line',
      x0: ob.tau_hari,
      x1: ob.tau_hari,
      yref: 'paper',
      y0: 0,
      y1: 1,
      line: { color: PALET.merah, width: 1.4 },
    },
  ]
  if (ok) {
    bentuk.push({
      type: 'line',
      x0: ok.tau_hari,
      x1: ok.tau_hari,
      yref: 'paper',
      y0: 0,
      y1: 1,
      line: { color: PALET.hijau, width: 1.4, dash: 'dashdot' },
    })
  }

  const anotasi: any[] = [
    {
      x: ob.tau_hari,
      y: 1,
      yref: 'paper',
      text: `biaya minimum ${num(ob.tau_hari, 0)} hari`,
      showarrow: false,
      yanchor: 'bottom',
      font: { size: 10, color: PALET.merah },
      bgcolor: 'rgba(255,255,255,.85)',
    },
    {
      x: xMax,
      y: dasar.biaya_tahunan,
      yref: 'y',
      text: 'run to failure',
      showarrow: false,
      xanchor: 'right',
      yanchor: 'bottom',
      font: { size: 9.5, color: PALET.abu },
    },
    {
      x: xMin,
      y: rTarget,
      yref: 'y2',
      text: `target R ${num(rTarget, 2)}`,
      showarrow: false,
      xanchor: 'left',
      yanchor: 'bottom',
      font: { size: 9.5, color: PALET.hijau },
    },
  ]
  if (ok) {
    anotasi.push({
      x: ok.tau_hari,
      y: 0.06,
      yref: 'paper',
      text: `target keandalan ${num(ok.tau_hari, 0)} hari`,
      showarrow: false,
      xanchor: 'left',
      font: { size: 10, color: PALET.hijau },
      bgcolor: 'rgba(255,255,255,.85)',
    })
  }

  return (
    <Plot
      height={height}
      exportName={`titik_optimal_${data.label}`}
      ariaLabel={`Kurva laju biaya dan keandalan terhadap interval untuk ${data.label}`}
      data={[
        {
          x: k.tau_hari,
          y: k.biaya_tahunan,
          type: 'scatter',
          mode: 'lines',
          name: 'Laju biaya tahunan',
          line: { color: PALET.biru, width: 2.6 },
          hovertemplate: 'interval %{x:.1f} hari<br>biaya %{y:,.0f}<extra></extra>',
        },
        {
          x: [ob.tau_hari],
          y: [ob.biaya_tahunan],
          type: 'scatter',
          mode: 'markers',
          name: 'Titik biaya minimum',
          marker: { color: PALET.merah, size: 13, line: { color: '#fff', width: 1.6 } },
          hovertemplate: `biaya minimum<br>interval %{x:.1f} hari<br>biaya %{y:,.0f}<extra></extra>`,
        },
        {
          x: k.tau_hari,
          y: k.keandalan,
          type: 'scatter',
          mode: 'lines',
          name: 'Keandalan R(τ)',
          yaxis: 'y2',
          line: { color: PALET.hijau, width: 2.2 },
          hovertemplate: 'interval %{x:.1f} hari<br>R = %{y:.4f}<extra></extra>',
        },
        {
          x: k.tau_hari,
          y: k.a_op,
          type: 'scatter',
          mode: 'lines',
          name: 'Ketersediaan A_op(τ)',
          yaxis: 'y2',
          line: { color: PALET.kuning, width: 1.9, dash: 'dot' },
          hovertemplate: 'interval %{x:.1f} hari<br>A_op = %{y:.4f}<extra></extra>',
        },
      ]}
      layout={{
        title: `Titik optimal ${data.label}: biaya dan keandalan terhadap interval`,
        margin: { l: 78, r: 62, t: 42, b: 76 },
        hovermode: 'x unified',
        xaxis: {
          title: 'Interval penggantian τ (hari)',
          type: 'log',
          exponentformat: 'none',
        },
        yaxis: {
          title: 'Laju biaya pemeliharaan tahunan',
          type: 'log',
          exponentformat: 'SI',
          rangemode: 'tozero',
        },
        yaxis2: {
          title: 'Keandalan dan ketersediaan',
          overlaying: 'y',
          side: 'right',
          range: [0, 1.02],
          gridcolor: 'rgba(0,0,0,0)',
          tickformat: '.2f',
        },
        shapes: bentuk,
        annotations: anotasi,
        legend: { orientation: 'h', y: -0.22, x: 0 },
      }}
    />
  )
}

/** Kartu ringkas tiga titik penting pada kurva. */
export function OptimumSummary({ data }: { data: any }) {
  const ob = data.optimal_biaya
  const ok = data.optimal_keandalan
  const dasar = data.garis_dasar
  const dipilih = data.rekomendasi?.interval_dianjurkan_hari

  const kartu = [
    {
      judul: 'Titik biaya minimum',
      tau: `${num(ob.tau_hari, 1)} hari`,
      baris: [
        ['Biaya tahunan', rupiah(ob.biaya_tahunan)],
        ['Keandalan pada τ', num(ob.r_pada_tau, 4)],
        ['Ketersediaan', num(ob.a_op, 4)],
        ['Kegagalan per tahun', num(ob.gagal_per_thn, 2)],
      ],
      nada: 'merah',
      catatan: ob.di_batas_grid ? 'Berada di batas rentang, minimum sesungguhnya di luar rentang.' : null,
    },
    ok
      ? {
          judul: 'Titik target keandalan',
          tau: `${num(ok.tau_hari, 1)} hari`,
          baris: [
            ['Biaya tahunan', rupiah(ok.biaya_tahunan)],
            ['Keandalan pada τ', num(ok.r_pada_tau, 4)],
            ['Ketersediaan', num(ok.a_op, 4)],
            ['Kegagalan per tahun', num(ok.gagal_per_thn, 2)],
          ],
          nada: 'hijau',
          catatan:
            data.lingkup === 'fs'
              ? 'Hanya informasi, tidak dipakai sebagai jadwal pada tingkat sistem.'
              : null,
        }
      : {
          judul: 'Titik target keandalan',
          tau: 'tidak tercapai',
          baris: [['Keandalan tertinggi', num(data.kurva.keandalan[0], 4)]],
          nada: 'abu',
          catatan: 'Target tidak dapat dicapai pada interval mana pun.',
        },
    {
      judul: 'Garis dasar run to failure',
      tau: 'tanpa jadwal',
      baris: [
        ['Biaya tahunan', rupiah(dasar.biaya_tahunan)],
        ['Ketersediaan', num(dasar.a_op, 4)],
        ['Kegagalan per tahun', num(dasar.gagal_per_thn, 2)],
        ['Penghematan τ*', `${num(dasar.penghematan_pct, 1)}%`],
      ],
      nada: 'abu',
      catatan: null,
    },
  ]

  const warna: Record<string, string> = {
    merah: 'border-merah-200 bg-merah-50/50',
    hijau: 'border-hijau-100 bg-hijau-50/60',
    abu: 'border-slate-200 bg-slate-50',
  }

  return (
    <div className="grid gap-3 lg:grid-cols-3">
      {kartu.map((c) => (
        <div key={c.judul} className={`rounded-md border px-3.5 py-3 ${warna[c.nada]}`}>
          <div className="flex items-baseline justify-between gap-2">
            <p className="text-xs font-semibold text-slate-700">{c.judul}</p>
            <p className="font-mono text-sm font-bold text-slate-900">{c.tau}</p>
          </div>
          <dl className="mt-2 space-y-0.5 text-2xs">
            {c.baris.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <dt className="text-slate-500">{k}</dt>
                <dd className="font-mono text-slate-800">{v}</dd>
              </div>
            ))}
          </dl>
          {c.catatan && <p className="mt-2 text-2xs leading-snug text-slate-500">{c.catatan}</p>}
          {dipilih != null &&
            Math.abs(
              (c.judul.includes('biaya') ? data.optimal_biaya.tau_hari : (ok?.tau_hari ?? -1)) - dipilih,
            ) < 1e-6 && (
              <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-biru-700 px-2 py-0.5 text-2xs font-semibold text-white">
                interval dianjurkan
              </p>
            )}
        </div>
      ))}
    </div>
  )
}
