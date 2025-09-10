'use client';
import { useCallback, useEffect, useState } from 'react';
import { Theme, ThemeContext } from './ThemeContext';

const STORAGE_KEY = 'theme';

function getStoredTheme(): Theme | null {
  if (typeof window === 'undefined') return null;
  const local = localStorage.getItem(STORAGE_KEY);
  if (local === 'light' || local === 'dark') return local as Theme;
  const match = document.cookie.match(/(?:^|; )theme=(light|dark)/);
  return match ? (match[1] as Theme) : null;
}

function getPreferredTheme(): Theme {
  if (typeof window === 'undefined') return 'dark';
  const stored = getStoredTheme();
  if (stored) return stored;
  const prefersDark =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches;
  return prefersDark ? 'dark' : 'light';
}

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>(getPreferredTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', theme === 'dark');
    localStorage.setItem(STORAGE_KEY, theme);
    document.cookie = `${STORAGE_KEY}=${theme}; path=/; max-age=31536000`;
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

