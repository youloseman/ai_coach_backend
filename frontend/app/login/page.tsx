// app/login/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api';
import { isAuthenticated, setAuthToken, setUser } from '@/lib/auth';
import { extractErrorMessage } from '@/lib/api';
import type { LoginCredentials, AuthResponse } from '@/types';

export default function LoginPage() {
  const router = useRouter();

  const [form, setForm] = useState<LoginCredentials>({
    email: '',
    password: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace('/dashboard');
    }
  }, [router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!form.email || !form.password) {
      setError('Please enter email and password');
      return;
    }

    setLoading(true);

    try {
      const response: AuthResponse = await authAPI.login(form);
      // ожидаем, что в ответе есть access_token и user
      setAuthToken(response.access_token);
      if (response.user) {
        setUser(response.user);
      }
      router.replace('/dashboard');
    } catch (err: unknown) {
      console.error('Login error:', err);
      const message = extractErrorMessage(err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="mb-5">
          <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">
            AI Triathlon Coach
          </div>
          <h1 className="text-xl font-semibold">Log in to your account</h1>
          <p className="text-xs text-slate-400 mt-1">
            Use your email and password to access your dashboard.
          </p>
        </div>

        {error && (
          <div className="mb-3 text-xs text-red-400 bg-red-950/40 border border-red-900 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3 text-sm">
          <div>
            <label className="block text-xs text-slate-400 mb-1" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={handleChange}
              className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-sm outline-none focus:border-sky-500"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label
              className="block text-xs text-slate-400 mb-1"
              htmlFor="password"
            >
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={form.password}
              onChange={handleChange}
              className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-sm outline-none focus:border-sky-500"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 px-4 py-2 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-sm font-medium"
          >
            {loading ? 'Logging in...' : 'Log in'}
          </button>
        </form>

        <div className="mt-4 text-xs text-slate-400 text-center">
          Don&apos;t have an account?{' '}
          <button
            type="button"
            onClick={() => router.push('/register')}
            className="text-sky-400 hover:underline"
          >
            Sign up
          </button>
        </div>
      </div>
    </div>
  );
}
