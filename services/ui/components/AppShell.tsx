import NavRail from '../components/NavRail';
import ApiStatus from '../app/api-status';
import ToastProvider, { useToast } from './ToastProvider';
import { Sync } from 'lucide-react';

function HeaderActions() {
  const { show } = useToast();
  return (
    <button
      onClick={() =>
        show({ title: 'Sync started', description: 'Fetching listens…', kind: 'info' })
      }
      className="inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
    >
      <Sync size={14} /> Sync
    </button>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <div className="grid min-h-dvh grid-cols-1 md:grid-cols-[240px_1fr]">
        <NavRail />
        <div className="flex min-h-dvh flex-col">
          <header className="sticky top-0 z-10 glass flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="hidden h-8 w-8 rounded-full bg-gradient-to-br from-emerald-400 to-sky-400 md:block" />
              <span className="text-sm text-muted-foreground">Your taste dashboard</span>
            </div>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <HeaderActions />
              <span>
                API: <ApiStatus />
              </span>
            </div>
          </header>
          <main className="container mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
        </div>
      </div>
    </ToastProvider>
  );
}
