'use client';

import Script from 'next/script';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { apiFetch } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { handleGoogle } from '../../lib/handleGoogle';
import { useToast } from '../../components/ToastProvider';
import { Music, Sparkles, Spotify, Radio } from 'lucide-react';

interface LoginFields {
  username: string;
  password: string;
}

interface AuthResponse {
  user_id?: string;
  detail?: string;
}

export default function LoginPage() {
  const params = useSearchParams();
  const router = useRouter();
  const next = params.get('next');
  const { setUserId } = useAuth();
  const { show } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFields>();

  async function loginRequest(values: LoginFields) {
    return apiFetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values),
    });
  }

  const onSubmit = handleSubmit(async (values) => {
    show({ title: 'Logging in…', kind: 'info' });
    const res = await loginRequest(values);
    if (res.ok) {
      const data: AuthResponse = await res.json().catch(() => ({}) as AuthResponse);
      setUserId(data.user_id || '');
      router.push(next || '/');
    } else {
      const data: AuthResponse = await res.json().catch(() => ({}) as AuthResponse);
      show({ title: data.detail || `${res.status} ${res.statusText}`, kind: 'error' });
    }
  });

  const onRegister = handleSubmit(async (values) => {
    show({ title: 'Registering…', kind: 'info' });
    const res = await apiFetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values),
    });
    if (res.ok) {
      const loginRes = await loginRequest(values);
      if (loginRes.ok) {
        const data: AuthResponse = await loginRes.json().catch(() => ({}) as AuthResponse);
        setUserId(data.user_id || '');
        router.push(next || '/');
      } else {
        const data: AuthResponse = await loginRes.json().catch(() => ({}) as AuthResponse);
        show({
          title: data.detail || `${loginRes.status} ${loginRes.statusText}`,
          kind: 'error',
        });
      }
    } else {
      const data: AuthResponse = await res.json().catch(() => ({}) as AuthResponse);
      show({ title: data.detail || `${res.status} ${res.statusText}`, kind: 'error' });
    }
  });

  async function handleGoogleClick() {
    await handleGoogle({ next, setUserId, router, show });
  }

  async function handleSpotifyClick() {
    const callback = encodeURIComponent(`${window.location.origin}/spotify/callback`);
    const res = await apiFetch(`/api/auth/spotify/login?callback=${callback}`);
    const data = await res.json().catch(() => ({}));
    if (data.url) window.location.href = data.url;
  }

  async function handleLastfmClick() {
    const callback = encodeURIComponent(`${window.location.origin}/lastfm/callback`);
    const res = await apiFetch(`/api/auth/lastfm/login?callback=${callback}`);
    const data = await res.json().catch(() => ({}));
    if (data.url) window.location.href = data.url;
  }

  return (
    <section className="relative flex min-h-[calc(100dvh-64px)] items-center justify-center px-4">
      <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
      {/* Ambient blobs */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-24 -left-16 h-64 w-64 rounded-full bg-gradient-to-br from-emerald-500/20 via-teal-400/10 to-cyan-400/10 blur-3xl" />
        <div className="absolute -bottom-24 -right-16 h-64 w-64 rounded-full bg-gradient-to-br from-fuchsia-400/10 via-pink-400/10 to-rose-400/10 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md overflow-hidden rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-md shadow-[0_20px_60px_-20px_rgba(0,0,0,0.5)]">
        <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br from-emerald-400/50 via-teal-400/40 to-cyan-400/50 blur-2xl" />
        <div className="flex items-center gap-2 text-emerald-300">
          <Music size={18} />
          <span className="text-xs uppercase tracking-wider">Welcome</span>
        </div>
        <h2 className="mt-2 bg-gradient-to-r from-emerald-400 via-cyan-400 to-fuchsia-400 bg-clip-text text-2xl font-extrabold text-transparent">
          Sign in to SideTrack
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">Your soundtrack, visualized</p>

        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <Input
            placeholder="Username"
            {...register('username', { required: 'Username is required' })}
          />
          {errors.username && <p className="text-xs text-rose-400">{errors.username.message}</p>}
          <Input
            type="password"
            placeholder="Password"
            {...register('password', { required: 'Password is required' })}
          />
          {errors.password && <p className="text-xs text-rose-400">{errors.password.message}</p>}
          <div className="flex gap-2">
            <Button type="submit" className="flex-1">
              Sign in
            </Button>
            <Button type="button" variant="outline" className="flex-1" onClick={onRegister}>
              Create account
            </Button>
          </div>
        </form>

        <div className="my-4 flex items-center gap-3 text-xs text-muted-foreground">
          <div className="h-px flex-1 bg-white/10" />
          or continue with
          <div className="h-px flex-1 bg-white/10" />
        </div>

        <div className="grid grid-cols-1 gap-2">
          <Button
            type="button"
            onClick={handleGoogleClick}
            variant="outline"
            className="w-full bg-white text-black"
          >
            <Sparkles size={16} className="mr-2" /> Continue with Google
          </Button>
          <Button type="button" variant="outline" className="w-full" onClick={handleSpotifyClick}>
            <Spotify size={16} className="mr-2" /> Continue with Spotify
          </Button>
          <Button type="button" variant="outline" className="w-full" onClick={handleLastfmClick}>
            <Radio size={16} className="mr-2" /> Continue with Last.fm
          </Button>
        </div>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          By continuing, you agree to our terms and privacy policy.
        </p>
      </div>
    </section>
  );
}
