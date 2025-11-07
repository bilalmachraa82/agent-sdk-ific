/**
 * Root Layout
 * Wraps entire application with providers
 */

import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'EVF Portugal 2030 - Plataforma de Candidaturas',
  description: 'Automatize a criação de Estudos de Viabilidade Financeira para fundos PT2030, PRR e SITCE',
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#3b82f6',
};

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: false,
    },
  },
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
