/**
 * Dashboard Home Page
 * Overview with stats and recent EVFs
 */

'use client';

import Link from 'next/link';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DashboardStats } from '@/components/dashboard-stats';
import { EVFList } from '@/components/evf-list';

export default function DashboardPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Visão geral dos seus projetos EVF
          </p>
        </div>
        <Link href="/dashboard/upload">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Novo EVF
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <DashboardStats />

      {/* Recent EVFs */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Projetos Recentes
        </h2>
        <EVFList />
      </div>
    </div>
  );
}
