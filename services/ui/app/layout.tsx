export const metadata = {
  title: 'SideTrack',
  description: 'Taste trajectory dashboard',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui, sans-serif', margin: 0 }}>
        <header style={{ padding: '12px 16px', borderBottom: '1px solid #eee' }}>
          <strong>SideTrack</strong>
        </header>
        <main style={{ padding: 16 }}>{children}</main>
      </body>
    </html>
  );
}

