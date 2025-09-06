export const metadata = {
  title: 'SideTrack',
  description: 'Taste trajectory dashboard',
};

import './globals.css';
import AppShell from '../components/AppShell';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
