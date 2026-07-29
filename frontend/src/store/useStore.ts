/**
 * State global aplikasi (zustand).
 *
 * Menyimpan: berkas ter-upload, parameter analisis, hasil analisis, hasil
 * modul berat, seleksi blok RBD, dan antrean toast.
 */
import { create } from 'zustand'
import {
  ApiError,
  api,
  type Analysis,
  type ConfigOverrides,
  type Lingkup,
  type UploadResult,
} from '../api/client'

/** Sasaran analisis titik optimal: satu peralatan atau satu Functional System. */
export type SasaranOptimal = { scope: 'equipment' | 'fs'; tag?: string; fs?: number }

export type Toast = {
  id: number
  tone: 'error' | 'success' | 'info' | 'warning'
  title: string
  message?: string
}

let toastSeq = 1

interface State {
  // ---- berkas ----
  notif?: UploadResult
  order?: UploadResult
  uploading: boolean

  // ---- parameter ----
  config: ConfigOverrides
  defaults?: any

  // ---- hasil ----
  analysis?: Analysis
  analyzing: boolean

  diagram?: any
  diagramLoading: boolean

  mc?: any
  mcLoading: boolean

  pm?: any
  pmLoading: boolean

  crit?: any
  critLoading: boolean

  costs?: any
  opt?: any
  optLoading: boolean

  // ---- interval pemeliharaan: pilihan tag dan kurvanya ----
  pmTags: string[]
  pmCurves?: any
  pmCurvesLoading: boolean

  // ---- titik optimal biaya dan keandalan ----
  lingkup: Lingkup
  lingkupFs: number
  lingkupTags: string[]
  sasaran: SasaranOptimal
  rTarget: number
  optimum?: any
  optimumLoading: boolean

  references?: any

  // ---- seleksi RBD ----
  selected: string[]
  selection?: any
  selectionLoading: boolean
  focusTag?: string
  focus?: any
  focusLoading: boolean

  // ---- UI ----
  toasts: Toast[]

  // ---- aksi ----
  pushToast: (t: Omit<Toast, 'id'>) => void
  dismissToast: (id: number) => void
  handleError: (e: unknown, fallbackTitle?: string) => void

  loadDefaults: () => Promise<void>
  loadReferences: () => Promise<void>
  uploadFile: (file: File) => Promise<void>
  clearDataset: (kind: 'notification' | 'order') => void

  setConfig: (patch: ConfigOverrides) => void
  resetConfig: () => void

  runAnalysis: (force?: boolean) => Promise<void>
  loadDiagram: () => Promise<void>
  runMonteCarlo: () => Promise<void>
  runPmOptimize: () => Promise<void>
  runCriticality: () => Promise<void>
  loadCosts: () => Promise<void>
  runCostOptimize: () => Promise<void>

  setPmTags: (tags: string[]) => void
  loadPmCurves: (force?: boolean) => Promise<void>

  setLingkup: (l: Lingkup) => void
  setLingkupFs: (fs: number) => void
  setLingkupTags: (tags: string[]) => void
  setSasaran: (s: SasaranOptimal) => void
  setRTarget: (r: number) => void
  loadOptimum: (force?: boolean) => Promise<void>

  toggleSelect: (tag: string, additive: boolean) => void
  clearSelection: () => void
  selectMany: (tags: string[]) => void
  refreshSelection: () => Promise<void>
  setFocus: (tag?: string) => Promise<void>
}

/** Buang seluruh hasil turunan, dipakai saat berkas berubah. */
const derivedReset = {
  analysis: undefined,
  diagram: undefined,
  mc: undefined,
  pm: undefined,
  crit: undefined,
  costs: undefined,
  opt: undefined,
  selection: undefined,
  focus: undefined,
  pmCurves: undefined,
  optimum: undefined,
} as const

/**
 * Menentukan hasil mana yang menjadi tidak sah ketika sebuah parameter diubah.
 *
 * Tanpa pemetaan ini, mengubah satu parameter algoritma genetika akan membuang
 * SELURUH hasil termasuk analisis keandalan, sehingga pengguna terdorong kembali
 * ke halaman Data dan harus menunggu perhitungan penuh tanpa alasan. Ukuran
 * populasi tidak mempengaruhi Weibull maupun RBD, jadi cukup Pareto front yang
 * dihitung ulang.
 */
function invalidasiUntuk(kunci: string[]): Partial<Record<keyof State, undefined>> {
  const semua = { ...derivedReset }
  // Parameter pembacaan dan estimasi: mengubah dasar seluruh perhitungan.
  const dasar = [
    'unit',
    'fail_types',
    'pm_type',
    'window_end',
    'beta_source',
    'beta_kmin',
    'cred_m0',
    'boot_b',
  ]
  if (kunci.some((k) => dasar.includes(k))) return semua

  const out: Record<string, undefined> = {}
  const tandai = (...nama: string[]) => nama.forEach((n) => (out[n] = undefined))

  for (const k of kunci) {
    if (k.startsWith('ga_')) tandai('opt')
    else if (k.startsWith('mc_')) tandai('mc')
    else if (k === 'cp' || k === 'cf') tandai('pm', 'pmCurves', 'opt', 'optimum', 'crit')
    else tandai('crit', 'optimum', 'pm', 'pmCurves') // parameter modul J dan ambang strategi
  }
  return out as Partial<Record<keyof State, undefined>>
}

export const useStore = create<State>((set, get) => ({
  uploading: false,
  config: {},
  analyzing: false,
  diagramLoading: false,
  mcLoading: false,
  pmLoading: false,
  critLoading: false,
  optLoading: false,
  selected: [],
  selectionLoading: false,
  focusLoading: false,
  toasts: [],
  pmTags: [],
  pmCurvesLoading: false,
  lingkup: 'cdu',
  lingkupFs: 1,
  lingkupTags: [],
  sasaran: { scope: 'fs', fs: 1 },
  rTarget: 0.9,
  optimumLoading: false,

  pushToast: (t) => {
    const id = toastSeq++
    set((s) => ({ toasts: [...s.toasts, { ...t, id }] }))
    const ttl = t.tone === 'error' ? 9000 : 4500
    setTimeout(() => get().dismissToast(id), ttl)
  },

  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((x) => x.id !== id) })),

  handleError: (e, fallbackTitle = 'Terjadi kesalahan') => {
    const err = e as ApiError
    const message = err?.message ?? String(e)
    const hint = err?.hint ? ` ${err.hint}` : ''
    get().pushToast({ tone: 'error', title: fallbackTitle, message: message + hint })
  },

  loadDefaults: async () => {
    try {
      const d = await api.defaults()
      set({ defaults: d })
    } catch (e) {
      get().handleError(e, 'Gagal memuat parameter default')
    }
  },

  loadReferences: async () => {
    if (get().references) return
    try {
      set({ references: await api.references() })
    } catch (e) {
      get().handleError(e, 'Gagal memuat daftar referensi')
    }
  },

  uploadFile: async (file) => {
    set({ uploading: true })
    try {
      const r = await api.upload(file)
      if (r.kind === 'notification') {
        set({ notif: r, ...derivedReset, selected: [], focusTag: undefined })
        get().pushToast({
          tone: 'success',
          title: 'Berkas notifikasi dimuat',
          message:
            `${r.summary.rows_unit} notifikasi unit ${r.summary.unit_prefix} ` +
            `dari ${r.summary.rows_in_file} baris; jendela ${r.summary.t_start} s.d. ${r.summary.t_end} ` +
            `(${Math.round(r.summary.t_obs_hours).toLocaleString('id-ID')} jam).`,
        })
        await get().runAnalysis(true)
      } else {
        set({ order: r, costs: undefined, opt: undefined })
        get().pushToast({
          tone: 'success',
          title: 'Berkas order/biaya dimuat',
          message: `${r.summary.rows_unit} order unit ${r.summary.unit_prefix}. Modul optimasi biaya aktif.`,
        })
      }
    } catch (e) {
      get().handleError(e, 'Berkas tidak dapat dibaca')
    } finally {
      set({ uploading: false })
    }
  },

  clearDataset: (kind) => {
    if (kind === 'notification') set({ notif: undefined, ...derivedReset, selected: [] })
    else set({ order: undefined, costs: undefined, opt: undefined })
  },

  setConfig: (patch) => {
    // Hanya buang hasil yang benar benar terpengaruh oleh parameter yang diubah.
    const buang = invalidasiUntuk(Object.keys(patch))
    set((s) => ({ config: { ...s.config, ...patch }, ...buang }))
  },

  resetConfig: () => set({ config: {}, ...derivedReset }),

  runAnalysis: async (force = false) => {
    const { notif, config, analysis } = get()
    if (!notif) return
    if (analysis && !force) return
    set({ analyzing: true })
    try {
      const a = await api.analyze(notif.dataset_id, config)
      set({ analysis: a })
    } catch (e) {
      get().handleError(e, 'Analisis gagal')
    } finally {
      set({ analyzing: false })
    }
  },

  loadDiagram: async () => {
    const { notif, config, diagram, diagramLoading } = get()
    if (!notif || diagram || diagramLoading) return
    set({ diagramLoading: true })
    try {
      set({ diagram: await api.rbdDiagram(notif.dataset_id, config) })
    } catch (e) {
      get().handleError(e, 'Diagram RBD gagal dimuat')
    } finally {
      set({ diagramLoading: false })
    }
  },

  runMonteCarlo: async () => {
    const { notif, config } = get()
    if (!notif) return
    set({ mcLoading: true })
    try {
      set({ mc: await api.monteCarlo(notif.dataset_id, config) })
    } catch (e) {
      get().handleError(e, 'Simulasi Monte Carlo gagal')
    } finally {
      set({ mcLoading: false })
    }
  },

  runPmOptimize: async () => {
    const { notif, config } = get()
    if (!notif) return
    set({ pmLoading: true })
    try {
      set({ pm: await api.pmOptimize(notif.dataset_id, config) })
    } catch (e) {
      get().handleError(e, 'Optimasi interval PM gagal')
    } finally {
      set({ pmLoading: false })
    }
  },

  runCriticality: async () => {
    const { notif, config } = get()
    if (!notif) return
    set({ critLoading: true })
    try {
      set({ crit: await api.criticality(notif.dataset_id, config) })
    } catch (e) {
      get().handleError(e, 'Penilaian kekritisan gagal')
    } finally {
      set({ critLoading: false })
    }
  },

  loadCosts: async () => {
    const { notif, order, config } = get()
    if (!notif) return
    try {
      const c = await api.costs(notif.dataset_id, order?.dataset_id, config)
      set({ costs: c })
      const ext = (c.per_tag ?? []).filter((t: any) => t.rasio_ekstrem)
      if (ext.length) {
        get().pushToast({
          tone: 'warning',
          title: 'Rasio biaya ekstrem terdeteksi',
          message:
            `${ext.length} tag memiliki rasio Cf/Cp di atas 50 dengan sedikit order ` +
            `(${ext
              .slice(0, 4)
              .map((t: any) => t.tag)
              .join(', ')}). Interval optimalnya ` +
            'akan terdorong ke batas bawah: tinjau biaya aktualnya.',
        })
      }
    } catch (e) {
      get().handleError(e, 'Agregasi biaya gagal')
    }
  },

  runCostOptimize: async () => {
    const { notif, order, config, lingkup, lingkupFs, lingkupTags } = get()
    if (!notif) return
    if (lingkup === 'equipment' && lingkupTags.length === 0) {
      get().pushToast({
        tone: 'warning',
        title: 'Belum ada peralatan dipilih',
        message: 'Pilih minimal satu tag peralatan sebelum menjalankan optimasi pada lingkup ini.',
      })
      return
    }
    set({ optLoading: true })
    try {
      if (!get().costs) await get().loadCosts()
      const o = await api.costOptimize(notif.dataset_id, order?.dataset_id, config, {
        scope: lingkup,
        fs: lingkup === 'fs' ? lingkupFs : undefined,
        tags: lingkup === 'equipment' ? lingkupTags : undefined,
      })
      set({ opt: o })
    } catch (e) {
      get().handleError(e, 'Optimasi NSGA-II gagal')
    } finally {
      set({ optLoading: false })
    }
  },

  // ---- interval pemeliharaan: kurva untuk tag pilihan ----
  setPmTags: (tags) => set({ pmTags: tags, pmCurves: undefined }),

  loadPmCurves: async (force = false) => {
    const { notif, order, config, pmTags, pmCurves, pmCurvesLoading } = get()
    if (!notif || pmTags.length === 0) return
    if (pmCurves && !force) return
    if (pmCurvesLoading) return
    set({ pmCurvesLoading: true })
    try {
      const c = await api.intervalCurves(notif.dataset_id, pmTags, order?.dataset_id, config)
      set({ pmCurves: c })
      if (c.dilewati?.length) {
        get().pushToast({
          tone: 'info',
          title: `${c.dilewati.length} peralatan dilewati`,
          message: c.dilewati
            .slice(0, 3)
            .map((d: any) => `${d.tag}: ${d.alasan}`)
            .join('; '),
        })
      }
    } catch (e) {
      get().handleError(e, 'Kurva interval gagal dimuat')
    } finally {
      set({ pmCurvesLoading: false })
    }
  },

  // ---- titik optimal biaya dan keandalan ----
  setLingkup: (l) => set({ lingkup: l, opt: undefined }),
  setLingkupFs: (fs) => set({ lingkupFs: fs, opt: undefined }),
  setLingkupTags: (tags) => set({ lingkupTags: tags, opt: undefined }),
  setSasaran: (s) => set({ sasaran: s, optimum: undefined }),
  setRTarget: (r) => set({ rTarget: r, optimum: undefined }),

  loadOptimum: async (force = false) => {
    const { notif, order, config, sasaran, rTarget, optimum, optimumLoading } = get()
    if (!notif) return
    if (optimum && !force) return
    if (optimumLoading) return
    if (sasaran.scope === 'equipment' && !sasaran.tag) return
    set({ optimumLoading: true })
    try {
      const o = await api.intervalOptimum(notif.dataset_id, sasaran, order?.dataset_id, config, rTarget)
      set({ optimum: o })
    } catch (e) {
      get().handleError(e, 'Analisis titik optimal gagal')
    } finally {
      set({ optimumLoading: false })
    }
  },

  toggleSelect: (tag, additive) => {
    const cur = get().selected
    let next: string[]
    if (additive) next = cur.includes(tag) ? cur.filter((t) => t !== tag) : [...cur, tag]
    else next = cur.length === 1 && cur[0] === tag ? [] : [tag]
    set({ selected: next })
    void get().refreshSelection()
  },

  clearSelection: () => set({ selected: [], selection: undefined }),

  selectMany: (tags) => {
    set({ selected: tags })
    void get().refreshSelection()
  },

  refreshSelection: async () => {
    const { notif, selected, config } = get()
    if (!notif || selected.length === 0) {
      set({ selection: undefined })
      return
    }
    set({ selectionLoading: true })
    try {
      set({ selection: await api.rbdSelection(notif.dataset_id, selected, 365, config) })
    } catch (e) {
      get().handleError(e, 'Perhitungan seleksi gagal')
    } finally {
      set({ selectionLoading: false })
    }
  },

  setFocus: async (tag) => {
    const { notif, config } = get()
    set({ focusTag: tag })
    if (!notif || !tag) {
      set({ focus: undefined })
      return
    }
    set({ focusLoading: true })
    try {
      set({ focus: await api.rbdEquipment(notif.dataset_id, tag, config) })
    } catch (e) {
      get().handleError(e, 'Detail peralatan gagal dimuat')
    } finally {
      set({ focusLoading: false })
    }
  },
}))
