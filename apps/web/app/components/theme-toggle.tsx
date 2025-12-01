'use client';

import { useEffect, useState } from 'react';

function applyTheme(theme: 'dark' | 'light') {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  root.classList.remove('theme-dark', 'theme-light');
  root.classList.add(theme === 'dark' ? 'theme-dark' : 'theme-light');
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    if (typeof window === 'undefined') return 'dark';
    return (localStorage.getItem('sidetrack-theme') as 'dark' | 'light') || 'dark';
  });

  useEffect(() => {
    localStorage.setItem('sidetrack-theme', theme);
    applyTheme(theme);
  }, [theme]);

  return (
    <button
      onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
      className="ml-2 hidden items-center gap-2 rounded-full border border-slate-800/80 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-300 shadow-soft transition hover:bg-slate-800/80 md:inline-flex"
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? 'Dark' : 'Light'} theme
    </button>
  );
}
