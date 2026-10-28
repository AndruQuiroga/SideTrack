import type { Metadata } from 'next';
import { getServerSession } from 'next-auth/next';

import { authOptions } from './lib/auth';
import { Navbar } from './components/navbar';
import { SessionProvider } from './components/session-provider';
import './globals.css';
import { ToastViewport } from './components/toast';
import { PwaRegister } from './components/pwa-register';

// Font class for consistent styling
const fontClassName = 'font-sans';

export const metadata: Metadata = {
  title: 'Sidetrack Club',
  description: 'Your listening history and your album club, in one place.',
  manifest: '/manifest.json',
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);
  return (
    <html lang="en">
      <body className={fontClassName}>
        <SessionProvider session={session}>
          <ThemeScript />
          <a href="#main-content" className="skip-link">
            Skip to content
          </a>
          <div className="app-layout">
            <Navbar />
            <div className="app-content">{children}</div>
          </div>
          <ToastViewport />
          <PwaRegister />
        </SessionProvider>
      </body>
    </html>
  );
}

function ThemeScript() {
  // Apply saved or system theme before paint to avoid FOUC
  const code = `(() => { try {
    const saved = localStorage.getItem('sidetrack-theme');
    const systemDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = (saved === 'dark' || saved === 'light') ? saved : (systemDark ? 'dark' : 'light');
    const root = document.documentElement;
    root.classList.remove('theme-dark','theme-light');
    root.classList.add(theme === 'dark' ? 'theme-dark' : 'theme-light');
  } catch(_){} })();`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
