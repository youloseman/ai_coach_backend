// app/page.tsx  (или frontend_home.tsx, если у тебя так организовано)
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';
import { goalsAPI } from '@/lib/api';

type Status = 'idle' | 'checking' | 'done';

export default function HomePage() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>('idle');

  useEffect(() => {
    const run = async () => {
      if (!isAuthenticated()) {
        router.replace('/login');
        return;
      }

      try {
        setStatus('checking');
        await goalsAPI.getPrimary();
        router.replace('/dashboard');
      } catch {
        // Если primary goal нет (404 или другая ошибка) — ведём на онбординг
        router.replace('/onboarding');
      } finally {
        setStatus('done');
      }
    };

    void run();
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-slate-500 text-sm">
        {status === 'checking'
          ? 'Preparing your dashboard...'
          : 'Redirecting...'}
      </div>
    </div>
  );
}
