'use client';

import { useState, FormEvent } from 'react';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError('');
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) {
      window.location.href = '/account';
    } else {
      setError('Login failed');
    }
  }

  async function handleRegister() {
    setError('');
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) {
      await handleLogin(new Event('submit') as unknown as FormEvent);
    } else {
      setError('Registration failed');
    }
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
    </section>
  );
}
