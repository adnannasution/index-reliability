/** @type {import('tailwindcss').Config} */

/*
 * Sistem desain mengikuti gaya visual pertamina.com:
 *   font    : Plus Jakarta Sans (400 / 500 / 600 / 700)
 *   primer  : #0B2F9F  biru korporat
 *   aksen   : #E21F23  merah Pertamina
 *   netral  : skala slate
 *   radius  : 4 / 6 / 8 px, tombol berbentuk pill
 *   bayangan: nyaris tidak dipakai; pemisah visual memakai garis tepi
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        biru: {
          50: '#eef2fd',
          100: '#dbe3fb',
          200: '#b9c8f7',
          300: '#8ea5f0',
          400: '#5c7ae6',
          500: '#2f52cf',
          600: '#1a3cb4',
          700: '#0B2F9F',
          800: '#0a2680',
          900: '#0a1f63',
          950: '#061240',
        },
        merah: {
          50: '#fdeef0',
          100: '#fbdadd',
          200: '#f6b6bc',
          300: '#ef8a93',
          400: '#e5525f',
          500: '#E21F23',
          600: '#c2181c',
          700: '#9d1418',
          800: '#7c1316',
          900: '#631316',
        },
        hijau: {
          50: '#eefaf3',
          100: '#d6f2e2',
          400: '#3fb883',
          500: '#1f9d68',
          600: '#137d52',
          700: '#0f6343',
        },
        kuning: {
          50: '#fef7ec',
          100: '#fdeacd',
          400: '#efab3c',
          500: '#dd8b16',
          600: '#b96c10',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      fontSize: {
        // Skala tipografi yang mengikuti pertamina.com (16 px / 28 px untuk isi).
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
        xs: ['0.75rem', { lineHeight: '1.125rem' }],
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],
        base: ['0.875rem', { lineHeight: '1.5rem' }],
        lg: ['1rem', { lineHeight: '1.75rem' }],
        xl: ['1.125rem', { lineHeight: '1.625rem' }],
        '2xl': ['1.375rem', { lineHeight: '1.875rem' }],
        '3xl': ['1.75rem', { lineHeight: '2.125rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        md: '0.375rem',
        lg: '0.5rem',
        xl: '0.625rem',
      },
      boxShadow: {
        // Sangat halus; dipakai hanya untuk elemen melayang (dropdown, panel).
        panel: '0 1px 2px rgba(15,23,42,.04), 0 8px 24px rgba(15,23,42,.08)',
        naik: '0 1px 3px rgba(15,23,42,.08)',
      },
      keyframes: {
        masuk: {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'none' },
        },
        geser: {
          from: { opacity: '0', transform: 'translateX(16px)' },
          to: { opacity: '1', transform: 'none' },
        },
        kilau: { '100%': { transform: 'translateX(100%)' } },
      },
      animation: {
        masuk: 'masuk .24s cubic-bezier(.16,1,.3,1)',
        geser: 'geser .26s cubic-bezier(.16,1,.3,1)',
        kilau: 'kilau 1.7s infinite',
      },
    },
  },
  plugins: [],
}
