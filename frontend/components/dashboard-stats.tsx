/**
 * Dashboard Statistics Component
 * Displays key metrics and KPIs in card format
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { TrendingUp, FileText, Clock, DollarSign } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatCompactNumber } from '@/lib/utils';
import apiClient from '@/lib/api-client';

export function DashboardStats() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiClient.getDashboardStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const statCards = [
    {
      title: 'EVFs Processados',
      value: stats?.completed_evfs || 0,
      total: stats?.total_evfs || 0,
      icon: FileText,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      title: 'Em Processamento',
      value: stats?.processing_evfs || 0,
      icon: Clock,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
    {
      title: 'Custo Total',
      value: stats?.total_cost_euros || 0,
      format: 'currency',
      icon: DollarSign,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      title: 'Tempo Médio',
      value: stats?.avg_processing_time_hours || 0,
      format: 'time',
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
  ];

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 w-24 bg-gray-200 rounded" />
              <div className="h-8 w-8 bg-gray-200 rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-20 bg-gray-200 rounded mb-2" />
              <div className="h-3 w-32 bg-gray-200 rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {statCards.map((stat, index) => {
        const Icon = stat.icon;
        let displayValue: string;

        if (stat.format === 'currency') {
          displayValue = formatCurrency(stat.value);
        } else if (stat.format === 'time') {
          displayValue = `${stat.value.toFixed(1)}h`;
        } else {
          displayValue = formatCompactNumber(stat.value);
        }

        return (
          <Card key={index} className="hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">
                {stat.title}
              </CardTitle>
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <Icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{displayValue}</div>
              {stat.total && (
                <p className="text-xs text-gray-500 mt-1">
                  de {formatCompactNumber(stat.total)} total
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
