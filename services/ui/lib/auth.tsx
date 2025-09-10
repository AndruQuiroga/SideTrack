'use client';

import { createContext, useContext, useEffect, useState } from 'react';

interface AuthContextValue {
  userId: string;
  setUserId: (id: string) => void;
}

const AuthContext = createContext<AuthContextValue>({ userId: '', setUserId: () => {} });

let currentUserId = '';
export function getUserId() {
  return currentUserId;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserId] = useState('');

  useEffect(() => {
    const match = document.cookie.match(/(?:^|; )uid=([^;]+)/);
    if (match) {
      setUserId(decodeURIComponent(match[1]));
    }
  }, []);

  useEffect(() => {
    currentUserId = userId;
  }, [userId]);

  return <AuthContext.Provider value={{ userId, setUserId }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
