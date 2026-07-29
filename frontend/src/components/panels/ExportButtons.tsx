/** Tombol ekspor tabel ke Excel dan CSV. */
import { useState } from 'react'
import { api } from '../../api/client'
import { useStore } from '../../store/useStore'
import { Tombol } from '../ui'

export function ExportButtons({ table }: { table?: string }) {
  const notif = useStore((s) => s.notif)
  const config = useStore((s) => s.config)
  const tanganiGalat = useStore((s) => s.handleError)
  const toast = useStore((s) => s.pushToast)
  const [sibuk, setSibuk] = useState<'xlsx' | 'csv' | null>(null)

  if (!notif) return null

  const jalankan = async (apa: 'xlsx' | 'csv') => {
    setSibuk(apa)
    try {
      if (apa === 'xlsx') await api.exportExcel(notif.dataset_id, config)
      else if (table) await api.exportCsv(table, notif.dataset_id, config)
      toast({ tone: 'success', title: 'Berkas selesai diunduh' })
    } catch (e) {
      tanganiGalat(e, 'Ekspor gagal')
    } finally {
      setSibuk(null)
    }
  }

  return (
    <div className="flex items-center gap-2">
      {table && (
        <Tombol
          kecil
          ikon="unduh"
          memuat={sibuk === 'csv'}
          disabled={sibuk !== null}
          onClick={() => void jalankan('csv')}
        >
          CSV
        </Tombol>
      )}
      <Tombol
        kecil
        ikon="unduh"
        memuat={sibuk === 'xlsx'}
        disabled={sibuk !== null}
        onClick={() => void jalankan('xlsx')}
      >
        Excel lengkap
      </Tombol>
    </div>
  )
}
