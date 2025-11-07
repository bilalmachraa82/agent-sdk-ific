/**
 * Settings Page
 * Tenant settings and usage information
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { formatCurrency, formatCompactNumber } from '@/lib/utils';
import { useStore } from '@/lib/store';
import apiClient from '@/lib/api-client';

export default function SettingsPage() {
  const { tenant, user } = useStore();

  const { data: usage } = useQuery({
    queryKey: ['tenant-usage'],
    queryFn: () => apiClient.getTenantUsage(),
  });

  return (
    <div className="max-w-4xl space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Definições</h1>
        <p className="text-gray-600 mt-1">
          Gerir a sua organização e utilização
        </p>
      </div>

      {/* Tenant Info */}
      <Card>
        <CardHeader>
          <CardTitle>Informação da Organização</CardTitle>
          <CardDescription>
            Detalhes da sua conta e subscrição
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-500">Nome</p>
              <p className="text-sm text-gray-900 mt-1">{tenant?.name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Slug</p>
              <p className="text-sm text-gray-900 mt-1">{tenant?.slug}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Plano</p>
              <Badge variant="outline" className="mt-1">
                {tenant?.plan}
              </Badge>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">ID</p>
              <p className="text-sm text-gray-900 mt-1 font-mono text-xs">
                {tenant?.id}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* User Info */}
      <Card>
        <CardHeader>
          <CardTitle>Informação do Utilizador</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-500">Email</p>
              <p className="text-sm text-gray-900 mt-1">{user?.email}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Nome</p>
              <p className="text-sm text-gray-900 mt-1">{user?.name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Função</p>
              <Badge variant="outline" className="mt-1">
                {user?.role}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Usage Stats */}
      {usage && (
        <Card>
          <CardHeader>
            <CardTitle>Utilização Mensal</CardTitle>
            <CardDescription>
              Estatísticas do mês corrente
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  EVFs Processados
                </span>
                <span className="text-sm font-semibold text-gray-900">
                  {usage.evfs_processed}
                </span>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  Tokens Consumidos
                </span>
                <span className="text-sm font-semibold text-gray-900">
                  {formatCompactNumber(usage.tokens_consumed)}
                </span>
              </div>
              <Progress value={(usage.tokens_consumed / 1000000) * 100} />
              <p className="text-xs text-gray-500 mt-1">
                Limite: 1M tokens/mês
              </p>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  Custo Total
                </span>
                <span className="text-sm font-semibold text-gray-900">
                  {formatCurrency(usage.cost_euros)}
                </span>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  Armazenamento
                </span>
                <span className="text-sm font-semibold text-gray-900">
                  {usage.storage_mb.toFixed(0)} MB
                </span>
              </div>
              <Progress value={(usage.storage_mb / 1000) * 100} />
              <p className="text-xs text-gray-500 mt-1">
                Limite: 1GB
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* API Settings - Future */}
      <Card>
        <CardHeader>
          <CardTitle>API e Integrações</CardTitle>
          <CardDescription>
            Configurações avançadas (disponível em breve)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            Funcionalidade em desenvolvimento
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
