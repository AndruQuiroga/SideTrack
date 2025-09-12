'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import * as Tooltip from '@radix-ui/react-tooltip';
import { AuthProvider } from '../lib/auth';
import { queryClient } from '../lib/query';
import { NavProvider } from '../components/NavContext';
import ToastProvider from '../components/ToastProvider';

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <AuthProvider>
        <QueryClientProvider client={queryClient}>
          <Tooltip.Provider delayDuration={150} skipDelayDuration={300} disableHoverableContent>
            <NavProvider>{children}</NavProvider>
          </Tooltip.Provider>
        </QueryClientProvider>
      </AuthProvider>
    </ToastProvider>
  );
}
