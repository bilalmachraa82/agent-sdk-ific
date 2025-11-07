/**
 * EVFs List Page
 * Full list of all EVF projects with filtering
 */

'use client';

import Link from 'next/link';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EVFList } from '@/components/evf-list';

export default function EVFsPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Projetos EVF</h1>
          <p className="text-gray-600 mt-1">
            Gerir e visualizar todos os estudos de viabilidade
          </p>
        </div>
        <Link href="/dashboard/upload">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Novo EVF
          </Button>
        </Link>
      </div>

      {/* EVF List */}
      <EVFList />
    </div>
  );
}
