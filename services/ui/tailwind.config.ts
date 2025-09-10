import type { Config } from 'tailwindcss';
import containerQueries from '@tailwindcss/container-queries';

export const tokens = {
  spacing: {
    1: 'var(--space-1)',
    2: 'var(--space-2)',
    3: 'var(--space-3)',
    4: 'var(--space-4)',
    5: 'var(--space-5)',
    6: 'var(--space-6)',
  },
  colors: {
    background: 'hsl(var(--background))',
    foreground: 'hsl(var(--foreground))',
    muted: {
      DEFAULT: 'hsl(var(--muted))',
      foreground: 'hsl(var(--muted-foreground))',
    },
    card: {
      DEFAULT: 'hsl(var(--card))',
      foreground: 'hsl(var(--card-foreground))',
    },
    border: 'hsl(var(--border))',
    input: 'hsl(var(--input))',
    primary: {
      DEFAULT: 'hsl(var(--primary))',
      foreground: 'hsl(var(--primary-foreground))',
    },
    secondary: {
      DEFAULT: 'hsl(var(--secondary))',
      foreground: 'hsl(var(--secondary-foreground))',
    },
    accent: {
      DEFAULT: 'hsl(var(--accent))',
      foreground: 'hsl(var(--accent-foreground))',
    },
    ring: 'hsl(var(--ring))',
  },
  lightColors: {
    background: 'hsl(var(--light-background))',
    foreground: 'hsl(var(--light-foreground))',
    muted: {
      DEFAULT: 'hsl(var(--light-muted))',
      foreground: 'hsl(var(--light-muted-foreground))',
    },
    card: {
      DEFAULT: 'hsl(var(--light-card))',
      foreground: 'hsl(var(--light-card-foreground))',
    },
    border: 'hsl(var(--light-border))',
    input: 'hsl(var(--light-input))',
    primary: {
      DEFAULT: 'hsl(var(--light-primary))',
      foreground: 'hsl(var(--light-primary-foreground))',
    },
    secondary: {
      DEFAULT: 'hsl(var(--light-secondary))',
      foreground: 'hsl(var(--light-secondary-foreground))',
    },
    accent: {
      DEFAULT: 'hsl(var(--light-accent))',
      foreground: 'hsl(var(--light-accent-foreground))',
    },
    ring: 'hsl(var(--light-ring))',
  },
  radii: {
    lg: 'var(--radius-lg)',
    md: 'var(--radius-md)',
    sm: 'var(--radius-sm)',
    full: 'var(--radius-full)',
  },
  fontSize: {
    xs: ['var(--text-xs)', { lineHeight: '1rem' }],
    sm: ['var(--text-sm)', { lineHeight: '1.25rem' }],
    base: ['var(--text-base)', { lineHeight: '1.5rem' }],
    lg: ['var(--text-lg)', { lineHeight: '1.75rem' }],
    xl: ['var(--text-xl)', { lineHeight: '1.75rem' }],
    '2xl': ['var(--text-2xl)', { lineHeight: '2rem' }],
  },
  shadows: {
    soft: 'var(--shadow-soft)',
  },
  brand: {
    green: 'hsl(var(--brand-green))',
    blue: 'hsl(var(--brand-blue))',
    orange: 'hsl(var(--brand-orange))',
    red: 'hsl(var(--brand-red))',
    purple: 'hsl(var(--brand-purple))',
  },
} as const;

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  darkMode: ['class'],
  theme: {
    extend: {
      spacing: tokens.spacing,
      colors: { ...tokens.colors, brand: tokens.brand },
      borderRadius: tokens.radii,
      boxShadow: tokens.shadows,
      fontSize: tokens.fontSize as any,
      fontFamily: {
        sans: ['var(--font-sans)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [containerQueries],
};

export default config;
