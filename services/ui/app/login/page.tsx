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

  return (
    <section className="max-w-sm mx-auto mt-20 space-y-4">
      <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
      <h2 className="text-xl font-bold">Login</h2>
      <form onSubmit={onSubmit} className="space-y-2">
        <Input
          placeholder="Username"
          {...register('username', { required: 'Username is required' })}
        />
        {errors.username && <p className="text-sm text-red-500">{errors.username.message}</p>}
        <Input
          type="password"
          placeholder="Password"
          {...register('password', { required: 'Password is required' })}
        />
        {errors.password && <p className="text-sm text-red-500">{errors.password.message}</p>}
        <div className="flex gap-2">
          <Button type="submit">Login</Button>
          <Button type="button" variant="outline" onClick={onRegister}>
            Register
          </Button>
        </div>
      </form>
      <Button
        type="button"
        onClick={handleGoogleClick}
        variant="outline"
        className="w-full bg-white text-black"
      >
        Continue with Google
      </Button>
    </section>
  );
}
