/** Halaman Metodologi & Referensi (§11): setiap rumus ditautkan ke sumbernya. */
import { useEffect } from 'react'
import { useStore } from '../store/useStore'
import { Callout, Card, Chip, Loading } from '../components/ui'

export function MethodologyPage() {
  const refs = useStore((s) => s.references)
  const load = useStore((s) => s.loadReferences)

  useEffect(() => {
    void load()
  }, [load])

  if (!refs)
    return (
      <Card title="Metodologi">
        <Loading label="Memuat daftar referensi…" rows={4} />
      </Card>
    )

  return (
    <div className="space-y-5">
      <Card
        title="Metodologi"
        subtitle="Setiap rumus pada aplikasi ini bersumber dari standar atau pustaka akademik"
      >
        <div className="space-y-3">
          <Callout tone="info" title="Prinsip penyusunan">
            Aplikasi ini adalah penerjemahan skrip <code>CDU_PdM_Balongan.m</code> (v3.0) menjadi aplikasi
            web. Skrip tersebut menjadi <strong>sumber kebenaran</strong> untuk metode, parameter default,
            mapping Functional System, struktur RBD, dan daftar grafik. Rumus tidak diubah: hanya
            diterjemahkan bahasanya, dan setiap fungsi perhitungan mencantumkan sumber referensinya di dalam
            kode.
          </Callout>
          <Callout tone="note" title="Data nyata vs sintetis">
            Seluruh angka pada aplikasi ini dihitung dari berkas notifikasi dan order SAP yang Anda unggah.
            Modul MATLAB yang memakai <strong>sensor sintetis</strong> (deteksi anomali autoencoder dan
            prediksi RUL berbasis LSTM) sengaja tidak ditampilkan agar tidak ada nilai yang tampak sebagai
            hasil pengukuran padahal bukan.
          </Callout>
          <Callout tone="warning" title="Penyimpangan yang diketahui terhadap laporan MATLAB">
            Pembandingan terhadap laporan menunjukkan kecocokan penuh pada ketersediaan (8 nilai), keandalan
            misi (16 nilai), interval optimal τ* (255/198/211 hari), dan konstanta
            <code> betaWorkbook</code> heater/vessel/exchanger sampai presisi mesin (~3×10⁻¹⁵). Selisih
            terbesar yang tersisa adalah <strong>0,0015 pada R(30 hari) FS-3</strong>, berasal dari β prior
            kelas <em>vessel</em>: MATLAB memakai <code>fminbnd</code> dengan toleransi bawaan TolX = 10⁻⁴
            pada permukaan likelihood yang hampir datar, sehingga berhenti di β = 0,79042 sedangkan optimum
            sebenarnya β = 0,78725 (nilai negatif log-likelihood-nya lebih kecil: 138,53437 vs 138,53457).
            Tiga metode independen sepakat pada 0,78725 dalam 1,2×10⁻⁸, sehingga nilai pada aplikasi ini lebih
            tepat.
          </Callout>
        </div>
      </Card>

      <Card title="Rumus per modul" subtitle="Pemetaan modul ke rumus dan sumbernya">
        <div className="overflow-auto rounded-lg border border-slate-200">
          <table className="tabel">
            <thead>
              <tr>
                <th style={{ width: '5rem' }}>Modul</th>
                <th style={{ width: '16rem' }}>Nama</th>
                <th>Rumus inti</th>
                <th style={{ width: '18rem' }}>Sumber</th>
              </tr>
            </thead>
            <tbody>
              {refs.modul.map((m: any) => (
                <tr key={m.kode}>
                  <td>
                    <Chip className="bg-biru-50 font-mono text-biru-700">{m.kode}</Chip>
                  </td>
                  <td className="font-medium">{m.nama}</td>
                  <td className="whitespace-normal font-mono text-xs leading-relaxed text-slate-600">
                    {m.rumus}
                  </td>
                  <td className="whitespace-normal text-xs text-slate-600">{m.sumber}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Referensi akademik & standar" subtitle={`${refs.referensi.length} rujukan wajib`}>
        <ol className="space-y-3">
          {refs.referensi.map((r: any) => (
            <li key={r.id} className="flex gap-3 border-b border-slate-100 pb-3 last:border-0 last:pb-0">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-2xs font-semibold text-slate-600">
                {r.id}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-biru-800">{r.kunci}</p>
                <p className="mt-0.5 text-xs italic leading-relaxed text-slate-600">{r.judul}</p>
                <p className="mt-1 text-xs leading-relaxed text-slate-700">{r.dipakai_untuk}</p>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {r.modul.map((m: string) => (
                    <Chip key={m} className="bg-slate-100 font-mono text-slate-600">
                      modul {m}
                    </Chip>
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  )
}
