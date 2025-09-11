'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../lib/auth';
import { queryClient } from '../lib/query';
import { NavProvider } from '../components/NavContext';

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <NavProvider>{children}</NavProvider>
      </QueryClientProvider>
    </AuthProvider>
  );
}
