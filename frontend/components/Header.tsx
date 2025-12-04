// components/Header.tsx
'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { logout, getUser } from '@/lib/auth';
import { LogOut, Activity, Target, BarChart3 } from 'lucide-react';

export default function Header() {
  const router = useRouter();
  const user = getUser();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center space-x-2">
            <Activity className="h-8 w-8 text-blue-600" />
            <span className="text-xl font-bold text-gray-900">AI Triathlon Coach</span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex space-x-8">
            <Link 
              href="/dashboard" 
              className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-1"
            >
              <BarChart3 className="h-4 w-4" />
              <span>Dashboard</span>
            </Link>
            <Link 
              href="/goals" 
              className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-1"
            >
              <Target className="h-4 w-4" />
              <span>Goals</span>
            </Link>
          </nav>

          {/* User menu */}
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-700">
              {user?.full_name || user?.username || 'User'}
            </span>
            <button
              onClick={handleLogout}
              className="flex items-center space-x-1 text-gray-700 hover:text-red-600 px-3 py-2 rounded-md text-sm font-medium"
            >
              <LogOut className="h-4 w-4" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
