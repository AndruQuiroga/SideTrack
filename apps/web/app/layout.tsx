import type { Metadata } from 'next';
import { Space_Grotesk } from 'next/font/google';

import { Navbar } from './components/navbar';
import './globals.css';
import { ToastViewport } from './components/toast';
import { PwaRegister } from './components/pwa-register';

const spaceGrotesk = Space_Grotesk({ subsets: ['latin'], display: 'swap' });

export const metadata: Metadata = {
  title: 'Sidetrack Club',
  description: 'Discord-powered album club, public archive, and social music tracker.',
  manifest: '/manifest.json',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={spaceGrotesk.className}>
        <ThemeScript />
        <div className="flex min-h-screen flex-col bg-sidetrack-bg">
          <Navbar />
          <div className="flex-1">{children}</div>
        </div>
        <ToastViewport />
        <PwaRegister />
      </body>
    </html>
  );
}

function ThemeScript() {
  // Apply saved or system theme before paint to avoid FOUC
  const code = `(() => { try {
    const saved = localStorage.getItem('sidetrack-theme');
    const systemDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (systemDark ? 'dark' : 'light');
    const root = document.documentElement;
    root.classList.remove('theme-dark','theme-light');
    root.classList.add(theme === 'dark' ? 'theme-dark' : 'theme-light');
  } catch(_){} })();`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
