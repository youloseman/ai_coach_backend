'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import type React from 'react';
import { queryClient } from '@/lib/api';

interface AppProvidersProps {
  children: React.ReactNode;
}

export const AppProviders = ({ children }: AppProvidersProps) => {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
};


