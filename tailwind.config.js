/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary gradient colors
        primary: {
          DEFAULT: '#667eea',
          dark: '#5568d3',
          light: '#764ba2',
        },
        // Secondary colors
        secondary: {
          DEFAULT: '#0066cc',
        },
        // Status colors
        success: {
          DEFAULT: '#22c55e',
          dark: '#15803d',
          light: '#c6f6d5',
        },
        error: {
          DEFAULT: '#dc2626',
          dark: '#c53030',
          light: '#fed7d7',
        },
        warning: {
          DEFAULT: '#ff9800',
          light: '#ffc107',
        },
        // Neutral palette
        neutral: {
          50: '#f7fafc',
          100: '#edf2f7',
          200: '#e2e8f0',
          300: '#cbd5e0',
          400: '#a0aec0',
          500: '#718096',
          600: '#4a5568',
          700: '#2d3748',
          800: '#1a202c',
        },
      },
      backgroundImage: {
        'gradient-primary': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 4px 16px rgba(0, 0, 0, 0.12)',
        'modal': '0 20px 60px rgba(0, 0, 0, 0.3)',
        'primary': '0 8px 24px rgba(102, 126, 234, 0.4)',
        'primary-sm': '0 4px 12px rgba(102, 126, 234, 0.4)',
      },
      animation: {
        'slideUp': 'slideUp 0.5s ease-out',
        'slideDown': 'slideDown 0.3s ease',
        'fadeIn': 'fadeIn 0.3s ease',
        'shake': 'shake 0.3s ease',
        'blob': 'blob 7s infinite',
        'pulse-soft': 'pulse-soft 4s ease-in-out infinite',
        'scale-in': 'scale-in 0.3s ease-out',
        'fade-in-up': 'fade-in-up 0.5s ease-out',
        'shimmer': 'shimmer 2s linear infinite',
        'spin-slow': 'spin 8s linear infinite',
      },
      keyframes: {
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '25%': { transform: 'translateX(-5px)' },
          '75%': { transform: 'translateX(5px)' },
        },
        blob: {
          '0%': { transform: 'translate(0px, 0px) scale(1)' },
          '33%': { transform: 'translate(30px, -50px) scale(1.1)' },
          '66%': { transform: 'translate(-20px, 20px) scale(0.9)' },
          '100%': { transform: 'translate(0px, 0px) scale(1)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '0.8' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.9)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}
