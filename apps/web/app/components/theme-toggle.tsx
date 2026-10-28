'use client';
import { useEffect, useState } from 'react';

export function ThemeToggle() {
  const [theme, setTheme] = useState<'dark' | 'light' | null>(null);
  useEffect(() => {
    setTheme(document.documentElement.classList.contains('theme-dark') ? 'dark' : 'light');
  }, []);
  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.classList.remove('theme-dark', 'theme-light');
    document.documentElement.classList.add(`theme-${next}`);
    try {
      localStorage.setItem('sidetrack-theme', next);
    } catch {
      /* Theme still works without storage. */
    }
    setTheme(next);
  }
  return (
    <button
      type="button"
      className="text-button"
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
      onClick={toggle}
    >
      {theme ? `${theme === 'dark' ? 'Light' : 'Dark'} appearance` : 'Change appearance'}
    </button>
  );
}
