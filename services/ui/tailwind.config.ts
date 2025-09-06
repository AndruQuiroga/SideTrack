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
    lg: '12px',
    md: '10px',
    sm: '8px',
    full: '9999px',
  },
};

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  darkMode: ['class'],
  theme: {
    extend: {
      spacing: tokens.spacing,
      colors: tokens.colors,
      borderRadius: tokens.radii,
      boxShadow: {
        soft: '0 10px 30px rgba(0,0,0,0.12)',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [containerQueries],
};

export default config;
