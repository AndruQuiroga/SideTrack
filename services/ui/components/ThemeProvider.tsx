'use client';
import { useCallback, useMemo, type ReactNode } from 'react';
import { ThemeProvider as NextThemeProvider, useTheme as useNextTheme } from 'next-themes';
import { Theme, ThemeContext } from './ThemeContext';

function ThemeContextBridge({ children }: { children: ReactNode }) {
  const { resolvedTheme, theme: storedTheme, setTheme } = useNextTheme();

  const activeTheme = useMemo<Theme>(() => {
    if (resolvedTheme === 'dark' || resolvedTheme === 'light') return resolvedTheme;
    if (storedTheme === 'dark' || storedTheme === 'light') return storedTheme;
    return 'dark';
  }, [resolvedTheme, storedTheme]);

  const setThemePreference = useCallback(
    (next: Theme) => {
      setTheme(next);
    },
    [setTheme],
  );

  const toggleTheme = useCallback(() => {
    setThemePreference(activeTheme === 'dark' ? 'light' : 'dark');
  }, [activeTheme, setThemePreference]);

  const value = useMemo(
    () => ({
      theme: activeTheme,
      setTheme: setThemePreference,
      toggleTheme,
    }),
    [activeTheme, setThemePreference, toggleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export default function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <NextThemeProvider attribute="class" defaultTheme="dark">
      <ThemeContextBridge>{children}</ThemeContextBridge>
    </NextThemeProvider>
  );
}

