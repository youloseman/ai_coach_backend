// lib/auth.ts
import type { User } from '@/types';

const TOKEN_KEY = 'token';
const USER_KEY = 'user';

export const setAuthToken = (token: string) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token);
    console.log('💾 setAuthToken called, token saved');
  }
};

export const getAuthToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
};

export const removeAuthToken = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
  }
};

export const setUser = (user: User) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
};

export const getUser = (): User | null => {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
};

export const removeUser = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(USER_KEY);
  }
};

export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};

export const logout = () => {
  removeAuthToken();
  removeUser();
  if (typeof window !== 'undefined') {
    window.location.href = '/login';
  }
};
