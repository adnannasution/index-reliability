import { useEffect, useState } from 'react'
import { useStore } from './store/useStore'
import { Header, NAV, Sidebar, SettingsDrawer, type PageId } from './components/panels/Shell'
import { EmptyState, Toasts } from './components/ui'
import { DataPage } from './pages/DataPage'
import { EquipmentPage } from './pages/EquipmentPage'
import { FsPage } from './pages/FsPage'
import { WeibullPage } from './pages/WeibullPage'
import { RbdPage } from './pages/RbdPage'
import { MonteCarloPage } from './pages/MonteCarloPage'
import { PmPage } from './pages/PmPage'
import { CostPage } from './pages/CostPage'
import { RecommendationPage } from './pages/RecommendationPage'
import { MethodologyPage } from './pages/MethodologyPage'

export default function App() {
  const [page, setPage] = useState<PageId>('data')
  const [settings, setSettings] = useState(false)
  // Sidebar dapat digeser buka/tutup di semua ukuran layar. Bawaan: terbuka di
  // layar besar, tertutup di layar kecil.
  const [menuTerbuka, setMenuTerbuka] = useState(
    () => typeof window !== 'undefined' && window.innerWidth >= 1024,
  )
  const analysis = useStore((s) => s.analysis)
  const loadDefaults = useStore((s) => s.loadDefaults)

  useEffect(() => {
    void loadDefaults()
  }, [loadDefaults])

  // Kembali ke halaman Data bila hasil analisis dibuang (mis. berkas dihapus).
  useEffect(() => {
    const nav = NAV.find((n) => n.id === page)
    if (nav?.needsData && !analysis) setPage('data')
  }, [analysis, page])

  const title = NAV.find((n) => n.id === page)?.label ?? ''

  const body = () => {
    if (page === 'data') return <DataPage />
    if (page === 'metodologi') return <MethodologyPage />
    if (!analysis)
      return (
        <EmptyState
          ikon="unggah"
          title="Belum ada data untuk dianalisis"
          message="Unggah berkas notifikasi pada halaman Data & Upload terlebih dahulu."
          action={
            <button className="btn btn-utama" onClick={() => setPage('data')}>
              Ke halaman Data &amp; Upload
            </button>
          }
        />
      )
    switch (page) {
      case 'equipment':
        return <EquipmentPage />
      case 'fs':
        return <FsPage />
      case 'weibull':
        return <WeibullPage />
      case 'rbd':
        return <RbdPage />
      case 'montecarlo':
        return <MonteCarloPage />
      case 'pm':
        return <PmPage />
      case 'cost':
        return <CostPage />
      case 'rekomendasi':
        return <RecommendationPage />
      default:
        return null
    }
  }

  return (
    <div className="flex h-full">
      <Sidebar
        page={page}
        setPage={setPage}
        terbuka={menuTerbuka}
        onTutup={() => setMenuTerbuka(false)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          onOpenSettings={() => setSettings(true)}
          menuTerbuka={menuTerbuka}
          onToggleMenu={() => setMenuTerbuka((v) => !v)}
        />
        <main className="flex-1 overflow-y-auto px-4 py-5 sm:px-5">
          <h2 className="mb-4 text-lg font-semibold tracking-tight text-biru-800">{title}</h2>
          <div className="mx-auto max-w-[1600px]">{body()}</div>
        </main>
      </div>
      <SettingsDrawer open={settings} onClose={() => setSettings(false)} />
      <Toasts />
    </div>
  )
}
