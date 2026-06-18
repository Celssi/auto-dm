/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0e14',
        'bg-elevated': '#0f1419',
        panel: '#141c28',
        'panel-hover': '#1a2435',
        border: '#263044',
        'border-light': '#354158',
        accent: '#d4af37',
        'accent-dim': '#a8882a',
        muted: '#8b9cb3',
        success: '#34d399',
        warning: '#fbbf24',
        danger: '#f87171',
      },
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        display: ['"Cinzel"', 'Georgia', 'serif'],
        sheet: ['"Bookman Old Style"', 'Georgia', 'serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(ellipse at top, rgba(212, 175, 55, 0.06) 0%, transparent 55%)',
      },
    },
  },
  plugins: [],
};
