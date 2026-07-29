import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Backend FastAPI berjalan di port 8000 (docker-compose) atau 8010 (manual).
 * Semua permintaan /api diteruskan melalui proxy sehingga frontend tidak perlu
 * tahu alamat backend dan tidak ada masalah CORS saat pengembangan.
 * Ganti target lewat variabel lingkungan VITE_API_TARGET bila perlu.
 */
const env = loadEnv('development', '.', 'VITE_')
const target = env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': { target, changeOrigin: true },
    },
    // Izinkan dev server membaca folder induk repo agar berkas contoh pada
    // ../data/ dapat dibuka langsung saat pengembangan dan pengujian.
    // Pengaturan ini HANYA berlaku untuk dev server, tidak untuk hasil build.
    fs: { allow: ['..'] },
    watch: {
      // Berkas Excel contoh berukuran besar dan kadang terkunci oleh Excel di
      // Windows; mengabaikannya mencegah watcher gagal dengan EBUSY.
      ignored: ['**/data/**', '**/*.xlsx'],
    },
  },
  preview: { port: 4173, host: true },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 4000, // plotly.js memang besar
    rollupOptions: {
      output: {
        manualChunks: {
          plotly: ['plotly.js-dist-min'],
          react: ['react', 'react-dom'],
        },
      },
    },
  },
})
