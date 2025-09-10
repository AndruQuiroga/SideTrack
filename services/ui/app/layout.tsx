export const metadata = {
  title: 'SideTrack',
  description: 'Taste trajectory dashboard',
};

import './globals.css';
import PageTransition from '../components/PageTransition';
import { Inter } from 'next/font/google';
import Providers from './providers';
import ThemeProvider from '../components/ThemeProvider';
import Header from '../components/layout/Header';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider>
          <Providers>
            <PageTransition>
              <Header />
              <main className="container mx-auto w-full max-w-6xl overflow-x-hidden px-4 py-6">{children}</main>
            </PageTransition>
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}

