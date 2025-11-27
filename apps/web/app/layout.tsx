import type { Metadata } from 'next';
import { Space_Grotesk } from 'next/font/google';

import { Navbar } from './components/navbar';
import './globals.css';

const spaceGrotesk = Space_Grotesk({ subsets: ['latin'], display: 'swap' });

export const metadata: Metadata = {
  title: 'Sidetrack Club',
  description: 'Discord-powered album club, public archive, and social music tracker.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={spaceGrotesk.className}>
        <div className="flex min-h-screen flex-col bg-sidetrack-bg">
          <Navbar />
          <div className="flex-1">{children}</div>
        </div>
      </body>
    </html>
  );
}
