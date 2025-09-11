'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../lib/auth';
import { queryClient } from '../lib/query';
import { NavProvider } from '../components/NavContext';
import ToastProvider from '../components/ToastProvider';

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <AuthProvider>
        <QueryClientProvider client={queryClient}>
          <NavProvider>{children}</NavProvider>
        </QueryClientProvider>
      </AuthProvider>
    </ToastProvider>
  );
}
