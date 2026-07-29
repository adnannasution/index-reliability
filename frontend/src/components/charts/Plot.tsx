/**
 * Pembungkus Plotly dengan tema seragam untuk seluruh grafik.
 *
 * Plotly dipilih karena interaktif (zoom, hover, ekspor PNG) dan mendukung
 * sumbu logaritmik yang diperlukan plot probabilitas Weibull serta jack knife.
 * Tema disamakan dengan tipografi dan palet aplikasi.
 */
import { useMemo } from 'react'
import createPlotlyComponent from 'react-plotly.js/factory'
// @ts-expect-error bundel minified tidak menyertakan tipe
import Plotly from 'plotly.js-dist-min'

const KomponenPlotly = createPlotlyComponent(Plotly)

export const SUMBU = {
  gridcolor: 'rgba(15,23,42,.07)',
  zerolinecolor: 'rgba(15,23,42,.16)',
  linecolor: 'rgba(15,23,42,.18)',
  tickfont: { size: 10.5, color: '#64748b' },
  titlefont: { size: 11.5, color: '#475569' },
  automargin: true,
}

export interface PlotProps {
  data: any[]
  layout?: Record<string, any>
  height?: number
  /** Nama berkas saat grafik diekspor ke PNG. */
  exportName?: string
  className?: string
  /** Keterangan aksesibilitas yang menjelaskan isi grafik. */
  ariaLabel?: string
  onClickPoint?: (e: any) => void
}

export function Plot({
  data,
  layout,
  height = 380,
  exportName = 'grafik',
  className,
  ariaLabel,
  onClickPoint,
}: PlotProps) {
  // Tipe layout Plotly memakai union literal yang ketat, misalnya orientation
  // 'h' atau 'v', sedangkan objek ini dibangun dengan spread sehingga
  // TypeScript melebarkannya menjadi string. Nilainya sudah sah bagi Plotly,
  // jadi hasil gabungan dilewatkan sebagai any hanya pada batas komponen.
  const gabungan = useMemo<any>(
    () => ({
      autosize: true,
      height,
      margin: { l: 62, r: 22, t: 34, b: 52 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: '"Plus Jakarta Sans", system-ui, sans-serif', size: 11.5, color: '#475569' },
      title: layout?.title
        ? typeof layout.title === 'string'
          ? {
              text: layout.title,
              font: { size: 12.5, color: '#0f172a', weight: 600 },
              x: 0,
              xanchor: 'left',
              y: 0.98,
            }
          : layout.title
        : undefined,
      hoverlabel: {
        bgcolor: '#ffffff',
        bordercolor: 'rgba(15,23,42,.14)',
        font: { size: 11.5, color: '#0f172a', family: '"Plus Jakarta Sans", system-ui, sans-serif' },
      },
      legend: {
        orientation: 'h',
        y: -0.19,
        x: 0,
        font: { size: 10.5 },
        bgcolor: 'rgba(0,0,0,0)',
        itemsizing: 'constant',
      },
      ...layout,
      xaxis: { ...SUMBU, ...(layout?.xaxis ?? {}) },
      yaxis: { ...SUMBU, ...(layout?.yaxis ?? {}) },
    }),
    [layout, height],
  )

  return (
    <div className={className} role="img" aria-label={ariaLabel}>
      <KomponenPlotly
        data={data}
        layout={gabungan}
        useResizeHandler
        style={{ width: '100%', height: `${height}px` }}
        onClick={onClickPoint}
        config={{
          displaylogo: false,
          responsive: true,
          locale: 'id',
          toImageButtonOptions: { format: 'png', filename: exportName, scale: 2.5 },
          modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
        }}
      />
    </div>
  )
}
