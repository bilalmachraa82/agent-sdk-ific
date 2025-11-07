/**
 * Financial Metrics Visualization
 * Charts and displays for VALF, TRF, payback, and cash flows
 */

'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { TrendingDown, TrendingUp, Clock, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatCurrency, formatPercent, isVALFCompliant, isTRFCompliant } from '@/lib/utils';
import apiClient from '@/lib/api-client';

interface FinancialMetricsProps {
  evfId: string;
}

export function FinancialMetrics({ evfId }: FinancialMetricsProps) {
  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ['financial-metrics', evfId],
    queryFn: () => apiClient.getFinancialMetrics(evfId),
  });

  const cashFlowData = useMemo(() => {
    if (!metrics?.cash_flows) return [];
    return metrics.cash_flows.map((value, index) => ({
      year: `Ano ${index + 1}`,
      value: value,
    }));
  }, [metrics]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 w-24 bg-gray-200 rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-32 bg-gray-200 rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <Card className="p-6">
        <p className="text-center text-gray-500">
          Erro ao carregar métricas financeiras
        </p>
      </Card>
    );
  }

  const valfCompliant = isVALFCompliant(metrics.valf);
  const trfCompliant = isTRFCompliant(metrics.trf);

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* VALF */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-gray-600">
                VALF (NPV)
              </CardTitle>
              {valfCompliant ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600" />
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(metrics.valf)}
            </div>
            <div className="flex items-center mt-2">
              <TrendingDown className="h-4 w-4 mr-1 text-gray-500" />
              <span className="text-xs text-gray-500">
                {valfCompliant ? 'Elegível PT2030' : 'Não elegível'}
              </span>
            </div>
            <Badge
              variant={valfCompliant ? 'default' : 'destructive'}
              className="mt-2"
            >
              {valfCompliant ? 'VALF < 0' : 'VALF ≥ 0'}
            </Badge>
          </CardContent>
        </Card>

        {/* TRF */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-gray-600">
                TRF (IRR)
              </CardTitle>
              {trfCompliant ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600" />
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPercent(metrics.trf)}
            </div>
            <div className="flex items-center mt-2">
              <TrendingUp className="h-4 w-4 mr-1 text-gray-500" />
              <span className="text-xs text-gray-500">
                {trfCompliant ? 'Elegível PT2030' : 'Não elegível'}
              </span>
            </div>
            <Badge
              variant={trfCompliant ? 'default' : 'destructive'}
              className="mt-2"
            >
              {trfCompliant ? 'TRF < 4%' : 'TRF ≥ 4%'}
            </Badge>
          </CardContent>
        </Card>

        {/* Payback */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">
              Payback Period
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metrics.payback.toFixed(1)} anos
            </div>
            <div className="flex items-center mt-2">
              <Clock className="h-4 w-4 mr-1 text-gray-500" />
              <span className="text-xs text-gray-500">
                Período de retorno
              </span>
            </div>
            <Badge variant="secondary" className="mt-2">
              {metrics.payback < 5 ? 'Rápido' : metrics.payback < 8 ? 'Médio' : 'Longo'}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* Cash Flow Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Projeção de Cash Flows</CardTitle>
          <CardDescription>
            Fluxos de caixa projetados para 10 anos (valores em €)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={cashFlowData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis tickFormatter={(value) => formatCurrency(value)} />
              <Tooltip
                formatter={(value: number) => [formatCurrency(value), 'Cash Flow']}
              />
              <Bar dataKey="value" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Additional Ratios */}
      {metrics.ratios && Object.keys(metrics.ratios).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Rácios Financeiros</CardTitle>
            <CardDescription>
              Indicadores adicionais de viabilidade
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Object.entries(metrics.ratios).map(([key, value]) => (
                <div key={key} className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">
                    {key.replace(/_/g, ' ').toUpperCase()}
                  </p>
                  <p className="text-lg font-semibold">
                    {typeof value === 'number' ? value.toFixed(2) : value}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
