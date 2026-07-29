/**
 * Klien HTTP ke backend FastAPI.
 *
 * Semua permintaan lewat prefix /api yang diproxy Vite ke backend, sehingga
 * tidak ada alamat backend yang di-hard-code di kode UI.
 *
 * Setiap galat diubah menjadi `ApiError` berpesan Bahasa Indonesia yang siap
 * ditampilkan sebagai toast (§9): tidak pernah menampilkan stack trace.
 */

export class ApiError extends Error {
  status: number
  kind: string
  hint?: string

  constructor(message: string, status: number, kind = 'error', hint?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.kind = kind
    this.hint = hint
  }
}

const BASE = '/api'

async function parseError(res: Response): Promise<ApiError> {
  let detail = `Permintaan gagal (HTTP ${res.status}).`
  let kind = 'http'
  let hint: string | undefined
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') detail = body.detail
    else if (Array.isArray(body?.detail)) detail = body.detail.map((d: any) => d?.msg ?? String(d)).join('; ')
    if (typeof body?.kind === 'string') kind = body.kind
    if (typeof body?.hint === 'string') hint = body.hint
  } catch {
    /* tanggapan bukan JSON: pakai pesan bawaan */
  }
  return new ApiError(detail, res.status, kind, hint)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new ApiError(
      'Tidak dapat menghubungi server analisis. Pastikan backend berjalan ' +
        '(uvicorn app.main:app) lalu muat ulang halaman.',
      0,
      'network',
      'Jalankan `docker compose up` atau backend pada terminal terpisah.',
    )
  }
  if (!res.ok) throw await parseError(res)
  return (await res.json()) as T
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/** Unduh berkas biner (ekspor Excel/CSV) dan picu simpan di peramban. */
async function download(path: string, body: unknown, fallbackName: string): Promise<void> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Tidak dapat menghubungi server saat mengunduh.', 0, 'network')
  }
  if (!res.ok) throw await parseError(res)

  const disp = res.headers.get('Content-Disposition') ?? ''
  const match = /filename="?([^"]+)"?/.exec(disp)
  const name = match?.[1] ?? fallbackName

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

// ---------------------------------------------------------------- tipe data
export type Kind = 'notification' | 'order'

/** Lingkup analisis biaya dan keandalan. */
export type Lingkup = 'cdu' | 'fs' | 'equipment'

export interface UploadResult {
  dataset_id: string
  kind: Kind
  filename: string
  sheet_name: string
  uploaded_at: string
  columns: string[]
  sheets: Record<string, string[]>
  preview: Record<string, unknown>[]
  summary: Record<string, any>
}

export interface ConfigOverrides {
  unit?: string
  window_end?: 'cutoff' | 'lastevent'
  beta_source?: 'equipment' | 'mle' | 'workbook'
  beta_kmin?: number
  cred_m0?: number
  cp?: number
  cf?: number
  mc_reps?: number
  mc_seed?: number
  svc_level?: number
  lead_months?: number
  iso_downtime?: number
  red_credit?: number
  beta_dfr?: number
  beta_wear?: number
  pm_min_saving?: number
  ga_pop_size?: number
  ga_generations?: number
  ga_crossover_prob?: number
  ga_mutation_eta?: number
  ga_seed?: number
  ga_tau_min_days?: number
  ga_tau_max_days?: number
  [k: string]: unknown
}

export interface Analysis {
  dataset_id: string
  config: Record<string, any>
  meta: Record<string, any>
  kpi: {
    judul: string
    nilai: string
    satuan: string
    keterangan: string
    tone: string
    ikon?: string
  }[]
  data_quality: { metrik: string; nilai: number }[]
  equipment: any[]
  functional_system: any[]
  crosstab: { classes: string[]; rows: string[]; values: number[][] }
  pareto: { equipment: any[]; per_fs: Record<string, any[]>; total_cm: number }
  weibull_class: any[]
  weibull_fs: any[]
  weibull_equipment: any[]
  mrr_example: any
  mrr_plots: any[]
  laplace: any[]
  rbd_stages: any[]
  rbd_system: any[]
  reliability_curve: { t_hari: number[]; fs1: number[]; fs2: number[]; fs3: number[]; cdu: number[] }
  reliability_horizons: any[]
  reliability_life: any[]
  availability: any[]
  beta_comparison: any[]
}

export const api = {
  health: () => request<any>('/health'),
  defaults: () => request<any>('/meta/defaults'),
  references: () => request<any>('/meta/references'),
  domain: () => request<any>('/meta/domain'),
  datasets: () => request<any[]>('/datasets'),

  upload: async (file: File): Promise<UploadResult> => {
    const fd = new FormData()
    fd.append('file', file)
    let res: Response
    try {
      res = await fetch(`${BASE}/upload`, { method: 'POST', body: fd })
    } catch {
      throw new ApiError('Tidak dapat menghubungi server saat mengunggah berkas.', 0, 'network')
    }
    if (!res.ok) throw await parseError(res)
    return (await res.json()) as UploadResult
  },

  analyze: (dataset_id: string, config?: ConfigOverrides) =>
    post<Analysis>('/analyze', { dataset_id, config }),

  rbdDiagram: (dataset_id: string, config?: ConfigOverrides) =>
    post<any>('/rbd/diagram', { dataset_id, tags: ['*'], config }),

  rbdEquipment: (dataset_id: string, tag: string, config?: ConfigOverrides) =>
    post<any>('/rbd/equipment', { dataset_id, tags: [tag], config }),

  rbdSelection: (dataset_id: string, tags: string[], horizon_days = 365, config?: ConfigOverrides) =>
    post<any>('/rbd/selection', { dataset_id, tags, horizon_days, config }),

  monteCarlo: (dataset_id: string, config?: ConfigOverrides) =>
    post<any>('/montecarlo', { dataset_id, config }),

  pmOptimize: (dataset_id: string, config?: ConfigOverrides) =>
    post<any>('/pm-optimize', { dataset_id, config }),

  criticality: (dataset_id: string, config?: ConfigOverrides) =>
    post<any>('/criticality', { dataset_id, config }),

  costs: (dataset_id: string, order_dataset_id?: string, config?: ConfigOverrides) =>
    post<any>('/costs', { dataset_id, order_dataset_id, config }),

  costOptimize: (
    dataset_id: string,
    order_dataset_id?: string,
    config?: ConfigOverrides,
    lingkup?: { scope: Lingkup; fs?: number; tags?: string[] },
  ) =>
    post<any>('/cost-optimize', {
      dataset_id,
      order_dataset_id,
      config,
      scope: lingkup?.scope ?? 'cdu',
      fs: lingkup?.fs,
      tags: lingkup?.tags,
    }),

  /** Kurva laju biaya terhadap interval untuk beberapa tag pilihan. */
  intervalCurves: (
    dataset_id: string,
    tags: string[],
    order_dataset_id?: string,
    config?: ConfigOverrides,
    range_multiplier = 3,
  ) =>
    post<any>('/interval/curves', {
      dataset_id,
      tags,
      order_dataset_id,
      config,
      range_multiplier,
    }),

  /** Titik optimal biaya dan keandalan terhadap waktu, per tag atau per FS. */
  intervalOptimum: (
    dataset_id: string,
    target: { scope: 'equipment' | 'fs'; tag?: string; fs?: number },
    order_dataset_id?: string,
    config?: ConfigOverrides,
    r_target = 0.9,
    range_multiplier = 3,
  ) =>
    post<any>('/interval/optimum', {
      dataset_id,
      scope: target.scope,
      tag: target.tag,
      fs: target.fs,
      order_dataset_id,
      config,
      r_target,
      range_multiplier,
    }),

  exportExcel: (dataset_id: string, config?: ConfigOverrides) =>
    download('/export/excel', { dataset_id, config }, 'Hasil_Keandalan_CDU.xlsx'),

  exportCsv: (table: string, dataset_id: string, config?: ConfigOverrides) =>
    download(`/export/csv/${table}`, { dataset_id, config }, `${table}.csv`),
}
