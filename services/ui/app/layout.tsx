export const metadata = {
  title: 'SideTrack',
  description: 'Taste trajectory dashboard',
};

import './globals.css';
import AppShell from '../components/AppShell';
import PageTransition from '../components/PageTransition';
import { ThemeProvider } from 'next-themes';
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <PageTransition>
            <AppShell>{children}</AppShell>
          </PageTransition>
        </ThemeProvider>
      </body>
    </html>
  );
}
