'use client';

import { createContext, useContext, useEffect, useState } from 'react';

interface AuthContextValue {
  userId: string;
}

const AuthContext = createContext<AuthContextValue>({ userId: '' });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserId] = useState('');

  useEffect(() => {
    const match = document.cookie.match(/(?:^|; )uid=([^;]+)/);
    if (match) {
      setUserId(decodeURIComponent(match[1]));
    }
  }, []);

  return <AuthContext.Provider value={{ userId }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
