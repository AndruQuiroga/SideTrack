'use client';

import { useState, FormEvent, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiFetch } from '../../lib/api';
import { useAuth } from '../../lib/auth';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const params = useSearchParams();
  const router = useRouter();
  const { setUserId } = useAuth();
  const next = params.get('next');

  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, []);

  async function loginRequest() {
    return apiFetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
  }

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError('');
    const res = await loginRequest();
    if (res.ok) {
      router.push(next || '/');
    } else {
      const data = await res.json().catch(() => ({}));
      setError(data.detail || `${res.status} ${res.statusText}`);
    }
  }

  async function handleRegister() {
    setError('');
    const res = await apiFetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) {
      const loginRes = await loginRequest();
      if (loginRes.ok) {
        router.push(next || '/');
      } else {
        const data = await loginRes.json().catch(() => ({}));
        setError(data.detail || `${loginRes.status} ${loginRes.statusText}`);
      }
    } else {
      const data = await res.json().catch(() => ({}));
      setError(data.detail || `${res.status} ${res.statusText}`);
    }
  }

  async function handleGoogle() {
    setError('');
    const g: any = (window as any).google;
    if (!g?.accounts?.id) {
      setError('Google services unavailable');
      return;
    }
    g.accounts.id.initialize({
      client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
      callback: async (response: any) => {
        const r = await apiFetch('/api/auth/continue/google', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: response.credential }),
        });
        if (r.ok) {
          const data = await r.json().catch(() => ({}));
          setUserId((data as any)?.user_id || '');
          router.push(next || '/');
        } else {
          const data = await r.json().catch(() => ({}));
          setError(data.detail || `${r.status} ${r.statusText}`);
        }
      },
    });
    g.accounts.id.prompt();
  }

  return (
    <section className="max-w-sm mx-auto mt-20 space-y-4">
      <h2 className="text-xl font-bold">Login</h2>
      {error && (
        <div role="alert" className="text-red-500">
          {error}
        </div>
      )}
      <form onSubmit={handleLogin} className="space-y-2">
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full rounded border px-2 py-1 text-black"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded border px-2 py-1 text-black"
        />
        <div className="flex gap-2">
          <button type="submit" className="rounded bg-emerald-500 px-3 py-1 text-white">
            Login
          </button>
          <button
            type="button"
            onClick={handleRegister}
            className="rounded bg-sky-500 px-3 py-1 text-white"
          >
            Register
          </button>
        </div>
      </form>
      <button
        type="button"
        onClick={handleGoogle}
        className="w-full rounded border bg-white px-3 py-1 text-black"
      >
        Continue with Google
      </button>
    </section>
  );
}
