'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../ThemeContext';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const Icon = theme === 'dark' ? Sun : Moon;
  return (
    <button
      onClick={toggleTheme}
      aria-label="Toggle theme"
      className="inline-flex h-8 w-8 items-center justify-center rounded-full hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
    >
      <Icon size={16} />
    </button>
  );
}

