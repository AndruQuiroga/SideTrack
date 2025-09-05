export const metadata = {
  title: 'SideTrack',
  description: 'Taste trajectory dashboard',
};

import ApiStatus from './api-status';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui, sans-serif', margin: 0 }}>
        <header
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid #eee',
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          <strong>SideTrack</strong>
          <span>
            <ApiStatus />
          </span>
        </header>
        <main style={{ padding: 16 }}>{children}</main>
      </body>
    </html>
  );
}
