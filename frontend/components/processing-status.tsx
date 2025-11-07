/**
 * Processing Status Component
 * Real-time status display with agent progress
 */

'use client';

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { formatDuration, formatRelativeTime } from '@/lib/utils';
import apiClient from '@/lib/api-client';

interface ProcessingStatusProps {
  evfId: string;
  onComplete?: () => void;
  onError?: () => void;
}

const agentSteps = [
  { name: 'InputAgent', label: 'Validação de Dados', duration: '~30s' },
  { name: 'ComplianceAgent', label: 'Verificação de Compliance', duration: '~45s' },
  { name: 'FinancialModelAgent', label: 'Cálculos Financeiros', duration: '~1m' },
  { name: 'NarrativeAgent', label: 'Geração de Texto', duration: '~2m' },
  { name: 'AuditAgent', label: 'Auditoria Final', duration: '~15s' },
];

export function ProcessingStatus({ evfId, onComplete, onError }: ProcessingStatusProps) {
  const { data: status, isLoading } = useQuery({
    queryKey: ['processing-status', evfId],
    queryFn: () => apiClient.getEVFStatus(evfId),
    refetchInterval: (query) => {
      // Stop polling when completed or failed
      const data = query.state.data;
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
  });

  useEffect(() => {
    if (status?.status === 'completed') {
      onComplete?.();
    } else if (status?.status === 'failed') {
      onError?.();
    }
  }, [status?.status, onComplete, onError]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            <span className="ml-2 text-gray-600">A carregar estado...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!status) {
    return null;
  }

  const currentAgentIndex = agentSteps.findIndex(
    (step) => step.name === status.current_agent
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Estado do Processamento</CardTitle>
            <CardDescription>
              {status.started_at && `Iniciado ${formatRelativeTime(status.started_at)}`}
            </CardDescription>
          </div>
          {status.status === 'processing' && (
            <Badge className="bg-blue-100 text-blue-800">
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              A Processar
            </Badge>
          )}
          {status.status === 'completed' && (
            <Badge className="bg-green-100 text-green-800">
              <CheckCircle className="h-3 w-3 mr-1" />
              Concluído
            </Badge>
          )}
          {status.status === 'failed' && (
            <Badge className="bg-red-100 text-red-800">
              <XCircle className="h-3 w-3 mr-1" />
              Falhado
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Progress */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              Progresso Geral
            </span>
            <span className="text-sm font-medium text-gray-900">
              {status.progress}%
            </span>
          </div>
          <Progress value={status.progress} />
        </div>

        {/* Agent Steps */}
        <div className="space-y-4">
          {agentSteps.map((step, index) => {
            const isCompleted = currentAgentIndex > index || status.status === 'completed';
            const isCurrent = currentAgentIndex === index && status.status === 'processing';
            const isPending = currentAgentIndex < index && status.status !== 'failed';

            return (
              <div key={step.name} className="flex items-start">
                {/* Icon */}
                <div className="flex-shrink-0 mr-4">
                  {isCompleted && (
                    <div className="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    </div>
                  )}
                  {isCurrent && (
                    <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                      <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
                    </div>
                  )}
                  {isPending && (
                    <div className="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center">
                      <Clock className="h-5 w-5 text-gray-400" />
                    </div>
                  )}
                  {status.status === 'failed' && !isCompleted && (
                    <div className="h-8 w-8 rounded-full bg-red-100 flex items-center justify-center">
                      <XCircle className="h-5 w-5 text-red-600" />
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1">
                  <p className={`font-medium ${isCurrent ? 'text-blue-600' : 'text-gray-900'}`}>
                    {step.label}
                  </p>
                  <p className="text-sm text-gray-500">
                    {step.duration}
                    {isCurrent && status.message && ` • ${status.message}`}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Error Message */}
        {status.error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm font-medium text-red-800 mb-1">Erro</p>
            <p className="text-sm text-red-700">{status.error}</p>
          </div>
        )}

        {/* Completion Info */}
        {status.status === 'completed' && status.completed_at && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-800">
              Processamento concluído com sucesso em{' '}
              {formatDuration(
                new Date(status.completed_at).getTime() -
                  new Date(status.started_at!).getTime()
              )}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
