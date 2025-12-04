// app/register/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api';
import { isAuthenticated, setAuthToken, setUser } from '@/lib/auth';
import { extractErrorMessage } from '@/lib/api';
import type { RegisterData, AuthResponse } from '@/types';

export default function RegisterPage() {
  const router = useRouter();

  const [form, setForm] = useState<RegisterData>({
    full_name: '',
    email: '',
    username: '',
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

    if (!form.full_name || !form.email || !form.username || !form.password) {
      setError('Please fill in all fields');
      return;
    }

    if (form.password.length < 6) {
      setError('Password should be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      const response: AuthResponse = await authAPI.register(form);
      setAuthToken(response.access_token);
      if (response.user) {
        setUser(response.user);
      }
      router.replace('/dashboard');
    } catch (err: unknown) {
      console.error('Register error:', err);
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
          <h1 className="text-xl font-semibold">Create your account</h1>
          <p className="text-xs text-slate-400 mt-1">
            A few details and you&apos;re ready to train.
          </p>
        </div>

        {error && (
          <div className="mb-3 text-xs text-red-400 bg-red-950/40 border border-red-900 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3 text-sm">
          <div>
            <label
              className="block text-xs text-slate-400 mb-1"
              htmlFor="full_name"
            >
              Full name
            </label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              value={form.full_name ?? ''}
              onChange={handleChange}
              className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-sm outline-none focus:border-sky-500"
              placeholder="Jane Doe"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-sm outline-none focus:border-sky-500"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              value={form.username}
              onChange={handleChange}
              className="w-full rounded-md bg-slate-950 border border-slate-700 px-3 py-2 text-sm outline-none focus:border-sky-500"
              placeholder="athlete123"
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
              autoComplete="new-password"
              value={form.password ?? ''}
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
            {loading ? 'Creating account...' : 'Sign up'}
          </button>
        </form>

        <div className="mt-4 text-xs text-slate-400 text-center">
          Already have an account?{' '}
          <button
            type="button"
            onClick={() => router.push('/login')}
            className="text-sky-400 hover:underline"
          >
            Log in
          </button>
        </div>
      </div>
    </div>
  );
}
