import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

const el = document.getElementById('root')
if (!el) throw new Error('Elemen #root tidak ditemukan pada index.html')

createRoot(el).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
